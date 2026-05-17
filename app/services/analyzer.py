"""
취도 분석 서비스 (파이프라인 통합)

개별 서비스(audio_converter, feature_extractor)를
하나의 파이프라인으로 조합하여 최종 분석 결과를 산출한다.

두 가지 분석 모드:
    1. 베이스라인 분석 (analyze_baseline_audios):
       맨정신 상태의 음성 3개 → 개인 음성 기준선(features) 생성
       → pingi-backend가 DB에 저장하여 이후 비교에 사용

    2. 핑이타임 분석 (analyze_recording_audio):
       술 마신 후 음성 1개 + 베이스라인 features → 취도 판정
       → score, level, changeRate 반환

각 피처의 취도 산출 기여도(가중치):
    - jitter   (15%): 성대 떨림 주기 불규칙성
    - shimmer  (15%): 음성 진폭 불안정성
    - hnr      (15%): 조화음 대비 잡음 비율
    - f1       (7.5%): 제1 포먼트 주파수 편차
    - f2       (7.5%): 제2 포먼트 주파수 편차
    - loudness (10%): 평균 음량 변화
    - f0       (15%): 기본 주파수 변동
    - speed    (15%): 발화 속도 변화
    총합 = 100%로, 가중 평균하여 단일 changeRate를 산출한다.
"""

import logging

import numpy as np

from app.models.schemas import (
    BaselineFeatures,
    BaselineResponse,
    RecordingDetail,
    RecordingResponse,
)
from app.utils.level_calculator import (
    DRUNK_DIRECTION,
    calculate_directional_change_rate,
    calculate_level,
)
from app.services.audio_converter import convert_to_wav, cleanup_temp_file
from app.services.feature_extractor import extract_all_features

logger = logging.getLogger(__name__)

_WEIGHTS: dict[str, float] = {
    "jitter": 0.15,
    "shimmer": 0.15,
    "hnr": 0.15,
    "f1": 0.075,
    "f2": 0.075,
    "loudness": 0.10,
    "f0": 0.15,
    "speed": 0.15,
}

_FEATURE_KEYS = list(_WEIGHTS.keys())


def _analyze_single_audio(
    audio_bytes: bytes,
    filename: str,
    sentence: str,
) -> dict[str, float]:
    """
    단일 오디오 파일을 분석하여 모든 피처를 추출한다.

    이 함수는 베이스라인과 핑이타임 분석 모두에서 공통으로 사용된다.
    오디오 변환 → openSMILE + librosa 분석의 전체 파이프라인을 실행한다.

    매개변수:
        audio_bytes: 업로드된 오디오 파일의 바이트 데이터
        filename:    원본 파일명 (포맷 판별용). 예) "recording.webm"
        sentence:    사용자가 읽어야 했던 문장 (speed 음절 수 계산용)

    반환값:
        {
            "jitter": 0.012, "shimmer": 0.45, "hnr": 12.3,
            "f1": 520.0, "f2": 1580.0, "loudness": 0.35, "f0": 28.5,
            "speed": 0.88,
        }
    """
    wav_path = convert_to_wav(audio_bytes, filename)

    try:
        return extract_all_features(wav_path, sentence)
    finally:
        cleanup_temp_file(wav_path)


