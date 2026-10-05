from bisect import bisect_right
from dataclasses import dataclass


@dataclass(frozen=True)
class NYSchedule:
    year: int
    filing_status: str
    brackets: dict[float, float]  # floor -> marginal rate, ascending
    standard_deduction: float
    recapture_start: float  # NYAGI where recapture begins
    first_recapture_tier_floor: float  # floor of the bracket the first tier flattens to
    flat_top_threshold: float  # NYAGI above which everything is taxed at the top rate
    mortgage_debt_limit: float  # pre-2018 IRC acquisition debt limit, which NY kept
    pease_threshold: float  # federal AGI above which the pre-2018 3%/80% limit applies
    itemized_adjustment_start: float  # NYAGI where the 25% itemized reduction phases in
    itemized_adjustment_upper_start: float  # NYAGI where it phases from 25% to 50%
    charitable_only_threshold: float  # NYAGI above which only charity is deductible
    phase_width: float = 50_000

    @property
    def floors(self) -> list[float]:
        return list(self.brackets)

    @property
    def rates(self) -> list[float]:
        return list(self.brackets.values())

    @property
    def first_recapture_tier(self) -> int:
        return self.floors.index(self.first_recapture_tier_floor)


MFJ_2026 = NYSchedule(
    year=2026,
    filing_status="MFJ",
    brackets={  # floor: rate
        0: 0.039,
        17_150: 0.044,
        23_600: 0.0515,
        27_900: 0.054,
        161_550: 0.059,
        323_200: 0.0685,
        2_155_350: 0.0965,
        5_000_000: 0.103,
        25_000_000: 0.109,
    },
    standard_deduction=16_050,
    recapture_start=107_650,
    first_recapture_tier_floor=27_900,
    flat_top_threshold=25_000_000,
    mortgage_debt_limit=1_000_000,
    pease_threshold=408_850,  # 2025 figure (IT-196-I); 2026 isn't published yet
    itemized_adjustment_start=200_000,
    itemized_adjustment_upper_start=475_000,
    charitable_only_threshold=1_000_000,
)


def bracket_tax(taxable_income: float, tax_schedule: NYSchedule) -> float:
    floors, rates = tax_schedule.floors, tax_schedule.rates
    tax = 0.0
    for i, (floor, rate) in enumerate(zip(floors, rates)):
        if taxable_income <= floor:
            break
        max_subject_within_bracket = (
            floors[i + 1] if i + 1 < len(floors) else float("inf")
        )
        tax += (min(taxable_income, max_subject_within_bracket) - floor) * rate
    return tax


def _phase(nyagi: float, start: float, tax_schedule: NYSchedule) -> float:
    # DTF worksheets round the phase-in fraction to 4 decimal places
    return round(
        min(max(nyagi - start, 0), tax_schedule.phase_width) / tax_schedule.phase_width,
        4,
    )


def nys_tax(
    ny_agi: float, taxable_income: float, tax_schedule: NYSchedule = MFJ_2026
) -> float:
    taxable_income = max(taxable_income, 0.0)
    floors, rates = tax_schedule.floors, tax_schedule.rates

    if ny_agi > tax_schedule.flat_top_threshold:
        return taxable_income * rates[-1]

    base = bracket_tax(
        taxable_income, tax_schedule
    )  # the "normal" tax without recapture adjustments
    if ny_agi <= tax_schedule.recapture_start:
        return base

    taxable_income_bracket_index = (
        bisect_right(floors, taxable_income) - 1
    )  # bracket containing your taxable income
    first_tier = tax_schedule.first_recapture_tier
    if taxable_income_bracket_index <= first_tier:
        target = rates[first_tier] * taxable_income
        return base + _phase(ny_agi, tax_schedule.recapture_start, tax_schedule) * (
            target - base
        )

    bracket_floor = floors[taxable_income_bracket_index]
    recapture_base = rates[
        taxable_income_bracket_index - 1
    ] * bracket_floor - bracket_tax(bracket_floor, tax_schedule)
    increment = (
        rates[taxable_income_bracket_index] - rates[taxable_income_bracket_index - 1]
    ) * bracket_floor
    return (
        base + recapture_base + _phase(ny_agi, bracket_floor, tax_schedule) * increment
    )


def deductible_mortgage_interest(
    interest_paid: float, loan_amount: float, tax_schedule: NYSchedule = MFJ_2026
) -> float:
    """Interest on debt above the limit isn't deductible, so prorate by the covered share."""
    if loan_amount <= tax_schedule.mortgage_debt_limit:
        return interest_paid
    return interest_paid * tax_schedule.mortgage_debt_limit / loan_amount


def ny_itemized_deduction(
    *,
    federal_agi: float,
    ny_agi: float,
    property_tax: float,
    mortgage_interest: float,
    state_and_local_income_taxes: float,
    tax_schedule: NYSchedule = MFJ_2026,
) -> float:
    """
    Form IT-196, lines 40-47. mortgage_interest should already be limited by
    deductible_mortgage_interest. state_and_local_income_taxes is what was paid
    during the year: NY disallows it, but it still sets the size of the Pease cut.
    """
    # Line 40: the pre-2018 federal "Pease" limit, applied to the full total
    total = property_tax + mortgage_interest + state_and_local_income_taxes
    pease_reduction = min(
        0.80 * total,
        0.03 * max(federal_agi - tax_schedule.pease_threshold, 0),
    )
    share_kept = 1 - pease_reduction / total if total else 0.0

    # Lines 41-45: income taxes come out net of their share of the Pease cut
    # (Worksheet 2), which leaves every other deduction scaled by share_kept
    before_adjustment = (total - state_and_local_income_taxes) * share_kept

    # Lines 46-47: NY's own high-income reduction
    if ny_agi > tax_schedule.charitable_only_threshold:
        return 0.0  # only (part of) charitable gifts survive, and those aren't modeled

    upper_start = tax_schedule.itemized_adjustment_upper_start
    if ny_agi > upper_start + tax_schedule.phase_width:
        adjustment = 0.50 * before_adjustment
    elif ny_agi > upper_start:  # Worksheet 4
        adjustment = (
            0.25 * before_adjustment * (1 + _phase(ny_agi, upper_start, tax_schedule))
        )
    else:  # Worksheet 3
        adjustment = (
            0.25
            * before_adjustment
            * _phase(ny_agi, tax_schedule.itemized_adjustment_start, tax_schedule)
        )
    return before_adjustment - adjustment
