TAX_RATE = 1.1


def adjusted(amount: float) -> float:
    return amount * TAX_RATE


def calculate(amounts: list[float]) -> float:
    total = 0.0
    try:
        for amount in amounts:
            value = adjusted(amount)
            if value > 10:
                total += value
            else:
                total = 0.0
    except TypeError:
        total = 0.0
    return total
