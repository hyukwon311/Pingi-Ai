"""
음향 특징 추출 서비스

openSMILE eGeMAPSv02와 librosa를 사용하여 음성 파일에서 음향 특징을 추출한다.

추출하는 특징 (9가지):
    openSMILE eGeMAPSv02 (8가지):
        1. jitter   — 성대 떨림 주기의 불규칙성 (amean). 취하면 증가.
        2. shimmer  — 음성 진폭의 불안정성 (amean). 취하면 증가.
        3. hnr      — 조화음 대비 잡음 비율 (amean). 취하면 감소.
        4. f1       — 제1 포먼트 발화 내 변동성 (stddevNorm). 취하면 증가.
        5. f2       — 제2 포먼트 발화 내 변동성 (stddevNorm). 취하면 증가.
        6. loudness — 평균 음량 (amean). 취하면 변화 방향 불확실(환경 의존).
        7. f0       — 기본 주파수 평균 (amean). 취하면 상승 경향(30% 예외).
        8. f0_var   — 기본 주파수 변동성 (stddevNorm). 취하면 증가. 가장 robust한 지표 중 하나.

    librosa (1가지):
        9. speed    — 발화 속도(초당 음절 수). 취하면 느려짐. 가장 일관된 지표.
"""

import logging
from functools import lru_cache

import librosa
import numpy as np
import opensmile

logger = logging.getLogger(__name__)

_KOREAN_NORMAL_SYLLABLE_RATE = 5.0
_SPEED_TOLERANCE = 2.5


@lru_cache(maxsize=1)
def _get_smile() -> opensmile.Smile:
    """openSMILE 인스턴스를 생성하고 캐싱한다."""
    logger.info("openSMILE eGeMAPSv02 초기화")
    return opensmile.Smile(
        feature_set=opensmile.FeatureSet.eGeMAPSv02,
        feature_level=opensmile.FeatureLevel.Functionals,
    )


def extract_opensmile_features(wav_path: str) -> dict[str, float]:
    """
    eGeMAPSv02로 8가지 음향 피처를 추출한다.

    F1/F2는 평균값이 아닌 정규화 표준편차(stddevNorm)를 사용한다.
    음주 시 F1/F2 평균은 거의 변하지 않지만, 발화 내 변동성이 크게 증가하기 때문이다.

    매개변수:
        wav_path: 16kHz 모노 wav 파일 경로

    반환값:
        {
            "jitter": 0.012,    # 주기 불규칙성 (로컬 jitter 평균)
            "shimmer": 0.45,    # 진폭 불안정성 (로컬 shimmer dB 평균)
            "hnr": 12.3,        # 조화음 대비 잡음 비율 (dB)
            "f1": 0.25,         # 제1 포먼트 발화 내 변동성 (stddevNorm)
            "f2": 0.18,         # 제2 포먼트 발화 내 변동성 (stddevNorm)
            "loudness": 0.35,   # 평균 음량 (sone)
            "f0": 28.5,         # 기본 주파수 평균 (semitone from 27.5Hz)
            "f0_var": 0.045,    # 기본 주파수 변동성 (stddevNorm)
        }
    """
    smile = _get_smile()
    df = smile.process_file(wav_path)

    features = {
        "jitter": float(df["jitterLocal_sma3nz_amean"].iloc[0]),
        "shimmer": float(df["shimmerLocaldB_sma3nz_amean"].iloc[0]),
        "hnr": float(df["HNRdBACF_sma3nz_amean"].iloc[0]),
        "f1": float(df["F1frequency_sma3nz_stddevNorm"].iloc[0]),
        "f2": float(df["F2frequency_sma3nz_stddevNorm"].iloc[0]),
        "loudness": float(df["loudness_sma3_amean"].iloc[0]),
        "f0": float(df["F0semitoneFrom27.5Hz_sma3nz_amean"].iloc[0]),
        "f0_var": float(df["F0semitoneFrom27.5Hz_sma3nz_stddevNorm"].iloc[0]),
    }

    logger.debug(
        "openSMILE 피처: jitter=%.4f, shimmer=%.3f, hnr=%.1f, "
        "f1=%.4f, f2=%.4f, loudness=%.3f, f0=%.1f, f0_var=%.4f",
        features["jitter"], features["shimmer"], features["hnr"],
        features["f1"], features["f2"], features["loudness"],
        features["f0"], features["f0_var"],
    )
    return features


def extract_speed_score(y: np.ndarray, sr: int, syllable_count: int) -> float:
    """
    발화 속도의 정상 범위 적합도를 측정한다.

    음절 수를 발화 시간(초)으로 나누어 초당 음절 수를 구한 뒤,
    한국어 평균 발화 속도(~5 음절/초)와 비교한다.

    매개변수:
        y:              오디오 시계열 데이터
        sr:             샘플링 레이트 (Hz)
        syllable_count: 기대 문장의 음절 수

    반환값:
        0.0 ~ 1.0 사이의 속도 적합도 점수.
        1.0에 가까울수록 정상 발화 속도.
    """
    intervals = librosa.effects.split(y, top_db=30)

    if len(intervals) == 0:
        logger.warning("발화 구간을 감지할 수 없습니다")
        return 0.5

    total_speech_samples = sum(end - start for start, end in intervals)
    speech_duration = total_speech_samples / sr

    if speech_duration < 0.1:
        logger.warning("발화 시간이 너무 짧습니다: %.3fs", speech_duration)
        return 0.5

    syllable_rate = syllable_count / speech_duration
    deviation = abs(syllable_rate - _KOREAN_NORMAL_SYLLABLE_RATE)
    score = max(0.0, 1.0 - (deviation / _SPEED_TOLERANCE))

    logger.debug(
        "speed: syllables=%d, duration=%.2fs, rate=%.1f syl/s → score=%.3f",
        syllable_count, speech_duration, syllable_rate, score,
    )
    return round(score, 4)


def count_korean_syllables(text: str) -> int:
    """
    한글 텍스트에서 음절(글자) 수를 센다.

    한글 유니코드 범위(U+AC00 ~ U+D7A3)에 해당하는 문자만 카운트한다.

    매개변수:
        text: 음절 수를 셀 텍스트. 예) "간장 공장 공장장은"

    반환값:
        한글 음절 수. 예) 7
    """
    return sum(1 for ch in text if 0xAC00 <= ord(ch) <= 0xD7A3)


def extract_all_features(wav_path: str, expected_sentence: str) -> dict[str, float]:
    """
    wav 파일에서 모든 음향 특징을 추출한다.

    openSMILE eGeMAPSv02로 8가지 피처를 추출하고,
    librosa로 발화 속도(speed)를 계산하여 총 9가지 피처를 반환한다.

    매개변수:
        wav_path:          16kHz 모노 wav 파일 경로
        expected_sentence: 사용자가 읽어야 했던 문장 (음절 수 계산용)

    반환값:
        {
            "jitter": ..., "shimmer": ..., "hnr": ...,
            "f1": ..., "f2": ..., "loudness": ..., "f0": ...,
            "f0_var": ..., "speed": 0.85,
        }
    """
    smile_features = extract_opensmile_features(wav_path)

    y, sr = librosa.load(wav_path, sr=None)
    syllable_count = count_korean_syllables(expected_sentence)
    if syllable_count == 0:
        syllable_count = len(expected_sentence.replace(" ", ""))

    speed = extract_speed_score(y, sr, syllable_count)

    return {**smile_features, "speed": speed}
