from dataclasses import dataclass

from tax_brackets import bracket_tax


@dataclass(frozen=True)
class FederalSchedule:
    year: int
    filing_status: str
    brackets: dict[float, float]  # floor -> marginal rate, ascending
    standard_deduction: float
    max_salt_deduction: float  # SALT cap before the high-income phase-down
    salt_phase_down_threshold: float  # MAGI above which the SALT cap shrinks
    salt_phase_down_rate: float  # cap reduction per dollar of MAGI over the threshold
    salt_floor: float  # the cap never drops below this
    mortgage_debt_limit: float  # acquisition debt whose interest is deductible


MFJ_2026 = FederalSchedule(
    year=2026,
    filing_status="MFJ",
    brackets={  # floor: marginal rate
        0: 0.10,
        24_800: 0.12,
        100_800: 0.22,
        211_400: 0.24,
        403_550: 0.32,
        512_450: 0.35,
        768_700: 0.37,
    },
    standard_deduction=32_200,
    max_salt_deduction=40_400,
    salt_phase_down_threshold=505_000,
    salt_phase_down_rate=0.30,
    salt_floor=10_000,
    mortgage_debt_limit=750_000,
)


def federal_income_tax(
    taxable_income: float, tax_schedule: FederalSchedule = MFJ_2026
) -> float:
    return bracket_tax(max(taxable_income, 0.0), tax_schedule.brackets)


def salt_deduction_limit(
    magi: float, tax_schedule: FederalSchedule = MFJ_2026
) -> float:
    """The SALT cap after the high-income phase-down. For W-2 income, MAGI here is just AGI."""
    reduction = (
        max(magi - tax_schedule.salt_phase_down_threshold, 0)
        * tax_schedule.salt_phase_down_rate
    )
    return max(tax_schedule.max_salt_deduction - reduction, tax_schedule.salt_floor)


def allowed_salt_deduction(
    state_and_local_taxes_paid: float,
    magi: float,
    tax_schedule: FederalSchedule = MFJ_2026,
) -> float:
    """state_and_local_taxes_paid: NYS + NYC income tax plus property tax."""
    return min(state_and_local_taxes_paid, salt_deduction_limit(magi, tax_schedule))

