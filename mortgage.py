def monthly_mortgage_payment(annual_rate: float, loan_amount: float) -> float:
    """
    annual_rate is a decimal representation of the rate (e.g. 0.05 for 5%)
    """
    number_of_payments = 30 * 12
    monthly_rate = annual_rate / 12

    if monthly_rate == 0:
        return loan_amount / number_of_payments

    growth_factor = (1 + monthly_rate) ** number_of_payments
    return loan_amount * monthly_rate * growth_factor / (growth_factor - 1)


def first_year_interest(annual_rate: float, loan_amount: float) -> float:
    """Total interest paid over the first 12 monthly payments."""
    monthly_rate = annual_rate / 12
    payment = monthly_mortgage_payment(annual_rate, loan_amount)

    balance = loan_amount
    interest_paid = 0.0
    for _ in range(12):
        interest = balance * monthly_rate
        interest_paid += interest
        balance -= payment - interest
    return interest_paid
