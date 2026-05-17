"""
레벨 계산기 단위 테스트

테스트 대상:
    app/utils/level_calculator.py

검증 항목:
    - 변화율 구간별 레벨 반환값이 pingi-backend와 동일한지
    - 경계값(0%, 5%, 15%, 30%, 50%, 70%)에서의 동작
    - 방향 인식 변화율 계산의 정확성
    - DRUNK_DIRECTION이 9개 피처를 모두 포함하는지

이 테스트가 중요한 이유:
    pingi-backend의 levelCalculator.ts와 동일한 결과를 보장해야
    프론트엔드에 표시되는 레벨이 일관성을 유지한다.

실행:
    pytest tests/test_level_calculator.py -v
"""

from app.utils.level_calculator import (
    DRUNK_DIRECTION,
    calculate_level,
    calculate_directional_change_rate,
)


class TestCalculateLevel:
    """calculate_level() 함수 테스트: 변화율 → 레벨 변환"""

    def test_level_0_under_5_percent(self):
        """변화율 < 5%이면 레벨 0 (멀쩡해요)"""
        assert calculate_level(0.0) == 0
        assert calculate_level(4.9) == 0

    def test_level_1_between_5_and_15(self):
        """5% ≤ 변화율 < 15%이면 레벨 1 (살짝 취기)"""
        assert calculate_level(5.0) == 1
        assert calculate_level(14.9) == 1

    def test_level_2_between_15_and_30(self):
        """15% ≤ 변화율 < 30%이면 레벨 2 (기분 좋은 취기)"""
        assert calculate_level(15.0) == 2
        assert calculate_level(29.9) == 2

    def test_level_3_between_30_and_50(self):
        """30% ≤ 변화율 < 50%이면 레벨 3 (제법 취함)"""
        assert calculate_level(30.0) == 3
        assert calculate_level(49.9) == 3

    def test_level_4_between_50_and_70(self):
        """50% ≤ 변화율 < 70%이면 레벨 4 (많이 취함)"""
        assert calculate_level(50.0) == 4
        assert calculate_level(69.9) == 4

    def test_level_5_over_70(self):
        """변화율 ≥ 70%이면 레벨 5 (만취)"""
        assert calculate_level(70.0) == 5
        assert calculate_level(100.0) == 5

    def test_negative_change_rate_uses_absolute(self):
        """음수 변화율도 절댓값으로 처리한다"""
        assert calculate_level(-25.0) == 2
        assert calculate_level(-60.0) == 4


class TestDirectionalChangeRate:
    """calculate_directional_change_rate() 함수 테스트"""

    def test_increase_direction_drunk(self):
        """increase 방향: 값이 증가하면 양수 변화율 (취한 방향)"""
        rate = calculate_directional_change_rate(0.01, 0.015, "increase")
        assert abs(rate - 50.0) < 0.01

    def test_increase_direction_sober(self):
        """increase 방향: 값이 감소하면 0으로 클램핑 (오히려 좋아짐)"""
        rate = calculate_directional_change_rate(0.015, 0.01, "increase")
        assert rate == 0.0

    def test_decrease_direction_drunk(self):
        """decrease 방향: 값이 감소하면 양수 변화율 (취한 방향)"""
        rate = calculate_directional_change_rate(15.0, 10.0, "decrease")
        assert abs(rate - 33.33) < 0.1

    def test_decrease_direction_sober(self):
        """decrease 방향: 값이 증가하면 0으로 클램핑"""
        rate = calculate_directional_change_rate(10.0, 15.0, "decrease")
        assert rate == 0.0

    def test_deviation_direction(self):
        """deviation 방향: 편차의 절대값으로 변화율 계산"""
        rate = calculate_directional_change_rate(500.0, 475.0, "deviation")
        assert rate == 5.0

    def test_deviation_direction_both_ways(self):
        """deviation 방향: 증가든 감소든 편차만 측정"""
        rate_up = calculate_directional_change_rate(500.0, 525.0, "deviation")
        rate_down = calculate_directional_change_rate(500.0, 475.0, "deviation")
        assert rate_up == rate_down == 5.0

    def test_baseline_zero_returns_zero(self):
        """베이스라인이 0이면 변화율 0 (0 나누기 방지)"""
        assert calculate_directional_change_rate(0.0, 0.5, "increase") == 0.0
        assert calculate_directional_change_rate(0.0, 0.5, "decrease") == 0.0
        assert calculate_directional_change_rate(0.0, 0.5, "deviation") == 0.0

    def test_no_change_returns_zero(self):
        """같은 값이면 변화율 0%"""
        assert calculate_directional_change_rate(12.0, 12.0, "increase") == 0.0
        assert calculate_directional_change_rate(12.0, 12.0, "decrease") == 0.0
        assert calculate_directional_change_rate(12.0, 12.0, "deviation") == 0.0


class TestDrunkDirection:
    """DRUNK_DIRECTION 딕셔너리 검증"""

    _EXPECTED_FEATURES = {
        "jitter", "shimmer", "hnr", "f1", "f2",
        "loudness", "f0", "f0_var", "speed",
    }

    def test_contains_all_features(self):
        """9개 피처가 모두 정의되어 있는지 확인"""
        assert set(DRUNK_DIRECTION.keys()) == self._EXPECTED_FEATURES

    def test_valid_directions_only(self):
        """모든 값이 유효한 방향 문자열인지 확인"""
        valid = {"increase", "decrease", "deviation"}
        for key, direction in DRUNK_DIRECTION.items():
            assert direction in valid, f"{key}의 방향 '{direction}'이 유효하지 않음"

    def test_specific_directions(self):
        """학술 근거 기반으로 설정된 방향을 검증"""
        assert DRUNK_DIRECTION["jitter"] == "increase"
        assert DRUNK_DIRECTION["shimmer"] == "increase"
        assert DRUNK_DIRECTION["hnr"] == "decrease"
        assert DRUNK_DIRECTION["f1"] == "increase"
        assert DRUNK_DIRECTION["f2"] == "increase"
        assert DRUNK_DIRECTION["loudness"] == "deviation"
        assert DRUNK_DIRECTION["f0"] == "increase"
        assert DRUNK_DIRECTION["f0_var"] == "increase"
        assert DRUNK_DIRECTION["speed"] == "decrease"
