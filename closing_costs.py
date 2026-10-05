from bisect import bisect_right

# NYS mansion tax: the rate for the price's tier applies to the whole price.
MANSION_TAX_TIERS = {  # price floor: rate
    1_000_000: 0.01,
    2_000_000: 0.0125,
    3_000_000: 0.015,
    5_000_000: 0.0225,
    10_000_000: 0.0325,
    15_000_000: 0.035,
    20_000_000: 0.039,
}

# NYC + NYS mortgage recording tax, buyer's share after the lender's 0.25%.
# Condos only: co-op share loans aren't recorded mortgages.
MORTGAGE_RECORDING_TAX_THRESHOLD = 500_000
MORTGAGE_RECORDING_TAX_RATE_BELOW = 0.018
MORTGAGE_RECORDING_TAX_RATE_ABOVE = 0.01925


def mansion_tax(price: float) -> float:
    floors = list(MANSION_TAX_TIERS)
    tier = bisect_right(floors, price) - 1
    if tier < 0:
        return 0.0
    return price * MANSION_TAX_TIERS[floors[tier]]


def mortgage_recording_tax(loan_amount: float) -> float:
    rate = (
        MORTGAGE_RECORDING_TAX_RATE_ABOVE
        if loan_amount >= MORTGAGE_RECORDING_TAX_THRESHOLD
        else MORTGAGE_RECORDING_TAX_RATE_BELOW
    )
    return max(loan_amount, 0.0) * rate
