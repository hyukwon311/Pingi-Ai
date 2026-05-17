"""
헬스 체크 엔드포인트

pingi-backend가 기동 시 pingi-ai 서버의 상태를 확인하는 용도이다.
AI 서버가 응답하지 않으면 백엔드는 Mock fallback 모드로 동작한다.

엔드포인트:
    GET /api/v1/health

응답 예시:
    {
        "status": "ok",
        "model": "opensmile-eGeMAPSv02",
        "version": "0.1.0"
    }
"""

from fastapi import APIRouter

from app.config import settings
from app.models.schemas import HealthResponse

router = APIRouter()

_MODEL_NAME = "opensmile-eGeMAPSv02"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="서버 상태 확인",
    description="pingi-ai 서버가 정상 동작 중인지 확인한다. "
                "사용 중인 음향 분석 모델 이름과 서버 버전을 함께 반환한다.",
)
async def health_check() -> HealthResponse:
    """
    서버 헬스 체크.

    pingi-backend가 주기적으로 호출하여 AI 서버 사용 가능 여부를 판단한다.
    이 엔드포인트가 200을 반환하면 정상, 그 외에는 fallback 모드로 전환.

    반환값:
        HealthResponse:
            - status:  "ok" (고정)
            - model:   "opensmile-eGeMAPSv02"
            - version: pingi-ai 서버 버전. 예) "0.1.0"
    """
    return HealthResponse(
        status="ok",
        model=_MODEL_NAME,
        version=settings.app_version,
    )
