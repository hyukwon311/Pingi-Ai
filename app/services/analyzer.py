"""
음향 분석 서비스 (파이프라인 통합)

개별 서비스(audio_converter, feature_extractor)를
하나의 파이프라인으로 조합하여 음향 피처를 추출한다.

두 가지 분석 모드:
    1. 단일 오디오 분석 (analyze_single_audio):
       오디오 1개 → 9개 피처 추출
       핑이타임 녹음 분석에서 사용

    2. 베이스라인 분석 (analyze_baseline_audios):
       맨정신 상태의 음성 3개 → 개인 음성 기준선(features + consistency) 생성
       pingi-backend가 DB에 저장하여 이후 비교에 사용

변화율/취도 계산은 pingi-backend에서 수행한다.
"""

import logging

import numpy as np

from app.models.schemas import (
    BaselineFeatures,
    BaselineResponse,
)
from app.services.audio_converter import convert_to_wav, cleanup_temp_file
from app.services.feature_extractor import extract_all_features

logger = logging.getLogger(__name__)

_FEATURE_KEYS = [
    "jitter", "shimmer", "hnr", "f1", "f2",
    "loudness", "f0", "f0_var", "speed",
]


def analyze_single_audio(
    audio_bytes: bytes,
    filename: str,
    sentence: str,
) -> dict[str, float]:
    """
    단일 오디오 파일을 분석하여 9개 피처를 추출한다.

    오디오 변환 → openSMILE + librosa 분석의 전체 파이프라인을 실행한다.

    매개변수:
        audio_bytes: 업로드된 오디오 파일의 바이트 데이터
        filename:    원본 파일명 (포맷 판별용). 예) "recording.webm"
        sentence:    사용자가 읽어야 했던 문장 (speed 음절 수 계산용)

    반환값:
        {
            "jitter": 0.012, "shimmer": 0.45, "hnr": 12.3,
            "f1": 0.25, "f2": 0.18, "loudness": 0.35, "f0": 28.5,
            "f0_var": 0.045, "speed": 0.88,
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
        result = analyze_single_audio(audio_bytes, filename, sentence)
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
        f1=round(averages["f1"], 4),
        f2=round(averages["f2"], 4),
        loudness=round(averages["loudness"], 4),
        f0=round(averages["f0"], 2),
        f0_var=round(averages["f0_var"], 4),
        speed=round(averages["speed"], 4),
        consistency=round(consistency, 4),
    )

    logger.info(
        "베이스라인 분석 완료: jitter=%.4f, shimmer=%.3f, hnr=%.1f, "
        "f1=%.4f, f2=%.4f, loudness=%.3f, f0=%.1f, f0_var=%.4f, "
        "speed=%.3f, consistency=%.3f",
        features.jitter, features.shimmer, features.hnr,
        features.f1, features.f2, features.loudness, features.f0,
        features.f0_var, features.speed, features.consistency,
    )

    return BaselineResponse(features=features)
