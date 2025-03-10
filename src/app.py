import os
import sys
import time
import traceback
import uuid
import async_substrate_interface
import jwt
import getpass
import base64
import hashlib
import asyncio
from bittensor.utils.balance import Balance
from bittensor_wallet.keypair import Keypair
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from core.config import setting
from core.utils import batch_transfer_balances, get_substrate, transfer_balance
from schema import TransferRequest, TransferResponse

# Create a semaphore with a value of 1 (only one request at a time)
# Try to process transfer request sequentially, rather than in parallel
request_semaphore = asyncio.Semaphore(1)

async def get_semaphore():
    async with request_semaphore:
        yield

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="Alpha Token Transfer API",
    description="Secure microservice for handling token transfers",
    version="1.0.0"
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security bearer token scheme
security = HTTPBearer()

# JWT validation function
def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        
        # Decode and verify the JWT
        payload = jwt.decode(
            token, 
            setting.JWT_SECRET_KEY, 
            algorithms=[setting.JWT_ALGORITHM],
            options={"verify_signature": True, "verify_exp": True}
        )
        
        # Verify token has not been used before (nonce check)
        if "jti" in payload:
            jti = payload["jti"]

            # In production, use Redis for distributed nonce tracking
            if jti in getattr(app.state, "used_tokens", set()):
                logger.warning(f"Token reuse detected: {jti}")
                raise HTTPException(status_code=401, detail="Token has been used before")
            
            # Mark this token as used
            if not hasattr(app.state, "used_tokens"):
                app.state.used_tokens = set()
            app.state.used_tokens.add(jti)

            if len(app.state.used_tokens) > setting.MAX_USED_TOKENS:
                logger.info("Resetting used_tokens set to prevent memory overflow")
                app.state.used_tokens.clear()

        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )
    

# Middleware for request validation and logging
@app.middleware("http")
async def validate_request(request: Request, call_next):
    # Record request time for monitoring
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Add request_id to request state for logging
    request.state.request_id = request_id
    
    # Log the incoming request
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Request {request_id}: {request.method} {request.url.path} from {client_host}")
    
    # Process the request
    try:
        response = await call_next(request)
        
        # Log response details
        process_time = time.time() - start_time
        status_code = response.status_code
        logger.info(
            f"Response {request_id}: Status {status_code}, "
            f"Completed in {process_time:.3f}s"
        )
        
        # Add request ID to response headers for tracing
        response.headers["X-Request-ID"] = request_id
        
        return response
    except Exception as e:
        # Log any unhandled exceptions
        process_time = time.time() - start_time
        logger.error(
            f"Error {request_id}: {str(e)}, "
            f"Occurred after {process_time:.3f}s"
        )
        raise


# API endpoints
@app.post("/api/v1/transfers", response_model=TransferResponse)
@limiter.limit("60/minute")  # Rate limiting
async def process_transfer(
    transfer: TransferRequest,
    payload: dict = Depends(verify_jwt_token),
    request: Request = None,
    dependencies = Depends(get_semaphore)
):
    """Process a money transfer between accounts"""
    # Get request ID from middleware
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.info(f"Processing transfer: {request_id}, Transaction ID: {transfer.transaction_id}")

    # Load the keypair.
    try:
        keypair = Keypair.create_from_mnemonic(setting.decrypted_wallet_secret)
    except Exception as exc:
        logger.error(f"Failed to initialize wallet: {exc}")
        return
    
    consecutive_failures = 0
    while True:
        try:
            substrate = await get_substrate()
            batch_transfer_balances(substrate, keypair, transfer.transfers_dict)
            break
        except async_substrate_interface.errors.SubstrateRequestException as exc:
            logger.error(f"Substrate request exception: {exc}")
            if "Invalid Transaction" in str(exc):
                return TransferResponse(
                    transaction_id=transfer.transaction_id,
                    status="error",
                    message="Invalid transaction"
                )
        except Exception as exc:
            logger.error(
                f"Unhandled exception performing transfer operation: {exc}\n{traceback.format_exc()}"
            )
            return TransferResponse(
                transaction_id=transfer.transaction_id,
                status="error",
                message="Unhandled exception"
            )
            
        await asyncio.sleep(5)
        setting.substrate = None
        consecutive_failures += 1
        if consecutive_failures >= 5:
            logger.error(
                "Giving up transfer, max consecutive failures reached {keypair.ss58_address=}"
            )
            return TransferResponse(
                transaction_id=transfer.transaction_id,
                status="error",
                message="Max consecutive failures reached"
            )
        
    return TransferResponse(
        transaction_id=transfer.transaction_id,
        status="success",
        message="Transfer processed successfully"
    )

if __name__ == "__main__":
    password = getpass.getpass(prompt='Please enter your password: ')
    setting.password = password

    # Derive a key from the password
    password_bytes = password.encode('utf-8')
    key = hashlib.sha256(password_bytes).digest()
    fernet = Fernet(base64.urlsafe_b64encode(key))

    try:
        # Decrypt the cipher text
        setting.decrypted_wallet_secret = fernet.decrypt(setting.cipher_text.encode('utf-8')).decode('utf-8')
        logger.info("Password is correct. Successfully decrypted the cipher text")
    except Exception as e:
        logger.error(f"Failed to decrypt cipher text: {str(e)}")
        sys.exit(1)

    # Launch the FastAPI app
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
