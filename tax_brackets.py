"""Helpers shared by the federal, NYS, and NYC tax schedules."""


def bracket_tax(amount: float, brackets: dict[float, float]) -> float:
    """Progressive tax on amount; brackets maps each floor to its marginal rate, ascending."""
    floors, rates = list(brackets), list(brackets.values())
    tax = 0.0
    for i, (floor, rate) in enumerate(zip(floors, rates)):
        if amount <= floor:
            break
        max_subject_within_bracket = (
            floors[i + 1] if i + 1 < len(floors) else float("inf")
        )
        tax += (min(amount, max_subject_within_bracket) - floor) * rate
    return tax


def deductible_mortgage_interest(
    interest_paid: float, loan_amount: float, debt_limit: float
) -> float:
    """Interest on debt above the limit isn't deductible, so prorate by the covered share."""
    if loan_amount <= debt_limit:
        return interest_paid
    return interest_paid * debt_limit / loan_amount
