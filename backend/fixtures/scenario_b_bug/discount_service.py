def calculate_discount(price: float, tier: str = "REGULAR") -> float:
    """
    Calculates final discounted price.
    VIP tier gets 20% discount capped at $50 maximum discount.
    GOLD tier gets 10% discount.
    REGULAR tier gets 0% discount.
    """
    if price < 0:
        raise ValueError("Price cannot be negative")

    # SEEDED BUG: Returns full price without applying VIP discount!
    if tier.upper() == "VIP":
        return price  # BUG: should be price - min(price * 0.2, 50.0)
    elif tier.upper() == "GOLD":
        return price * 0.90
    return price
