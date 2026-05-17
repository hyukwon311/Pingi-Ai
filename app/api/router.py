"""
API 라우터 통합

디렉토리 내의 모든 엔드포인트 라우터를 하나로 합친다.
main.py에서 이 라우터를 /api/v1 접두사로 마운트하면
아래와 같은 URL 구조가 완성된다:

    GET  /api/v1/health            → health.py
    POST /api/v1/analyze/baseline  → baseline.py
    POST /api/v1/analyze/recording → recording.py

새 엔드포인트를 추가하려면:
    1. app/api/ 디렉토리에 새 모듈 생성 (예: feedback.py)
    2. 해당 모듈에서 router = APIRouter() 정의
    3. 이 파일에서 include_router() 호출
"""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.baseline import router as baseline_router
from app.api.recording import router as recording_router

api_router = APIRouter()

api_router.include_router(
    health_router,
    tags=["모니터링"],
)

api_router.include_router(
    baseline_router,
    tags=["음성 분석"],
)

api_router.include_router(
    recording_router,
    tags=["음성 분석"],
)
