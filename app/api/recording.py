"""
핑이타임 녹음 분석 엔드포인트

술자리 도중 15분 간격(또는 수동)으로 멤버가 녹음한 음성을
베이스라인과 비교하여 현재 취도를 판정한다.

엔드포인트:
    POST /api/v1/analyze/recording

요청 (multipart/form-data):
    - audio (file): 핑이타임 녹음 파일 (webm/wav)
    - sentence (string): 이번 핑이타임의 기대 문장
    - baselineFeatures (string, JSON): 해당 멤버의 베이스라인 특성값
      예) '{"jitter": 0.012, "shimmer": 0.45, "hnr": 12.3, ...}'

응답:
    {
        "score": 0.35,
        "level": 2,
        "changeRate": 23.5,
        "detail": {
            "currentJitter": 0.018,
            "currentShimmer": 0.62,
            "currentHnr": 9.8,
            "currentF1": 495.0,
            "currentF2": 1520.0,
            "currentLoudness": 0.42,
            "currentF0": 30.1,
            "currentSpeed": 0.72
        }
    }

호출 시점 (pingi-backend 기준):
    POST /v1/checkpoints/:id/recordings 처리 시
    checkpointService.ts → voiceAnalysisService.ts에서 이 엔드포인트를 호출한다.
"""

import json
import logging

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.models.schemas import BaselineFeatures, RecordingResponse, ErrorResponse
from app.services.analyzer import analyze_recording_audio

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze/recording",
    response_model=RecordingResponse,
    responses={
        400: {"model": ErrorResponse, "description": "오디오, 문장, 또는 베이스라인 누락/형식 오류"},
        500: {"model": ErrorResponse, "description": "분석 중 내부 오류 발생"},
    },
    summary="핑이타임 녹음 분석",
    description="현재 녹음을 베이스라인과 비교하여 취도(score, level, changeRate)를 계산한다. "
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
    baselineFeatures: str = Form(
        ...,
        description='해당 멤버의 베이스라인 특성값 (JSON 문자열). '
                    '예) \'{"jitter": 0.012, "shimmer": 0.45, "hnr": 12.3, ...}\'',
    ),
) -> RecordingResponse:
    """
    핑이타임 녹음을 분석하여 취도를 판정한다.

    처리 과정:
        1. baselineFeatures JSON 문자열을 파싱하여 BaselineFeatures 객체로 변환
        2. 오디오 파일을 wav로 변환 후 openSMILE + librosa 음향 분석
        3. 베이스라인 대비 변화율 계산 → level, score 산출

    매개변수:
        audio:            핑이타임 녹음 파일 (multipart file)
        sentence:         기대 문장 텍스트 (multipart form field)
        baselineFeatures: 베이스라인 특성값 JSON 문자열 (multipart form field)

    반환값:
        RecordingResponse: score(0~1), level(0~5), changeRate(%), detail(상세 데이터)

    에러:
        400: - 오디오 파일이 비어있는 경우
             - baselineFeatures가 유효한 JSON이 아닌 경우
             - baselineFeatures에 필수 필드가 누락된 경우
        500: 음향 분석 중 예외 발생
    """
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "EMPTY_AUDIO", "message": "오디오 파일이 비어있습니다"}},
            )

        try:
            features_dict = json.loads(baselineFeatures)
            baseline = BaselineFeatures(**features_dict)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_BASELINE",
                        "message": f"baselineFeatures 형식이 올바르지 않습니다: {e}",
                    }
                },
            )

        filename = audio.filename or "recording.webm"

        logger.info(
            "핑이타임 분석 요청: file=%s, sentence='%s', baseline={jitter=%.4f, shimmer=%.3f, hnr=%.1f}",
            filename,
            sentence[:30],
            baseline.jitter,
            baseline.shimmer,
            baseline.hnr,
        )

        result = await analyze_recording_audio(audio_bytes, filename, sentence, baseline)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("핑이타임 분석 실패")
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "ANALYSIS_FAILED", "message": f"녹음 분석 중 오류 발생: {e}"}},
        )
