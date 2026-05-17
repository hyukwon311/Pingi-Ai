"""
오디오 포맷 변환 서비스

브라우저의 MediaRecorder API로 녹음하면 webm(Opus) 포맷이 생성된다.
openSMILE과 librosa는 wav 포맷에서 가장 안정적으로 동작하므로,
분석 전에 모든 오디오 파일을 16kHz 모노 wav로 통일한다.

변환 스펙:
    - 입력: webm, m4a, mp3, ogg 등 (ffmpeg가 지원하는 모든 포맷)
    - 출력: wav (16kHz, 모노, 16bit PCM)
    - 의존성: pydub + ffmpeg (시스템에 ffmpeg 설치 필요)

왜 16kHz 모노인가:
    - 음성 피처 분석(jitter, shimmer, HNR 등)에 16kHz면 충분하다
    - 모노 채널이면 스테레오 대비 처리 속도가 2배 빠르다
    - 음성 분석에 스테레오 정보는 불필요하다
"""

import os
import uuid
import logging

from pydub import AudioSegment

from app.config import settings

logger = logging.getLogger(__name__)

# 음성 피처 분석용 샘플링 레이트
_TARGET_SAMPLE_RATE = 16000

# 음성 분석용 채널 수 (모노)
_TARGET_CHANNELS = 1


def ensure_temp_dir() -> None:
    """임시 디렉토리가 존재하지 않으면 생성한다."""
    os.makedirs(settings.temp_dir, exist_ok=True)


def convert_to_wav(input_bytes: bytes, original_filename: str) -> str:
    """
    업로드된 오디오 바이트를 16kHz 모노 wav 파일로 변환한다.

    매개변수:
        input_bytes:      업로드된 오디오 파일의 바이트 데이터
        original_filename: 원본 파일명. 확장자로 입력 포맷을 판별한다.
                           예) "recording.webm", "voice.m4a"

    반환값:
        변환된 wav 파일의 절대 경로.
        호출자가 사용 후 cleanup_temp_file()로 삭제해야 한다.

    예외:
        RuntimeError: ffmpeg가 설치되지 않았거나 변환에 실패한 경우
    """
    ensure_temp_dir()

    # 원본 확장자 추출 (webm, m4a, mp3 등)
    _, ext = os.path.splitext(original_filename)
    ext = ext.lstrip(".").lower() or "webm"

    # 고유 파일명으로 임시 파일 생성 (동시 요청 시 충돌 방지)
    temp_id = uuid.uuid4().hex[:12]
    input_path = os.path.join(settings.temp_dir, f"{temp_id}_input.{ext}")
    output_path = os.path.join(settings.temp_dir, f"{temp_id}_output.wav")

    try:
        # 1단계: 업로드된 바이트를 임시 파일로 저장
        with open(input_path, "wb") as f:
            f.write(input_bytes)

        # 2단계: pydub(ffmpeg)로 포맷 변환
        audio = AudioSegment.from_file(input_path, format=ext)
        audio = audio.set_frame_rate(_TARGET_SAMPLE_RATE)
        audio = audio.set_channels(_TARGET_CHANNELS)
        audio.export(output_path, format="wav")

        logger.info(
            "오디오 변환 완료: %s → wav (duration=%.1fs, sr=%dHz)",
            ext,
            len(audio) / 1000,
            _TARGET_SAMPLE_RATE,
        )

        return output_path

    except Exception as e:
        # 변환 실패 시 출력 파일도 정리
        cleanup_temp_file(output_path)
        raise RuntimeError(f"오디오 변환 실패 ({ext} → wav): {e}") from e

    finally:
        # 입력 임시 파일은 항상 삭제
        cleanup_temp_file(input_path)


def cleanup_temp_file(file_path: str) -> None:
    """
    임시 파일을 안전하게 삭제한다.

    파일이 존재하지 않아도 에러를 발생시키지 않는다.
    분석 완료 후 호출하여 디스크 공간을 확보한다.

    매개변수:
        file_path: 삭제할 파일의 경로
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError as e:
        logger.warning("임시 파일 삭제 실패: %s (%s)", file_path, e)
