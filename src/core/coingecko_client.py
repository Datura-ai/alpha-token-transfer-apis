from decimal import Decimal

import requests


class CoinGeckoClient:
    def __init__(self):
        self.url = "https://api.coingecko.com/api/v3/coins/bittensor"

    def get_currency_rate(self) -> float:
        response = requests.get(self.url)
        response.raise_for_status()

        rate_float = response.json()["market_data"]["current_price"]["usd"]
        return float(Decimal(str(rate_float)))

    def convert_to_tao(self, amount: float) -> tuple[float, float]:
        current_rate = self.get_currency_rate()
        return amount / current_rate, current_rate


coingecko_client = CoinGeckoClient()