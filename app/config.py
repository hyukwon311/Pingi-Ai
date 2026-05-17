"""
pingi-ai 서버 설정 모듈

환경 변수(.env 파일)로부터 서버 실행에 필요한 설정값을 로드한다.
pydantic-settings를 사용하여 타입 안전성과 기본값을 보장한다.

사용 예시:
    from app.config import settings
    print(settings.port)  # 8001
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    pingi-ai 서버 전체 설정

    각 필드는 환경 변수와 1:1로 매핑된다.
    예) PORT 환경 변수 → settings.port
    """

    # --- 서버 설정 ---
    port: int = 8001
    """서버 실행 포트. pingi-backend(8000)와 충돌하지 않도록 8001 사용."""

    # --- 임시 파일 경로 ---
    temp_dir: str = "./tmp"
    """업로드된 오디오 파일의 포맷 변환 시 사용하는 임시 디렉토리 경로."""

    # --- 앱 메타데이터 ---
    app_version: str = "0.1.0"
    """API 버전. 헬스 체크 응답에 포함된다."""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# 싱글턴 인스턴스: 앱 전체에서 `from app.config import settings`로 접근
settings = Settings()
