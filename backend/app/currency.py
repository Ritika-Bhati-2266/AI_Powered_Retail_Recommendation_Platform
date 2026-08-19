"""
Currency conversion helper with hardcoded rates.
All prices are stored in USD in the database.
Conversion happens server-side based on customer's stored currency preference.
"""

# Hardcoded fixed conversion rates (USD -> target)
CURRENCY_CONFIG: dict[str, dict] = {
    "USD": {"symbol": "$", "rate_to_usd": 1.0},
    "INR": {"symbol": "₹", "rate_to_usd": 83.0},
    "EUR": {"symbol": "€", "rate_to_usd": 0.92},
    "JPY": {"symbol": "¥", "rate_to_usd": 150.0},
}

DEFAULT_CURRENCY = "USD"


def convert_price(price_usd: float, target_currency: str | None = None) -> tuple[float, str, str]:
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
    if target in ("INR", "JPY"):
        converted = round(converted)  # whole numbers (no sub-unit fares)
    else:
        converted = round(converted, 2)

    return converted, target, config["symbol"]


def price_to_usd(amount: float, source_currency: str | None = None) -> float:
    """Convert an amount stored in a local currency back to USD.

    Orders store line-item prices in the customer's display currency (see
    ``orders.place_order``), while every business metric — LTV, segment
    thresholds, personalised discount rules — is defined in USD. This is the
    reverse of :func:`convert_price`: it unwraps the currency multiplier so
    behavioural metrics are always computed in USD regardless of the currency
    the order was placed in (otherwise an INR customer's LTV would be inflated
    ~83x and skew segment/discount logic).
    """
    if not amount:
        return 0.0
    source = source_currency or DEFAULT_CURRENCY
    config = CURRENCY_CONFIG.get(source)
    if not config or config["rate_to_usd"] <= 0:
        return amount
    return amount / config["rate_to_usd"]


def get_available_currencies() -> dict[str, str]:
    """Return dict of currency code -> symbol for the selector UI."""
    return {code: cfg["symbol"] for code, cfg in CURRENCY_CONFIG.items()}
