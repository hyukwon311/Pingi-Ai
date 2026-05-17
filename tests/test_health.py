"""
헬스 체크 엔드포인트 테스트

테스트 대상:
    GET /api/v1/health

검증 항목:
    - 응답 상태 코드가 200인지
    - 응답 body에 status, model, version 필드가 있는지
    - status 값이 "ok"인지

실행:
    pytest tests/test_health.py -v
"""

import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
async def test_health_returns_ok():
    """헬스 체크가 200 OK와 함께 status="ok"를 반환하는지 확인한다."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert "model" in body
    assert "version" in body
