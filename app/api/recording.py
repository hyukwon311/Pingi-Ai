"""
핑이타임 녹음 분석 엔드포인트

술자리 도중 15분 간격(또는 수동)으로 멤버가 녹음한 음성에서
9개 음향 피처를 추출하고, 베이스라인 대비 변화율 및 취도 레벨을 산출한다.

엔드포인트:
    POST /api/v1/analyze/recording

요청 (multipart/form-data):
    - audio (file): 핑이타임 녹음 파일 (webm/wav)
    - sentence (string): 이번 핑이타임의 기대 문장
    - baseline (string): 베이스라인 피처 JSON 문자열

응답:
    {
        "features": { "jitter": 0.018, ..., "speed": 0.72 },
        "change_rate": 23.5,
        "level": 2,
        "level_description": "기분 좋은 취기"
    }

호출 시점 (pingi-backend 기준):
    POST /v1/checkpoints/:id/recordings 처리 시
    checkpointService.ts → voiceAnalysisService.ts에서 이 엔드포인트를 호출한다.
"""

import json
import logging

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from pydantic import ValidationError

from app.models.schemas import RecordingResponse, BaselineFeatures, ErrorResponse
from app.services.analyzer import analyze_recording

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze/recording",
    response_model=RecordingResponse,
    responses={
        400: {"model": ErrorResponse, "description": "오디오 파일, 문장 또는 baseline 누락/형식 오류"},
        500: {"model": ErrorResponse, "description": "피처 추출 중 내부 오류 발생"},
    },
    summary="핑이타임 녹음 분석",
    description="핑이타임 녹음에서 9개 음향 피처를 추출하고 베이스라인 대비 변화율/취도를 산출한다. "
                "pingi-backend가 핑이타임 녹음 제출 시 호출한다.",
)
async def analyze_recording_endpoint(
    audio: UploadFile = File(
        ...,
        description="핑이타임 녹음 파일 (webm/wav)",
    ),
    sentence: str = Form(
        ...,
        description="이번 핑이타임의 기대 문장. 예) '경찰청 철창살은...'",
    ),
    baseline: str = Form(
        ...,
        description='베이스라인 피처 JSON. 예) \'{"jitter":0.012,"shimmer":0.45,...}\'',
    ),
) -> RecordingResponse:
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "EMPTY_AUDIO", "message": "오디오 파일이 비어있습니다"}},
            )

        try:
            baseline_data = json.loads(baseline)
            baseline_features = BaselineFeatures(**baseline_data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "INVALID_BASELINE", "message": f"baseline JSON 형식이 올바르지 않습니다: {e}"}},
            )

        filename = audio.filename or "recording.webm"

        logger.info(
            "핑이타임 분석 요청: file=%s, sentence='%s'",
            filename,
            sentence[:30],
        )

        return analyze_recording(audio_bytes, filename, sentence, baseline_features)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("핑이타임 분석 실패")
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "ANALYSIS_FAILED", "message": f"분석 중 오류 발생: {e}"}},
        )
