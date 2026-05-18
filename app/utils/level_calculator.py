"""
취도 레벨 계산기

베이스라인 대비 발음 변화율(changeRate)을 0~5 레벨로 변환한다.

레벨 기준표:
    레벨 0 (멀쩡해요)       : 변화율 < 5%
    레벨 1 (살짝 취기)      : 5% ≤ 변화율 < 15%
    레벨 2 (기분 좋은 취기)  : 15% ≤ 변화율 < 30%
    레벨 3 (제법 취함)       : 30% ≤ 변화율 < 50%
    레벨 4 (많이 취함)       : 50% ≤ 변화율 < 70%
    레벨 5 (만취)            : 변화율 ≥ 70%
"""


# 음주 시 각 피처의 변화 방향 정의.
# "increase": 취하면 값이 증가 → (current - baseline) / baseline
# "decrease": 취하면 값이 감소 → (baseline - current) / baseline
# "deviation": 취하면 편차가 커짐 → abs(current - baseline) / baseline
DRUNK_DIRECTION: dict[str, str] = {
    "jitter": "deviation",
    "shimmer": "deviation",
    "hnr": "decrease",
    "f1": "increase",
    "f2": "increase",
    "loudness": "deviation",
    "f0": "increase",
    "f0_var": "increase",
    "speed": "decrease",
}

# 각 피처의 가중치 (합 = 1.0).
# 그룹 A — 의미 있는 변화량 (합 65%):
#   speed(20%), f0_var(18%), hnr(15%), f0(12%)
# 그룹 B — 일관성 부족 / 외부 요인·개인차 큰 Feature (합 35%):
#   jitter(9%), shimmer(9%), loudness(9%), f1(4%), f2(4%)
FEATURE_WEIGHTS: dict[str, float] = {
    "jitter": 0.09,
    "shimmer": 0.09,
    "hnr": 0.15,
    "f1": 0.04,
    "f2": 0.04,
    "loudness": 0.09,
    "f0": 0.12,
    "f0_var": 0.18,
    "speed": 0.20,
}


def calculate_level(change_rate: float) -> int:
    """
    변화율(%)을 취도 레벨(0~5)로 변환한다.

    음수 변화율도 절댓값으로 처리하여 발음이 "좋아진" 경우에도
    변화 자체를 감지한다.

    매개변수:
        change_rate: 베이스라인 대비 변화율 (%). 예) 23.5

    반환값:
        0~5 사이의 정수 레벨
    """
    abs_rate = abs(change_rate)

    if abs_rate < 5:
        return 0
    if abs_rate < 15:
        return 1
    if abs_rate < 30:
        return 2
    if abs_rate < 50:
        return 3
    if abs_rate < 70:
        return 4
    return 5


def calculate_directional_change_rate(
    baseline_value: float,
    current_value: float,
    direction: str,
) -> float:
    """
    방향을 고려한 변화율(%)을 계산한다.

    반환값은 항상 양수일수록 "취한 방향으로 변했음"을 의미한다.
    음수가 나오면 0으로 클램핑한다 (오히려 좋아진 방향).

    매개변수:
        baseline_value: 맨정신 상태의 측정값
        current_value:  현재(음주 후) 측정값
        direction:      변화 방향 ("increase", "decrease", "deviation")

    반환값:
        변화율 (%). 양수 = 취한 방향. 0 이상으로 클램핑.
    """
    if baseline_value == 0:
        return 0.0

    if direction == "increase":
        rate = (current_value - baseline_value) / abs(baseline_value) * 100
    elif direction == "decrease":
        rate = (baseline_value - current_value) / abs(baseline_value) * 100
    elif direction == "deviation":
        rate = abs(current_value - baseline_value) / abs(baseline_value) * 100
    else:
        rate = 0.0

    return max(0.0, rate)


def get_level_description(level: int) -> str:
    """
    레벨 숫자에 대응하는 한글 설명을 반환한다.

    매개변수:
        level: 0~5 사이의 취도 레벨

    반환값:
        레벨에 대응하는 한글 설명 문자열
    """
    descriptions = {
        0: "멀쩡해요",
        1: "살짝 취기",
        2: "기분 좋은 취기",
        3: "제법 취함",
        4: "많이 취함",
        5: "만취",
    }
    return descriptions.get(level, "알 수 없음")
