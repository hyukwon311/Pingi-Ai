"""
데이터 모델 패키지

API 요청/응답에 사용되는 Pydantic 스키마를 정의한다.
FastAPI가 자동으로 OpenAPI 문서를 생성할 수 있도록 모든 필드에
타입과 설명을 명시한다.

모듈 구성:
    schemas.py - 요청/응답 데이터 모델 (BaselineResponse, RecordingResponse 등)
"""

from .schemas import (
    BaselineFeatures,
    BaselineResponse,
    RecordingFeatures,
    RecordingResponse,
    HealthResponse,
    ErrorDetail,
    ErrorResponse,
)

__all__ = [
    "BaselineFeatures",
    "BaselineResponse",
    "RecordingFeatures",
    "RecordingResponse",
    "HealthResponse",
    "ErrorDetail",
    "ErrorResponse",
]
