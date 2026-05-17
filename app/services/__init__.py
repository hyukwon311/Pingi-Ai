"""
서비스 패키지 (비즈니스 로직 계층)

음성 분석의 전체 파이프라인을 구성하는 서비스 모듈들을 포함한다.
각 서비스는 단일 책임 원칙(SRP)에 따라 하나의 역할만 수행한다.

음성 분석 파이프라인 흐름:
    ┌──────────────┐    ┌───────────────────┐    ┌──────────────┐
    │ audio_       │    │ feature_          │    │ analyzer     │
    │ converter    │───▶│ extractor         │───▶│              │
    │              │    │                   │    │              │
    │ webm → wav   │    │ openSMILE 7피처   │    │ 베이스라인    │
    │ 포맷 변환    │    │ + librosa speed   │    │ 대비 취도 계산│
    └──────────────┘    └───────────────────┘    └──────────────┘

모듈 구성:
    audio_converter.py   - 오디오 포맷 변환 (webm/m4a → wav)
    feature_extractor.py - openSMILE eGeMAPSv02 + librosa 음향 특징 추출
    analyzer.py          - 베이스라인 대비 취도 분석 (파이프라인 통합)
"""

from .analyzer import analyze_baseline_audios, analyze_single_audio

__all__ = [
    "analyze_baseline_audios",
    "analyze_single_audio",
]
