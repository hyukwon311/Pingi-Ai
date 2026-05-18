"""
베이스라인 분석 엔드포인트

술자리 시작 전, 멤버가 맨정신 상태에서 잰말 문장 1개를 녹음한다.
이 녹음을 분석하여 개인 음성 기준선(baseline features)을 생성한다.
pingi-backend는 이 features를 DB에 저장하고,
이후 핑이타임에서 이 기준선 대비 변화율로 취도를 판정한다.

엔드포인트:
    POST /api/v1/analyze/baseline

요청 (multipart/form-data):
    - audio (file): 녹음 파일 (webm/wav)
    - sentence (string): 문장 텍스트

응답:
    {
        "features": {
            "jitter": 0.012, "shimmer": 0.45, "hnr": 12.3,
            "f1": 0.25, "f2": 0.18, "loudness": 0.35,
            "f0": 28.5, "f0_var": 0.045, "speed": 0.88
        }
    }

호출 시점 (pingi-backend 기준):
    POST /v1/members/:id/baseline/complete 처리 시
    baselineService.ts에서 이 엔드포인트를 호출한다.
"""

import logging

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.models.schemas import BaselineResponse, ErrorResponse
from app.services.analyzer import analyze_baseline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze/baseline",
    response_model=BaselineResponse,
    responses={
        400: {"model": ErrorResponse, "description": "오디오 파일 또는 문장 누락"},
        500: {"model": ErrorResponse, "description": "분석 중 내부 오류 발생"},
    },
    summary="베이스라인 음성 분석",
    description="맨정신 상태의 음성 1개를 분석하여 개인 음성 기준선(features)을 생성한다. "
                "pingi-backend가 baseline complete 시점에 호출한다.",
)
async def analyze_baseline_endpoint(
    audio: UploadFile = File(
        ...,
        description="베이스라인 녹음 파일 (webm/wav)",
    ),
    sentence: str = Form(
        ...,
        description="녹음의 기대 문장. 예) '간장 공장 공장장은...'",
    ),
) -> BaselineResponse:
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "EMPTY_AUDIO", "message": "오디오 파일이 비어있습니다"}},
            )

        filename = audio.filename or "baseline.webm"

        logger.info(
            "베이스라인 분석 요청: file=%s, sentence='%s'",
            filename,
            sentence[:30],
        )

        return analyze_baseline(audio_bytes, filename, sentence)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("베이스라인 분석 실패")
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "ANALYSIS_FAILED", "message": f"베이스라인 분석 중 오류 발생: {e}"}},
        )
