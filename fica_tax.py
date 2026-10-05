from dataclasses import dataclass


@dataclass(frozen=True)
class FICASchedule:
    year: int
    filing_status: str
    social_security_rate: float
    social_security_wage_base: float
    medicare_rate: float
    additional_medicare_rate: float
    additional_medicare_threshold: float


MFJ_2026 = FICASchedule(
    year=2026,
    filing_status="MFJ",
    social_security_rate=0.062,
    social_security_wage_base=184_500,
    medicare_rate=0.0145,
    additional_medicare_rate=0.009,
    additional_medicare_threshold=250_000,
)


def social_security_tax(
    fica_wages: float, tax_schedule: FICASchedule = MFJ_2026
) -> float:
    """Employee Social Security tax, limited to the annual wage base."""
    return (
        min(max(fica_wages, 0.0), tax_schedule.social_security_wage_base)
        * tax_schedule.social_security_rate
    )


def medicare_tax(fica_wages: float, tax_schedule: FICASchedule = MFJ_2026) -> float:
    """Employee Medicare tax, including the Additional Medicare Tax."""
    fica_wages = max(fica_wages, 0.0)
    return (
        fica_wages * tax_schedule.medicare_rate
        + max(fica_wages - tax_schedule.additional_medicare_threshold, 0.0)
        * tax_schedule.additional_medicare_rate
    )


def fica_tax(fica_wages: float, tax_schedule: FICASchedule = MFJ_2026) -> float:
    """Total employee FICA tax on wages subject to Social Security and Medicare."""
    return social_security_tax(fica_wages, tax_schedule) + medicare_tax(
        fica_wages, tax_schedule
    )
