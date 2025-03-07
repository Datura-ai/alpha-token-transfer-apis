import uuid
import click
import secrets
import base64
from cryptography.fernet import Fernet
import hashlib
import jwt
from core.config import setting
import requests

def create_jwt_token():
    """Helper function to create a JWT token for testing."""
    payload = {
        "sub": "test_user",
        "jti": str(uuid.uuid4()),
        "exp": 9999999999  # Set a far future expiration for testing
    }
    token = jwt.encode(payload, setting.JWT_SECRET_KEY, algorithm=setting.JWT_ALGORITHM)
    return token

@click.group()
def cli():
    pass

@cli.command()
@click.option('--length', default=32, help='Length of the generated JWT secret key')
def generate_jwt_secret(length):
    """Generate a secure random string suitable for a JWT secret key."""
    # Generate random bytes
    random_bytes = secrets.token_bytes(length)
    
    # Convert to base64 for readability and usability
    jwt_secret = base64.b64encode(random_bytes).decode('utf-8')

    print(f"JWT_SECRET_KEY={jwt_secret}")
    
    return jwt_secret

@cli.command()
@click.option('--mnemonic', type=str, prompt="Mnemonic phrase", help='Mnemonic phrase')
@click.option('--password', type=str, prompt="Password to encrypt the mnemonic", help='Password for the cipher text')
def generate_cipher_text(mnemonic: str, password: str):
    """Generate a secure random string suitable for a cipher text."""
    # Derive a key from the password
    password_bytes = password.encode('utf-8')
    key = hashlib.sha256(password_bytes).digest()
    fernet = Fernet(base64.urlsafe_b64encode(key))

    # Encrypt the mnemonic
    mnemonic_bytes = mnemonic.encode('utf-8')
    cipher_text = fernet.encrypt(mnemonic_bytes).decode('utf-8')

    print(f"cipher_text={cipher_text}")

    return cipher_text

@cli.command()
@click.option('--amount_in_usd', type=float, prompt="Amount in USD", help='Amount in USD')
@click.option('--miner_coldkey', type=str, prompt="Miner coldkey", help='Miner coldkey')
def transfer_balance(amount_in_usd: float, miner_coldkey: str):
    """Transfer balance from the hotkey to the miner coldkey."""
    server_url = "http://localhost:8000"
    response = requests.post(
        f"{server_url}/api/v1/transfers",
        json={
            "amount_in_usd": amount_in_usd,
            "miner_coldkey": miner_coldkey,
            "billing_history_id": "123",
        },
        headers={"Authorization": f"Bearer {create_jwt_token()}"},
    )
    print(response.json())
if __name__ == "__main__":
    cli()