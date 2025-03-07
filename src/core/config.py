import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from async_substrate_interface.sync_substrate import SubstrateInterface

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    cipher_text: str = os.getenv("CIPHER_TEXT")
    subtensor: str = os.getenv("SUBTENSOR_ADDRESS", "wss://test.finney.opentensor.ai:443")
    net_uid: int = os.getenv("NET_UID", 51)
    hotkey: str | None = os.getenv("HOTKEY")
    password: str | None = None
    decrypted_wallet_secret: str | None = None
    substrate: SubstrateInterface | None = None
    
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = 'HS256'
    TOKEN_EXPIRE_MINUTES: int = 30
    MAX_USED_TOKENS: int = 1000

setting = Settings()