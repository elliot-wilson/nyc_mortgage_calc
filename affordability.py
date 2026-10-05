from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

from closing_costs import mansion_tax, mortgage_recording_tax
from household_tax import IncomeTaxes, fica_taxes, income_taxes
from mortgage import first_year_interest, monthly_mortgage_payment

MIN_DOWN_PAYMENT_SHARE = 0.20  # you can't put down less than 20%

# Leftover thresholds for the monthly indicator
COMFORTABLE_LEFTOVER = 1_000  # at or above: green
MINIMUM_LEFTOVER = 500  # below: red; in between: yellow

# Cushion threshold for the closing cash indicator
COMFORTABLE_CUSHION = 20_000  # at or above: green; below zero: red

# Debt-to-income: the monthly payment as a share of gross monthly income.
# Lenders: conforming loans usually allow up to 45%, or 50% with compensating
# factors like strong credit or large reserves; 43% is the safe rule of thumb.
COMFORTABLE_LENDER_DTI = 0.43  # at or below: green
MAX_LENDER_DTI = 0.50  # above: red; in between: yellow

# Co-op board thresholds. Boards set their own, but most land in these ranges.
COMFORTABLE_BOARD_DTI = 0.25  # at or below: green
MAX_BOARD_DTI = 0.30  # above: red; in between: yellow
# Liquidity: savings left after closing, in months of housing payments.
COMFORTABLE_LIQUIDITY_MONTHS = 24  # at or above: green
MINIMUM_LIQUIDITY_MONTHS = 12  # below: red; in between: yellow

# The "How high can you go?" search
PRICE_SEARCH_STEP = 10_000
PRICE_SEARCH_LIMIT = 5_000_000


@dataclass(frozen=True)
class Household:
    gross_income: float
    contribution_401k: float
    health_insurance: float  # annual premiums, deducted pre-tax from pay
    fica_wages_per_person: list[float]
    monthly_expenses: float
    available_cash: float  # for the purchase; excludes the emergency fund
    emergency_fund: float  # untouched, but co-op boards count it as liquid

    @property
    def pretax_deductions(self) -> float:
        return self.contribution_401k + self.health_insurance


@dataclass(frozen=True)
class ClosingAssumptions:
    buyer_attorney: float
    lender_attorney: float
    lender_fees: float
    building_fees: float
    recording_and_misc: float
    points: float  # percent of the loan
    buyer_broker: float  # percent of price
    title_insurance: float  # percent of price; condos only
    escrow_months: float  # property tax collected upfront; condos only
    tax_adjustment_months: float  # property tax the seller prepaid; condos only
    fee_adjustment_months: float  # fees the seller prepaid
    moving: float


@dataclass(frozen=True)
class Home:
    price: float
    down_payment: float  # a percent of price, or dollars, per down_payment_is_percent
    down_payment_is_percent: bool
    rate_percent: float
    is_condo: bool
    monthly_fees: float  # condo common charges or co-op maintenance
    property_tax: float  # an annual percent of price, or monthly dollars
    property_tax_is_percent: bool
    coop_interest_monthly: float
    insurance_monthly: float
    upkeep_percent: float  # yearly upkeep savings, as a percent of price
    closing: ClosingAssumptions


VerdictKind = Literal["success", "warn", "danger"]  # mo.callout kinds


@dataclass(frozen=True)
class Verdict:
    kind: VerdictKind
    label: str

    def passes(self, *, allow_tight: bool) -> bool:
        """Green always passes; yellow passes only if allow_tight."""
        return self.kind == "success" or (allow_tight and self.kind == "warn")


