from dataclasses import dataclass


@dataclass(frozen=True)
class Limits401k:
    year: int
    elective_deferral: float  # 402(g) employee deferral limit
    compensation_limit: float  # 401(a)(17) pay that can be counted


LIMITS_2026 = Limits401k(
    year=2026,
    elective_deferral=24_500,
    compensation_limit=360_000,
)


def employee_deferral(
    annual_income: float,
    *,
    amount: float | None = None,
    percent: float | None = None,
    limits: Limits401k = LIMITS_2026,
) -> float:
    if (amount is None) == (percent is None):
        raise ValueError("Specify exactly one of amount or percent")
    if percent is not None:
        eligible_pay = min(annual_income, limits.compensation_limit)
        amount = eligible_pay * percent / 100
    return min(max(amount or 0.0, 0.0), limits.elective_deferral, annual_income)
