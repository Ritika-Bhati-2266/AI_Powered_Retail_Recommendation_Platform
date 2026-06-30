"""
Currency conversion helper with hardcoded rates.
All prices are stored in USD in the database.
Conversion happens server-side based on customer's stored currency preference.
"""
from typing import Optional

# Hardcoded fixed conversion rates (USD -> target)
CURRENCY_CONFIG: dict[str, dict] = {
    "USD": {"symbol": "$", "rate_to_usd": 1.0},
    "INR": {"symbol": "₹", "rate_to_usd": 83.0},
    "EUR": {"symbol": "€", "rate_to_usd": 0.92},
}

DEFAULT_CURRENCY = "USD"


def convert_price(price_usd: float, target_currency: Optional[str] = None) -> tuple[float, str, str]:
    """
    Convert price from USD to target currency.
    Returns (converted_price, currency_code, symbol).
    Prices stored in USD in the DB; converted server-side.
    """
    target = target_currency or DEFAULT_CURRENCY
    config = CURRENCY_CONFIG.get(target)
    if not config:
        # Unknown currency, return as USD
        return price_usd, "USD", "$"

    rate = config["rate_to_usd"]
    converted = price_usd * rate

    # Round appropriately
    if target == "INR":
        converted = int(round(converted))  # INR has no paise in display
    elif target == "JPY":
        converted = int(round(converted))
    else:
        converted = round(converted, 2)

    return converted, target, config["symbol"]


def get_available_currencies() -> dict[str, str]:
    """Return dict of currency code -> symbol for the selector UI."""
    return {code: cfg["symbol"] for code, cfg in CURRENCY_CONFIG.items()}
