"""
베이스라인 분석 엔드포인트

술자리 시작 전, 멤버가 맨정신 상태에서 3개의 잰말 문장을 녹음한다.
이 녹음들을 분석하여 개인 음성 기준선(baseline features)을 생성한다.
pingi-backend는 이 features를 DB에 저장하고,
이후 핑이타임에서 이 기준선 대비 변화율로 취도를 판정한다.

엔드포인트:
    POST /api/v1/analyze/baseline

요청 (multipart/form-data):
    - audio1 (file): 첫 번째 녹음 (webm/wav)
    - audio2 (file): 두 번째 녹음
    - audio3 (file): 세 번째 녹음
    - sentence1 (string): 첫 번째 문장 텍스트
    - sentence2 (string): 두 번째 문장 텍스트
    - sentence3 (string): 세 번째 문장 텍스트

응답:
    {
        "features": {
            "jitter": 0.012, "shimmer": 0.45, "hnr": 12.3,
            "f1": 520.0, "f2": 1580.0, "loudness": 0.35, "f0": 28.5,
            "speed": 0.88, "consistency": 0.9
        }
    }

호출 시점 (pingi-backend 기준):
    POST /v1/members/:id/baseline/complete 처리 시
    baselineService.ts에서 이 엔드포인트를 호출한다.
"""

import logging

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.models.schemas import BaselineResponse, ErrorResponse
from app.services.analyzer import analyze_baseline_audios

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze/baseline",
    response_model=BaselineResponse,
    responses={
        400: {"model": ErrorResponse, "description": "오디오 파일 또는 문장 누락"},
        500: {"model": ErrorResponse, "description": "분석 중 내부 오류 발생"},
    },
    summary="베이스라인 음성 분석",
    description="맨정신 상태의 음성 3개를 분석하여 개인 음성 기준선(features)을 생성한다. "
                "pingi-backend가 baseline complete 시점에 호출한다.",
)
async def analyze_baseline(
    audio1: UploadFile = File(
        ...,
        description="첫 번째 베이스라인 녹음 파일 (webm/wav)",
    ),
    audio2: UploadFile = File(
        ...,
        description="두 번째 베이스라인 녹음 파일 (webm/wav)",
    ),
    audio3: UploadFile = File(
        ...,
        description="세 번째 베이스라인 녹음 파일 (webm/wav)",
    ),
    sentence1: str = Form(
        ...,
        description="첫 번째 녹음의 기대 문장. 예) '간장 공장 공장장은...'",
    ),
    sentence2: str = Form(
        ...,
        description="두 번째 녹음의 기대 문장",
    ),
    sentence3: str = Form(
        ...,
        description="세 번째 녹음의 기대 문장",
    ),
) -> BaselineResponse:
    """
    베이스라인 음성 3개를 분석한다.

    처리 과정:
        1. 업로드된 3개 오디오 파일을 각각 wav로 변환
        2. 각 오디오에 대해 openSMILE + librosa 음향 분석 수행
        3. 3개 결과의 평균으로 베이스라인 features 산출
        4. 3개 녹음 간 일관성(consistency) 계산

    매개변수:
        audio1~3:    업로드된 오디오 파일 (multipart/form-data의 file 필드)
        sentence1~3: 각 녹음의 기대 문장 (multipart/form-data의 text 필드)

    반환값:
        BaselineResponse: features (8개 음향 지표 + consistency)

    에러:
        400: 오디오 파일이 비어있거나 읽을 수 없는 경우
        500: 음향 분석 중 예외 발생
    """
    try:
        audio_data_list: list[tuple[bytes, str]] = []
        for i, audio_file in enumerate([audio1, audio2, audio3], start=1):
            content = await audio_file.read()
            if not content:
                raise HTTPException(
                    status_code=400,
                    detail={"error": {"code": "EMPTY_AUDIO", "message": f"audio{i} 파일이 비어있습니다"}},
                )
            audio_data_list.append((content, audio_file.filename or f"audio{i}.webm"))

        sentences = [sentence1, sentence2, sentence3]

        logger.info(
            "베이스라인 분석 요청: files=[%s], sentences=[%s]",
            ", ".join(f.filename or "unknown" for f in [audio1, audio2, audio3]),
            ", ".join(s[:20] + "..." for s in sentences),
        )

        result = await analyze_baseline_audios(audio_data_list, sentences)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("베이스라인 분석 실패")
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "ANALYSIS_FAILED", "message": f"베이스라인 분석 중 오류 발생: {e}"}},
        )
