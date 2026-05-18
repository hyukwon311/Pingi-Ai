"""
API 요청/응답 스키마 정의

pingi-backend가 pingi-ai를 호출할 때 주고받는 데이터 구조를 정의한다.
모든 스키마는 Pydantic BaseModel을 상속하여 자동 검증과 직렬화를 수행한다.

API 흐름:
    1. 베이스라인 분석: 오디오 1개 → BaselineResponse (9개 피처)
    2. 핑이타임 분석: 오디오 1개 + baseline → RecordingResponse (피처 + 변화율 + 취도)
    3. 헬스 체크: → HealthResponse (status, model, version)

pingi-ai가 피처 추출부터 변화율/취도 계산까지 전체를 담당한다.
pingi-backend는 세션 관리와 결과 저장/조회만 수행한다.

음향 피처 (openSMILE eGeMAPSv02 + librosa):
    jitter, shimmer, hnr, f0 — openSMILE amean (평균값)
    f1, f2, f0_var, loudness — openSMILE stddevNorm (발화 내 변동성)
    speed — librosa 기반 발화 속도 점수 (0~1)
"""

from pydantic import BaseModel, Field


# =============================================================================
# 베이스라인 분석 관련 스키마
# =============================================================================

class BaselineFeatures(BaseModel):
    """
    맨정신 상태의 음성 특성 지표 (베이스라인)

    술을 마시기 전 녹음에서 추출한 음성 특성값이다.
    이후 핑이타임에서 이 값을 기준으로 변화율을 계산하여 취도를 판정한다.

    openSMILE amean 피처는 원시값, stddevNorm 피처는 정규화 표준편차이다.
    speed만 0~1 범위이다.
    """

    jitter: float = Field(
        ...,
        description="성대 떨림 주기 불규칙성 (로컬 jitter 평균). 취하면 변동하나 방향 일관성이 부족하다.",
        examples=[0.012],
    )
    shimmer: float = Field(
        ...,
        description="음성 진폭 불안정성 (로컬 shimmer dB 평균). 취하면 변동한다(성별·모음 의존적).",
        examples=[0.45],
    )
    hnr: float = Field(
        ...,
        description="조화음 대비 잡음 비율 (HNR, dB). 취하면 감소한다.",
        examples=[12.3],
    )
    f1: float = Field(
        ...,
        description="제1 포먼트 발화 내 변동성 (stddevNorm). 취하면 턱/입 제어 저하로 증가한다.",
        examples=[0.25],
    )
    f2: float = Field(
        ...,
        description="제2 포먼트 발화 내 변동성 (stddevNorm). 취하면 혀 제어 저하로 증가한다.",
        examples=[0.18],
    )
    loudness: float = Field(
        ...,
        description="음량 변동성 (stddevNorm). 음주 시 호흡 제어 저하로 분포 확산. 측정 환경 의존적.",
        examples=[0.35],
    )
    f0: float = Field(
        ...,
        description="기본 주파수 평균 (semitone from 27.5Hz). 취하면 상승 경향이나 개인차 존재.",
        examples=[28.5],
    )
    f0_var: float = Field(
        ...,
        description="기본 주파수 변동성 (stddevNorm). 취하면 운동 제어 저하로 거의 보편적으로 증가한다.",
        examples=[0.045],
    )
    speed: float = Field(
        ...,
        ge=0.0, le=1.0,
        description="발화 속도 안정성 (0~1). 정상 발화 속도에 가까울수록 높은 값. 가장 일관된 음주 지표.",
        examples=[0.88],
    )


class BaselineResponse(BaseModel):
    """
    POST /api/v1/analyze/baseline 응답

    맨정신 상태의 음성 1개를 분석하여 개인 음성 기준선(features)을 반환한다.
    pingi-backend는 features를 DB에 저장하여 이후 핑이타임 비교에 사용한다.
    """

    features: BaselineFeatures = Field(
        ...,
        description="녹음에서 추출한 9개 음성 특성값",
    )