@dataclass(frozen=True)
class Result:
    down_payment: float
    down_payment_raised: bool  # the entered amount was under the 20% minimum
    loan_amount: float
    monthly_mortgage_payment: float
    monthly_property_tax: float
    total_monthly_payment: float
    monthly_upkeep: float  # set aside for upkeep, not a bill
    closing_cost_items: dict[str, float]
    closing_costs_total: float
    prepaid_items: dict[str, float]
    prepaid_total: float
    moving_costs: float
    cash_needed_at_closing: float
    taxes: IncomeTaxes  # recurring, without one-time points
    points_tax_savings: float
    social_security: float
    medicare: float
    monthly_net: float
    monthly_leftover: float
    closing_cushion: float
    dti: float  # monthly payment over gross monthly income
    liquidity_months: float  # liquid savings after closing, in housing payments

    @property
    def fica(self) -> float:
        return self.social_security + self.medicare

    @property
    def total_tax(self) -> float:
        return self.taxes.total + self.fica

    @property
    def monthly_verdict(self) -> Verdict:
        if self.monthly_leftover >= COMFORTABLE_LEFTOVER:
            return Verdict("success", "Sustainable")
        if self.monthly_leftover >= MINIMUM_LEFTOVER:
            return Verdict("warn", "Tight")
        return Verdict("danger", "Not sustainable")

    @property
    def closing_verdict(self) -> Verdict:
        if self.closing_cushion >= COMFORTABLE_CUSHION:
            return Verdict("success", "Affordable")
        if self.closing_cushion >= 0:
            return Verdict("warn", "Tight")
        return Verdict("danger", "Not affordable")

    @property
    def lender_dti_verdict(self) -> Verdict:
        if self.dti <= COMFORTABLE_LENDER_DTI:
            return Verdict("success", "Meets most lenders")
        if self.dti <= MAX_LENDER_DTI:
            return Verdict("warn", "Needs a strong application")
        return Verdict("danger", "Above lenders' limit")

    @property
    def board_dti_verdict(self) -> Verdict:
        if self.dti <= COMFORTABLE_BOARD_DTI:
            return Verdict("success", "Meets most boards")
        if self.dti <= MAX_BOARD_DTI:
            return Verdict("warn", "Meets lenient boards")
        return Verdict("danger", "Above most boards' limit")

    @property
    def liquidity_verdict(self) -> Verdict:
        if self.liquidity_months >= COMFORTABLE_LIQUIDITY_MONTHS:
            return Verdict("success", "Meets most boards")
        if self.liquidity_months >= MINIMUM_LIQUIDITY_MONTHS:
            return Verdict("warn", "Meets lenient boards")
        return Verdict("danger", "Below most boards' minimum")


