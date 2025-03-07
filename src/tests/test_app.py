import asyncio
import uuid
import anyio
import pytest
import jwt
from httpx import AsyncClient, ASGITransport
from fastapi import status
from app import app
from core.config import setting

default_payload = {
    "miner_hotkey": "test_miner_hotkey",
    "amount_in_usd": 100.0,
    "billing_history_id": "test_billing_history_id"
}


def create_jwt_token():
    """Helper function to create a JWT token for testing."""
    payload = {
        "sub": "test_user",
        "jti": str(uuid.uuid4()),
        "exp": 9999999999  # Set a far future expiration for testing
    }
    token = jwt.encode(payload, setting.JWT_SECRET_KEY, algorithm=setting.JWT_ALGORITHM)
    return token


@pytest.mark.anyio
async def test_sequential_requests():
    token = create_jwt_token()
    
    async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as client:
        # Send two requests and ensure they are processed sequentially
        responses = await asyncio.gather(
            client.post("/api/v1/transfers", json=default_payload, headers={
                'Authorization': f'Bearer {create_jwt_token()}'
            }),
            client.post("/api/v1/transfers", json=default_payload, headers={
                'Authorization': f'Bearer {create_jwt_token()}'
            })
        )
        response1, response2 = responses
        
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK