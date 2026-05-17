"""
핑이타임 녹음 분석 엔드포인트

술자리 도중 15분 간격(또는 수동)으로 멤버가 녹음한 음성에서
9개 음향 피처를 추출하여 반환한다.
변화율/취도 계산은 pingi-backend에서 수행한다.

엔드포인트:
    POST /api/v1/analyze/recording

요청 (multipart/form-data):
    - audio (file): 핑이타임 녹음 파일 (webm/wav)
    - sentence (string): 이번 핑이타임의 기대 문장

응답:
    {
        "features": {
            "jitter": 0.018, "shimmer": 0.62, "hnr": 9.8,
            "f1": 0.35, "f2": 0.28, "loudness": 0.42,
            "f0": 30.1, "f0_var": 0.078, "speed": 0.72
        }
    }

호출 시점 (pingi-backend 기준):
    POST /v1/checkpoints/:id/recordings 처리 시
    checkpointService.ts → voiceAnalysisService.ts에서 이 엔드포인트를 호출한다.
"""

import logging

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.models.schemas import RecordingResponse, RecordingFeatures, ErrorResponse
from app.services.analyzer import analyze_single_audio

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze/recording",
    response_model=RecordingResponse,
    responses={
        400: {"model": ErrorResponse, "description": "오디오 파일 또는 문장 누락"},
        500: {"model": ErrorResponse, "description": "피처 추출 중 내부 오류 발생"},
    },
    summary="핑이타임 녹음 피처 추출",
    description="핑이타임 녹음에서 9개 음향 피처를 추출한다. "
                "pingi-backend가 핑이타임 녹음 제출 시 호출한다.",
)
async def analyze_recording(
    audio: UploadFile = File(
        ...,
        description="핑이타임 녹음 파일 (webm/wav)",
    ),
    sentence: str = Form(
        ...,
        description="이번 핑이타임의 기대 문장. 예) '경찰청 철창살은...'",
    ),
) -> RecordingResponse:
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "EMPTY_AUDIO", "message": "오디오 파일이 비어있습니다"}},
            )

        filename = audio.filename or "recording.webm"

        logger.info(
            "핑이타임 피처 추출 요청: file=%s, sentence='%s'",
            filename,
            sentence[:30],
        )

        result = analyze_single_audio(audio_bytes, filename, sentence)

        features = RecordingFeatures(
            jitter=round(result["jitter"], 6),
            shimmer=round(result["shimmer"], 4),
            hnr=round(result["hnr"], 2),
            f1=round(result["f1"], 4),
            f2=round(result["f2"], 4),
            loudness=round(result["loudness"], 4),
            f0=round(result["f0"], 2),
            f0_var=round(result["f0_var"], 4),
            speed=round(result["speed"], 4),
        )

        return RecordingResponse(features=features)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("핑이타임 피처 추출 실패")
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "EXTRACTION_FAILED", "message": f"피처 추출 중 오류 발생: {e}"}},
        )