async def analyze_baseline_audios(
    audio_data_list: list[tuple[bytes, str]],
    sentences: list[str],
) -> BaselineResponse:
    """
    베이스라인 음성 3개를 분석하여 개인 음성 기준선을 생성한다.

    맨정신 상태에서 녹음한 3개 음성의 피처를 각각 추출한 뒤,
    평균값을 베이스라인 features로 산출한다.

    consistency(일관성) 계산:
        3개 녹음의 각 피처에 대해 변동 계수(CV = std/mean)를 구한 뒤,
        전체 피처의 평균 CV가 낮을수록 높은 일관성 점수를 부여한다.

    매개변수:
        audio_data_list: [(오디오바이트, 파일명)] 리스트, 길이 3.
        sentences:       각 녹음에 대응하는 기대 문장 리스트, 길이 3.

    반환값:
        BaselineResponse { features }
    """
    logger.info("베이스라인 분석 시작: %d개 오디오", len(audio_data_list))

    results: list[dict[str, float]] = []
    for i, ((audio_bytes, filename), sentence) in enumerate(zip(audio_data_list, sentences)):
        logger.info("베이스라인 녹음 %d/3 분석 중...", i + 1)
        result = _analyze_single_audio(audio_bytes, filename, sentence)
        results.append(result)

    averages: dict[str, float] = {}
    cvs: list[float] = []

    for key in _FEATURE_KEYS:
        values = [r[key] for r in results]
        avg = float(np.mean(values))
        averages[key] = avg

        std = float(np.std(values))
        cv = std / abs(avg) if avg != 0 else 0.0
        cvs.append(cv)

    avg_cv = float(np.mean(cvs))
    # CV를 0~1 일관성 점수로 변환: CV=0 → 1.0(완벽), CV≥0.5 → 0.0
    consistency = max(0.0, min(1.0, 1.0 - (avg_cv / 0.5)))

    features = BaselineFeatures(
        jitter=round(averages["jitter"], 6),
        shimmer=round(averages["shimmer"], 4),
        hnr=round(averages["hnr"], 2),
        f1=round(averages["f1"], 2),
        f2=round(averages["f2"], 2),
        loudness=round(averages["loudness"], 4),
        f0=round(averages["f0"], 2),
        speed=round(averages["speed"], 4),
        consistency=round(consistency, 4),
    )

    logger.info(
        "베이스라인 분석 완료: jitter=%.4f, shimmer=%.3f, hnr=%.1f, "
        "f1=%.0f, f2=%.0f, loudness=%.3f, f0=%.1f, speed=%.3f, consistency=%.3f",
        features.jitter, features.shimmer, features.hnr,
        features.f1, features.f2, features.loudness, features.f0,
        features.speed, features.consistency,
    )

    return BaselineResponse(features=features)


async def analyze_recording_audio(
    audio_bytes: bytes,
    filename: str,
    sentence: str,
    baseline_features: BaselineFeatures,
) -> RecordingResponse:
    """
    핑이타임 녹음을 베이스라인과 비교하여 취도를 판정한다.

    처리 과정:
        1. 현재 녹음의 8개 피처 추출
        2. 각 피처별로 방향 인식 변화율 계산
        3. 가중 평균으로 종합 changeRate 산출
        4. changeRate → level(0~5) 변환
        5. score(0.0~1.0) 산출

    매개변수:
        audio_bytes:       핑이타임 녹음 바이트 데이터
        filename:          원본 파일명. 예) "pingitime.webm"
        sentence:          이번 핑이타임의 기대 문장
        baseline_features: DB에 저장된 해당 멤버의 베이스라인 피처

    반환값:
        RecordingResponse { score, level, changeRate, detail }
    """
    logger.info("핑이타임 분석 시작: sentence='%s'", sentence[:30])

    current = _analyze_single_audio(audio_bytes, filename, sentence)

    baseline_dict = {
        "jitter": baseline_features.jitter,
        "shimmer": baseline_features.shimmer,
        "hnr": baseline_features.hnr,
        "f1": baseline_features.f1,
        "f2": baseline_features.f2,
        "loudness": baseline_features.loudness,
        "f0": baseline_features.f0,
        "speed": baseline_features.speed,
    }

    weighted_change = 0.0
    for key in _FEATURE_KEYS:
        direction = DRUNK_DIRECTION[key]
        change = calculate_directional_change_rate(
            baseline_dict[key], current[key], direction,
        )
        weighted_change += change * _WEIGHTS[key]

    level = calculate_level(weighted_change)
    score = max(0.0, min(1.0, abs(weighted_change) / 100))

    logger.info(
        "핑이타임 분석 완료: changeRate=%.1f%%, level=%d, score=%.2f",
        weighted_change, level, score,
    )

    return RecordingResponse(
        score=round(score, 2),
        level=level,
        changeRate=round(weighted_change, 1),
        detail=RecordingDetail(
            currentJitter=round(current["jitter"], 6),
            currentShimmer=round(current["shimmer"], 4),
            currentHnr=round(current["hnr"], 2),
            currentF1=round(current["f1"], 2),
            currentF2=round(current["f2"], 2),
            currentLoudness=round(current["loudness"], 4),
            currentF0=round(current["f0"], 2),
            currentSpeed=round(current["speed"], 4),
        ),
    )
