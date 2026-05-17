"""
pingi-ai 메인 엔트리포인트

핑이(Pingi) 서비스의 음성 분석 AI 서버이다.
pingi-backend로부터 HTTP 요청을 받아 음성 파일을 분석하고,
취도(score, level, changeRate)를 반환한다.

음향 분석 엔진: openSMILE eGeMAPSv02 (7피처) + librosa (발화 속도)

실행 방법:
    # 개발 서버 (자동 리로드)
    uvicorn main:app --port 8001 --reload

    # 프로덕션 서버
    uvicorn main:app --port 8001 --workers 2

API 문서:
    서버 실행 후 http://localhost:8001/docs 에서 Swagger UI 확인 가능

아키텍처:
    pingi-front (React) → pingi-backend (Express) → [pingi-ai (이 서버)]
    - pingi-front는 pingi-ai를 직접 호출하지 않는다.
    - 모든 요청은 pingi-backend를 거쳐서 온다.
    - pingi-ai는 순수하게 음성 분석만 담당한다.
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.router import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="pingi-ai",
    description=(
        "핑이(Pingi) 음성 분석 AI 서버.\n\n"
        "술자리에서 녹음한 음성을 분석하여 음향 특징 변화율 기반의 취도(0~5 레벨)를 판정한다.\n"
        "openSMILE eGeMAPSv02로 7가지 음향 피처를 추출하고, librosa로 발화 속도를 측정한다.\n"
        "pingi-backend에서 HTTP로 호출하며, 프론트엔드가 직접 접근하지 않는다."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def on_startup() -> None:
    """서버 시작 시 실행되는 초기화 작업."""
    os.makedirs(settings.temp_dir, exist_ok=True)

    logger.info("=" * 60)
    logger.info("pingi-ai 서버 시작")
    logger.info("  버전:         %s", settings.app_version)
    logger.info("  포트:         %s", settings.port)
    logger.info("  분석 엔진:    openSMILE eGeMAPSv02 + librosa")
    logger.info("  임시 디렉토리: %s", settings.temp_dir)
    logger.info("  API 문서:     http://localhost:%s/docs", settings.port)
    logger.info("=" * 60)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """서버 종료 시 임시 디렉토리의 잔여 파일을 정리한다."""
    logger.info("pingi-ai 서버 종료")
    if os.path.exists(settings.temp_dir):
        for filename in os.listdir(settings.temp_dir):
            filepath = os.path.join(settings.temp_dir, filename)
            try:
                os.remove(filepath)
            except OSError:
                pass