# =============================================================================
# 핑이타임 녹음 분석 관련 스키마
# =============================================================================

class RecordingFeatures(BaseModel):
    """핑이타임 녹음에서 추출한 9개 음향 피처"""

    jitter: float = Field(
        ...,
        description="성대 떨림 주기 불규칙성 (로컬 jitter 평균)",
        examples=[0.018],
    )
    shimmer: float = Field(
        ...,
        description="음성 진폭 불안정성 (로컬 shimmer dB 평균)",
        examples=[0.62],
    )
    hnr: float = Field(
        ...,
        description="조화음 대비 잡음 비율 (HNR, dB)",
        examples=[9.8],
    )
    f1: float = Field(
        ...,
        description="제1 포먼트 발화 내 변동성 (stddevNorm)",
        examples=[0.35],
    )
    f2: float = Field(
        ...,
        description="제2 포먼트 발화 내 변동성 (stddevNorm)",
        examples=[0.28],
    )
    loudness: float = Field(
        ...,
        description="음량 변동성 (stddevNorm)",
        examples=[0.42],
    )
    f0: float = Field(
        ...,
        description="기본 주파수 평균 (semitone from 27.5Hz)",
        examples=[30.1],
    )
    f0_var: float = Field(
        ...,
        description="기본 주파수 변동성 (stddevNorm)",
        examples=[0.078],
    )
    speed: float = Field(
        ...,
        ge=0.0, le=1.0,
        description="발화 속도 안정성 (0~1)",
        examples=[0.72],
    )


class RecordingResponse(BaseModel):
    """
    POST /api/v1/analyze/recording 응답

    핑이타임 녹음에서 추출한 9개 음향 피처와 함께
    베이스라인 대비 변화율, 취도 레벨, 레벨 설명을 반환한다.
    """

    features: RecordingFeatures = Field(
        ...,
        description="핑이타임 녹음에서 추출한 9개 음향 피처",
    )
    change_rate: float = Field(
        ...,
        description="베이스라인 대비 가중 평균 변화율 (%). 높을수록 많이 취함.",
        examples=[23.5],
    )
    level: int = Field(
        ...,
        ge=0, le=5,
        description="취도 레벨 (0~5). 0=멀쩡, 5=만취.",
        examples=[2],
    )
    level_description: str = Field(
        ...,
        description="취도 레벨에 대응하는 한글 설명",
        examples=["기분 좋은 취기"],
    )


# =============================================================================
# 헬스 체크 스키마
# =============================================================================

class HealthResponse(BaseModel):
    """
    GET /api/v1/health 응답

    pingi-ai 서버의 동작 상태를 확인한다.
    pingi-backend가 기동 시 이 엔드포인트를 호출하여
    AI 서버 사용 가능 여부를 판단한다.
    """

    status: str = Field(
        ...,
        description="서버 상태. 정상이면 'ok'.",
        examples=["ok"],
    )
    model: str = Field(
        ...,
        description="사용 중인 음향 분석 모델 이름",
        examples=["opensmile-eGeMAPSv02"],
    )
    version: str = Field(
        ...,
        description="pingi-ai 서버 버전",
        examples=["0.1.0"],
    )


# =============================================================================
# 에러 응답 스키마
# =============================================================================

class ErrorDetail(BaseModel):
    """에러 상세 정보"""

    code: str = Field(
        ...,
        description="에러 코드. 클라이언트가 에러 종류를 구분하는 데 사용.",
        examples=["ANALYSIS_FAILED"],
    )
    message: str = Field(
        ...,
        description="사람이 읽을 수 있는 에러 메시지",
        examples=["음성 파일을 분석할 수 없습니다"],
    )


class ErrorResponse(BaseModel):
    """
    모든 에러 응답의 공통 형식

    pingi-backend가 에러를 일관되게 처리할 수 있도록
    에러 코드와 메시지를 포함한다.
    """

    error: ErrorDetail
