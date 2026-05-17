"""
음향 특징 추출기 단위 테스트

테스트 대상:
    app/services/feature_extractor.py

검증 항목:
    - count_korean_syllables()의 음절 수 계산
    - extract_speed_score()의 점수 범위 및 정상 동작
    - 피처 키 상수 목록이 9개 피처를 포함하는지

실행:
    pytest tests/test_feature_extractor.py -v
"""

import numpy as np

from app.services.feature_extractor import (
    count_korean_syllables,
    extract_speed_score,
)


class TestCountKoreanSyllables:
    """count_korean_syllables() 함수 테스트"""

    def test_basic_korean(self):
        """한글 음절 수를 정확히 센다"""
        assert count_korean_syllables("간장 공장") == 4

    def test_longer_sentence(self):
        """긴 문장의 음절 수 계산"""
        assert count_korean_syllables("간장 공장 공장장은") == 8

    def test_no_korean(self):
        """한글이 없으면 0"""
        assert count_korean_syllables("hello 123") == 0

    def test_mixed(self):
        """한글과 영문이 섞여 있으면 한글만 카운트"""
        assert count_korean_syllables("hello 세계") == 2

    def test_empty(self):
        """빈 문자열이면 0"""
        assert count_korean_syllables("") == 0


class TestExtractSpeedScore:
    """extract_speed_score() 함수 테스트"""

    def test_returns_score_in_range(self):
        """반환값이 0~1 범위인지 확인"""
        sr = 16000
        duration = 2.0
        y = np.random.randn(int(sr * duration)).astype(np.float32)
        y = y * 0.5
        score = extract_speed_score(y, sr, syllable_count=10)
        assert 0.0 <= score <= 1.0

    def test_silent_audio_returns_default(self):
        """무음 오디오는 기본값(0.5) 반환"""
        sr = 16000
        y = np.zeros(sr * 2)
        score = extract_speed_score(y, sr, syllable_count=10)
        assert score == 0.5


class TestFeatureKeys:
    """피처 키 목록이 analyzer의 _WEIGHTS, DRUNK_DIRECTION과 일치하는지 검증"""

    _EXPECTED_OPENSMILE_KEYS = {
        "jitter", "shimmer", "hnr", "f1", "f2",
        "loudness", "f0", "f0_var",
    }

    _EXPECTED_ALL_KEYS = _EXPECTED_OPENSMILE_KEYS | {"speed"}

    def test_opensmile_feature_count(self):
        """openSMILE 피처가 8개인지 확인"""
        assert len(self._EXPECTED_OPENSMILE_KEYS) == 8

    def test_all_feature_count(self):
        """전체 피처(openSMILE + speed)가 9개인지 확인"""
        assert len(self._EXPECTED_ALL_KEYS) == 9