def evaluate(household: Household, home: Home) -> Result:
    price = home.price
    rate = home.rate_percent / 100
    closing = home.closing

    entered_down_payment = (
        price * home.down_payment / 100
        if home.down_payment_is_percent
        else home.down_payment
    )
    minimum_down_payment = price * MIN_DOWN_PAYMENT_SHARE
    down_payment = min(max(entered_down_payment, minimum_down_payment), price)
    loan_amount = price - down_payment
    has_loan = loan_amount > 0  # an all-cash purchase has no lender costs or escrow

    monthly_mortgage = monthly_mortgage_payment(rate, loan_amount)
    interest_paid = first_year_interest(rate, loan_amount)

    monthly_property_tax = (
        price * home.property_tax / 100 / 12
        if home.property_tax_is_percent
        else home.property_tax
    )
    # A co-op's property tax is already part of its maintenance fee.
    billed_property_tax = monthly_property_tax if home.is_condo else 0.0
    coop_building_interest = 0.0 if home.is_condo else home.coop_interest_monthly * 12

    total_monthly_payment = (
        monthly_mortgage
        + home.monthly_fees
        + billed_property_tax
        + home.insurance_monthly
    )
    monthly_upkeep = price * home.upkeep_percent / 100 / 12

    # Closing costs
    points_paid = loan_amount * closing.points / 100
    closing_cost_items = {
        "Mansion tax": mansion_tax(price),
        "Mortgage recording tax": (
            mortgage_recording_tax(loan_amount) if home.is_condo else 0.0
        ),
        "Title insurance": (
            price * closing.title_insurance / 100 if home.is_condo else 0.0
        ),
        "Our attorney": closing.buyer_attorney,
        "Lender's attorney": closing.lender_attorney if has_loan else 0.0,
        "Lender fees": closing.lender_fees if has_loan else 0.0,
        "Points": points_paid,
        "Building fees": closing.building_fees,
        "Recording, searches, and misc.": closing.recording_and_misc,
        "Our broker": price * closing.buyer_broker / 100,
    }
    closing_costs_total = sum(closing_cost_items.values())

    # Cash due at closing that isn't a fee: the first year of insurance,
    # interest through month-end (assume an early-month closing, the costliest),
    # property tax the lender collects upfront into escrow (condos), and
    # reimbursing the seller for taxes and fees they prepaid for our months.
    prepaid_items = {
        "Homeowner's insurance (first year)": home.insurance_monthly * 12,
        "Interest through month-end": loan_amount * rate / 12,
        "Property tax escrow": (
            monthly_property_tax * closing.escrow_months
            if home.is_condo and has_loan
            else 0.0
        ),
        # A co-op's tax is inside maintenance, so only the fee months apply.
        "Seller reimbursement": home.monthly_fees * closing.fee_adjustment_months
        + (
            monthly_property_tax * closing.tax_adjustment_months
            if home.is_condo
            else 0.0
        ),
    }
    prepaid_total = sum(prepaid_items.values())
    moving_costs = closing.moving
    cash_needed_at_closing = (
        down_payment + closing_costs_total + prepaid_total + moving_costs
    )

    # Taxes. Points are deductible only in the year paid, so the recurring
    # figures that drive the monthly budget leave them out; their one-time
    # savings are reported separately.
    agi = household.gross_income - household.pretax_deductions

    def _taxes(interest: float) -> IncomeTaxes:
        return income_taxes(
            agi=agi,
            property_tax=monthly_property_tax * 12,
            mortgage_interest=interest,
            loan_amount=loan_amount,
            coop_building_interest=coop_building_interest,
        )

    taxes = _taxes(interest_paid)
    points_tax_savings = (
        taxes.total - _taxes(interest_paid + points_paid).total if points_paid else 0.0
    )
    social_security, medicare = fica_taxes(household.fica_wages_per_person)

    # Take-home pay: what's left of each paycheck after 401(k), health
    # insurance, and taxes
    monthly_net = (agi - taxes.total - social_security - medicare) / 12
    cushion = household.available_cash - cash_needed_at_closing

    return Result(
        down_payment=down_payment,
        down_payment_raised=entered_down_payment < minimum_down_payment,
        loan_amount=loan_amount,
        monthly_mortgage_payment=monthly_mortgage,
        monthly_property_tax=monthly_property_tax,
        total_monthly_payment=total_monthly_payment,
        monthly_upkeep=monthly_upkeep,
        closing_cost_items=closing_cost_items,
        closing_costs_total=closing_costs_total,
        prepaid_items=prepaid_items,
        prepaid_total=prepaid_total,
        moving_costs=moving_costs,
        cash_needed_at_closing=cash_needed_at_closing,
        taxes=taxes,
        points_tax_savings=points_tax_savings,
        social_security=social_security,
        medicare=medicare,
        monthly_net=monthly_net,
        monthly_leftover=monthly_net
        - total_monthly_payment
        - monthly_upkeep
        - household.monthly_expenses,
        closing_cushion=cushion,
        dti=(
            total_monthly_payment / (household.gross_income / 12)
            if household.gross_income
            else float("inf")
        ),
        liquidity_months=(
            (cushion + household.emergency_fund) / total_monthly_payment
            if total_monthly_payment
            else float("inf")
        ),
    )


def max_affordable_price(
    household: Household,
    home: Home,
    acceptable: Callable[[Result], bool],
    *,
    step: float = PRICE_SEARCH_STEP,
    limit: float = PRICE_SEARCH_LIMIT,
) -> float | None:
    """
    The highest price (in `step` increments) up to which every price is
    acceptable, holding every other input fixed. None if even the first step
    fails; `limit` if nothing up to it does.
    """
    best = None
    price = step
    while price <= limit:
        if not acceptable(evaluate(household, replace(home, price=price))):
            break
        best = price
        price += step
    return best
