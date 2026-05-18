"""
음향 분석 서비스 (파이프라인 통합)

개별 서비스(audio_converter, feature_extractor)를
하나의 파이프라인으로 조합하여 음향 피처를 추출하고,
베이스라인 대비 변화율/취도까지 계산한다.

두 가지 분석 모드:
    1. 베이스라인 분석 (analyze_baseline):
       맨정신 상태의 오디오 1개 → 9개 피처 추출
       pingi-backend가 DB에 저장하여 이후 비교에 사용

    2. 핑이타임 녹음 분석 (analyze_recording):
       오디오 1개 + 베이스라인 피처 → 9개 피처 추출 + 변화율 + 취도 레벨 산출
"""

import logging

from app.models.schemas import (
    BaselineFeatures,
    BaselineResponse,
    RecordingFeatures,
    RecordingResponse,
)
from app.services.audio_converter import convert_to_wav, cleanup_temp_file
from app.services.feature_extractor import extract_all_features
from app.utils.level_calculator import (
    DRUNK_DIRECTION,
    FEATURE_WEIGHTS,
    calculate_directional_change_rate,
    calculate_level,
    get_level_description,
)

logger = logging.getLogger(__name__)

_FEATURE_KEYS = [
    "jitter", "shimmer", "hnr", "f1", "f2",
    "loudness", "f0", "f0_var", "speed",
]


def _extract_features(
    audio_bytes: bytes,
    filename: str,
    sentence: str,
) -> dict[str, float]:
    """오디오 파일에서 9개 피처를 추출하는 내부 파이프라인."""
    wav_path = convert_to_wav(audio_bytes, filename)

    try:
        return extract_all_features(wav_path, sentence)
    finally:
        cleanup_temp_file(wav_path)


def analyze_baseline(
    audio_bytes: bytes,
    filename: str,
    sentence: str,
) -> BaselineResponse:
    """
    맨정신 상태의 오디오 1개를 분석하여 개인 음성 기준선을 생성한다.

    매개변수:
        audio_bytes: 업로드된 오디오 파일의 바이트 데이터
        filename:    원본 파일명 (포맷 판별용). 예) "recording.webm"
        sentence:    사용자가 읽어야 했던 문장 (speed 음절 수 계산용)

    반환값:
        BaselineResponse { features }
    """
    logger.info("베이스라인 분석 시작")

    result = _extract_features(audio_bytes, filename, sentence)

    features = BaselineFeatures(
        jitter=round(result["jitter"], 6),
        shimmer=round(result["shimmer"], 4),
        hnr=round(result["hnr"], 2),
        f1=round(result["f1"], 4),
        f2=round(result["f2"], 4),
        loudness=round(result["loudness"], 4),
        f0=round(result["f0"], 2),
        f0_var=round(result["f0_var"], 4),
        speed=round(result["speed"], 4),
    )

    logger.info(
        "베이스라인 분석 완료: jitter=%.4f, shimmer=%.3f, hnr=%.1f, "
        "f1=%.4f, f2=%.4f, loudness=%.3f, f0=%.1f, f0_var=%.4f, speed=%.3f",
        features.jitter, features.shimmer, features.hnr,
        features.f1, features.f2, features.loudness, features.f0,
        features.f0_var, features.speed,
    )

    return BaselineResponse(features=features)


def analyze_recording(
    audio_bytes: bytes,
    filename: str,
    sentence: str,
    baseline: BaselineFeatures,
) -> RecordingResponse:
    """
    핑이타임 녹음을 분석하여 피처, 변화율, 취도 레벨을 반환한다.

    매개변수:
        audio_bytes: 업로드된 오디오 파일의 바이트 데이터
        filename:    원본 파일명 (포맷 판별용)
        sentence:    사용자가 읽어야 했던 문장
        baseline:    맨정신 상태에서 추출한 베이스라인 피처

    반환값:
        RecordingResponse { features, change_rate, level, level_description }
    """
    result = _extract_features(audio_bytes, filename, sentence)

    features = RecordingFeatures(
        jitter=round(result["jitter"], 6),
        shimmer=round(result["shimmer"], 4),
        hnr=round(result["hnr"], 2),
        f1=round(result["f1"], 4),
        f2=round(result["f2"], 4),
        loudness=round(result["loudness"], 4),
        f0=round(result["f0"], 2),
        f0_var=round(result["f0_var"], 4),
        speed=round(result["speed"], 4),
    )

    baseline_dict = baseline.model_dump()
    weighted_sum = 0.0

    for key in _FEATURE_KEYS:
        direction = DRUNK_DIRECTION[key]
        rate = calculate_directional_change_rate(
            baseline_dict[key], result[key], direction,
        )
        weighted_sum += rate * FEATURE_WEIGHTS[key]

    change_rate = round(weighted_sum, 2)
    level = calculate_level(change_rate)
    description = get_level_description(level)

    logger.info(
        "핑이타임 분석 완료: changeRate=%.1f%%, level=%d (%s)",
        change_rate, level, description,
    )

    return RecordingResponse(
        features=features,
        change_rate=change_rate,
        level=level,
        level_description=description,
    )
