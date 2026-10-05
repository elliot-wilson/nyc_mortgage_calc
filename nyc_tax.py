from dataclasses import dataclass


@dataclass(frozen=True)
class NYCSchedule:
    year: int
    filing_status: str
    brackets: dict[float, float]  # floor -> marginal rate, ascending
    school_fixed_credit: float  # refundable, flat amount
    school_fixed_income_limit: float  # income ceiling for the fixed credit
    school_rate_reduction: dict[float, float]  # floor -> credit rate, ascending
    school_rate_reduction_taxable_income_limit: (
        float  # NYC taxable income ceiling (hard cliff)
    )

    @property
    def floors(self) -> list[float]:
        return list(self.brackets)

    @property
    def rates(self) -> list[float]:
        return list(self.brackets.values())


MFJ_2026 = NYCSchedule(
    year=2026,
    filing_status="MFJ",
    brackets={  # income floor: marginal rate
        0: 0.03078,
        21_600: 0.03762,
        45_000: 0.03819,
        90_000: 0.03876,
    },
    school_fixed_credit=125,
    school_fixed_income_limit=250_000,
    school_rate_reduction={
        0: 0.00171,
        21_600: 0.00228,
    },
    school_rate_reduction_taxable_income_limit=500_000,
)


def _bracket_tax(amount: float, floors: list[float], rates: list[float]) -> float:
    tax = 0.0
    for i, (floor, rate) in enumerate(zip(floors, rates)):
        if amount <= floor:
            break
        max_subject_within_bracket = (
            floors[i + 1] if i + 1 < len(floors) else float("inf")
        )
        tax += (min(amount, max_subject_within_bracket) - floor) * rate
    return tax


def bracket_tax(amount: float, tax_schedule: NYCSchedule) -> float:
    return _bracket_tax(amount, tax_schedule.floors, tax_schedule.rates)


def nyc_gross_tax(taxable_income: float, tax_schedule: NYCSchedule = MFJ_2026) -> float:
    return bracket_tax(max(taxable_income, 0.0), tax_schedule)


def nyc_school_credits(
    taxable_income: float, income: float, tax_schedule: NYCSchedule = MFJ_2026
) -> float:
    """
    taxable_income: NYC taxable income (same as NY taxable income for a full-year resident).
    income: the fixed credit's income test. It's STAR-defined income, roughly
            federal AGI minus taxable IRA distributions; federal AGI is a fine proxy.
    """
    credit = 0.0
    if income <= tax_schedule.school_fixed_income_limit:
        credit += tax_schedule.school_fixed_credit
    if taxable_income <= tax_schedule.school_rate_reduction_taxable_income_limit:
        credit += round(
            _bracket_tax(
                max(taxable_income, 0.0),
                list(tax_schedule.school_rate_reduction),
                list(tax_schedule.school_rate_reduction.values()),
            )
        )
    return credit


def nyc_tax(
    taxable_income: float, income: float, tax_schedule: NYCSchedule = MFJ_2026
) -> float:
    return nyc_gross_tax(taxable_income, tax_schedule) - nyc_school_credits(
        taxable_income, income, tax_schedule
    )
