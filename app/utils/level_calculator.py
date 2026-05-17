"""
취도 레벨 계산기

베이스라인 대비 발음 변화율(changeRate)을 0~5 레벨로 변환한다.
이 모듈의 계산 공식은 pingi-backend의 utils/levelCalculator.ts와
정확히 동일하게 유지해야 한다. 두 곳의 공식이 다르면 프론트엔드에
표시되는 레벨이 불일치할 수 있다.

레벨 기준표:
    레벨 0 (멀쩡해요)       : 변화율 < 5%
    레벨 1 (살짝 취기)      : 5% ≤ 변화율 < 15%
    레벨 2 (기분 좋은 취기)  : 15% ≤ 변화율 < 30%
    레벨 3 (제법 취함)       : 30% ≤ 변화율 < 50%
    레벨 4 (많이 취함)       : 50% ≤ 변화율 < 70%
    레벨 5 (만취)            : 변화율 ≥ 70%

pingi-backend 원본:
    pingi-backend/src/utils/levelCalculator.ts
"""


# 음주 시 각 피처의 변화 방향 정의.
# "increase": 취하면 값이 증가 → (current - baseline) / baseline
# "decrease": 취하면 값이 감소 → (baseline - current) / baseline
# "deviation": 취하면 편차가 커짐 → abs(current - baseline) / baseline
DRUNK_DIRECTION: dict[str, str] = {
    "jitter": "increase",
    "shimmer": "increase",
    "hnr": "decrease",
    "f1": "deviation",
    "f2": "deviation",
    "loudness": "increase",
    "f0": "increase",
    "speed": "decrease",
}


def calculate_level(change_rate: float) -> int:
    """
    변화율(%)을 취도 레벨(0~5)로 변환한다.

    pingi-backend의 calculateLevel()과 동일한 구간 기준을 사용한다.
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

    pingi-backend의 getLevelDescription()과 동일한 문구를 사용한다.

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
