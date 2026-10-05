import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium", app_title="Can you afford it?")

with app.setup(hide_code=True):
    import math
    from collections.abc import Callable
    from dataclasses import dataclass
    from typing import Literal

    # The static site installs only packages the notebook imports, so import
    # paste_box's dependency here for it to be available there.
    import anywidget  # noqa: F401  # pyright: ignore[reportUnusedImport]
    import marimo as mo

    from affordability import (
        MIN_DOWN_PAYMENT_SHARE,
        PRICE_SEARCH_LIMIT,
        PRICE_SEARCH_STEP,
        ClosingAssumptions,
        Home,
        Household,
        Result,
        Verdict,
        evaluate,
        max_affordable_price,
    )
    from listing import BuildingType, Listing, parse_listing
    from nys_tax import MFJ_2026 as NY_MFJ_2026
    from paste_box import PasteBox
    from retirement_401k import employee_deferral

    CardKind = Literal["neutral", "success", "warn", "danger"]
    Display = Literal["Percentage", "Amount"]

    @dataclass(frozen=True)
    class Defaults:
        """Starting values, reset if Reset button is clicked."""

        spouse_1_wages: int = 220_000
        spouse_2_wages: int = 0
        contribution_percent: float = 8
        spouse_1_health_insurance: int = 600
        spouse_2_health_insurance: int = 0
        available_cash: int = 340_000
        emergency_fund: int = 0
        monthly_expenses: int = 3_500
        upkeep_percent: float = 0.5
        home_price: int = 1_200_000
        down_payment_display: Display = "Percentage"
        down_payment_percent: float = 20
        down_payment_amount: int = 250_000
        mortgage_rate: float = 7.25
        building_type: BuildingType = "Condo"
        monthly_fees: int = 1_000
        property_tax_display: Display = "Amount"
        property_tax_percent: float = 0.9
        property_tax_monthly: int = 950
        coop_interest_monthly: int = 250
        insurance_monthly: int = 50

    # A co-op's maintenance includes its property tax. When a listing doesn't
    # give the tax portion, assume a modest share: it only feeds the SALT
    # deduction, so guessing low errs toward higher taxes.
    COOP_TAX_SHARE_OF_MAINTENANCE = 0.4

    def number(value: object) -> float:
        """A numeric UI value as a float; an emptied number field reads as None."""
        if value is None:
            return 0.0
        if not isinstance(value, int | float):
            raise TypeError(f"Expected a number, got {value!r}")
        return float(value)

    def money(amount: float, *, markdown: bool = True) -> str:
        """Whole dollars with a minus sign. mo.md needs $ escaped, mo.stat doesn't."""
        dollar = "\\$" if markdown else "$"
        sign = "−" if round(amount) < 0 else ""
        return f"{sign}{dollar}{abs(amount):,.0f}"


@app.cell(hide_code=True)
def _():
    reset_button: mo.ui.button = mo.ui.button(
        value=0,
        on_click=lambda count: count + 1,
        label="::lucide:rotate-ccw:: Reset",
        tooltip="Reset every input to its default",
    )
    return (reset_button,)


@app.cell(hide_code=True)
def _(reset_button: mo.ui.button):
    # Every cell that creates inputs reads these, so clicking Reset reruns this
    # cell, then those, recreating each input at its default.
    _ = reset_button
    defaults: Defaults = Defaults()
    return (defaults,)


@app.cell(hide_code=True)
def _(defaults: Defaults):
    def _wage_inputs(wages: int, health_insurance: int) -> mo.ui.dictionary:
        return mo.ui.dictionary(
            {
                "income": mo.ui.slider(
                    start=0,
                    stop=600_000,
                    step=10_000,
                    value=wages,
                    include_input=True,
                    label="Annual wages",
                ),
                "contribution_percent": mo.ui.slider(
                    start=0,
                    stop=50,
                    step=0.5,
                    value=defaults.contribution_percent,
                    include_input=True,
                    label="401(k) contribution (% of gross)",
                ),
                # Employer plans take premiums out of pay before income tax
                # and FICA (a Section 125 plan).
                "health_insurance": mo.ui.number(
                    start=0,
                    step=10,
                    value=health_insurance,
                    label="Health insurance (monthly, pre-tax)",
                ),
            }
        )

    spouse_1_inputs: mo.ui.dictionary = _wage_inputs(
        defaults.spouse_1_wages, defaults.spouse_1_health_insurance
    )
    spouse_2_inputs: mo.ui.dictionary = _wage_inputs(
        defaults.spouse_2_wages, defaults.spouse_2_health_insurance
    )
    return spouse_1_inputs, spouse_2_inputs


@app.cell(hide_code=True)
def _(spouse_1_inputs: mo.ui.dictionary, spouse_2_inputs: mo.ui.dictionary):
    def _panel(inputs: mo.ui.dictionary) -> mo.Html:
        return mo.vstack(
            [
                inputs["income"],
                inputs["contribution_percent"],
                inputs["health_insurance"],
            ]
        )

    income_panel: mo.ui.tabs = mo.ui.tabs(
        {
            "Spouse 1": _panel(spouse_1_inputs),
            "Spouse 2": _panel(spouse_2_inputs),
        }
    )
    return (income_panel,)


@app.cell(hide_code=True)
def _(defaults: Defaults):
    _ = defaults  # rerun on reset, clearing the pasted listing
    listing_paste: mo.ui.anywidget = mo.ui.anywidget(
        PasteBox(
            placeholder="On a StreetEasy listing, press Cmd+A then Cmd+C, then paste here"
        )
    )
    return (listing_paste,)


@app.cell(hide_code=True)
def _(listing_paste: mo.ui.anywidget):
    # The inputs it fills take these as their defaults, so they stay editable.
    listing_text: str = listing_paste.value.get("text", "")
    listing: Listing = parse_listing(listing_text)
    return listing, listing_text


@app.cell(hide_code=True)
def _(defaults: Defaults):
    upfront_cash: mo.ui.number = mo.ui.number(
        start=0,
        step=1_000,
        value=defaults.available_cash,
        label="Available cash",
    )
    emergency_fund: mo.ui.number = mo.ui.number(
        start=0,
        step=1_000,
        value=defaults.emergency_fund,
        label="Emergency fund",
    )
    return emergency_fund, upfront_cash


@app.cell(hide_code=True)
def _(defaults: Defaults):
    monthly_expenses: mo.ui.slider = mo.ui.slider(
        start=0,
        step=100,
        stop=20_000,
        value=defaults.monthly_expenses,
        include_input=True,
        label="Monthly expenses",
    )
    upkeep: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=3,
        step=0.1,
        value=defaults.upkeep_percent,
        include_input=True,
        label="Upkeep (% of price/yr)",
    )
    return monthly_expenses, upkeep


@app.cell(hide_code=True)
def _(defaults: Defaults):
    down_payment_input_percentage: mo.ui.slider = mo.ui.slider(
        start=MIN_DOWN_PAYMENT_SHARE * 100,
        stop=50,
        step=0.5,
        value=defaults.down_payment_percent,
        include_input=True,
        label="Down payment (% of price)",
    )

    down_payment_input_amount: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=PRICE_SEARCH_LIMIT,
        step=10_000,
        value=defaults.down_payment_amount,
        include_input=True,
        label="Down payment (amount)",
    )

    down_payment_display: mo.ui.radio = mo.ui.radio(
        options=["Percentage", "Amount"],
        value=defaults.down_payment_display,
        inline=True,
    )

    mortgage_rate: mo.ui.slider = mo.ui.slider(
        start=0.0,
        stop=15.0,
        step=0.125,
        include_input=True,
        label="Mortgage rate",
        value=defaults.mortgage_rate,
    )
    return (
        down_payment_display,
        down_payment_input_amount,
        down_payment_input_percentage,
        mortgage_rate,
    )


@app.cell(hide_code=True)
def _(defaults: Defaults, listing: Listing):
    _price = listing.price or defaults.home_price
    home_price: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=max(PRICE_SEARCH_LIMIT, _price),
        step=1_000,  # fine enough to hold a listing's exact price
        value=_price,
        include_input=True,
        label="Home price",
    )
    return (home_price,)


@app.cell(hide_code=True)
def _(defaults: Defaults, listing: Listing):
    building_type: mo.ui.radio = mo.ui.radio(
        options=["Condo", "Co-op"],
        value=listing.building_type or defaults.building_type,
        inline=True,
    )

    _fees = listing.monthly_fees or defaults.monthly_fees
    condo_or_coop_fees: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=max(5_000, _fees),
        step=1,
        include_input=True,
        label="Condo or co-op fees (monthly)",
        value=_fees,
    )

    property_tax_display: mo.ui.radio = mo.ui.radio(
        options=["Percentage", "Amount"],
        value=defaults.property_tax_display,
        inline=True,
    )
    return building_type, condo_or_coop_fees, property_tax_display


@app.cell(hide_code=True)
def _(building_type: mo.ui.radio, defaults: Defaults, listing: Listing):
    # Recreated when the building type changes, since a co-op's figure means
    # something different: the tax portion of maintenance.
    property_tax_input_percentage: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=3,
        step=0.05,
        value=defaults.property_tax_percent,
        include_input=True,
        label="Property tax (annual % of price)",
    )

    if listing.monthly_taxes:
        _taxes = listing.monthly_taxes
    elif building_type.value == "Co-op":
        _maintenance = listing.monthly_fees or defaults.monthly_fees
        _taxes = round(_maintenance * COOP_TAX_SHARE_OF_MAINTENANCE)
    else:
        _taxes = defaults.property_tax_monthly
    property_tax_input_amount: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=max(5_000, _taxes),
        step=1,
        value=_taxes,
        include_input=True,
        label="Property tax (monthly)",
    )
    return property_tax_input_amount, property_tax_input_percentage


@app.cell(hide_code=True)
def _(defaults: Defaults):
    # Shown on the co-op's year-end letter; deductible like mortgage interest.
    coop_interest_portion: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=5_000,
        step=25,
        value=defaults.coop_interest_monthly,
        include_input=True,
        label="Co-op interest (monthly)",
    )

    # HO-6 "walls-in" coverage; the building's master policy is in the fees.
    homeowners_insurance: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=500,
        step=5,
        value=defaults.insurance_monthly,
        include_input=True,
        label="Homeowner's insurance (monthly)",
    )
    return coop_interest_portion, homeowners_insurance


@app.cell(hide_code=True)
def _(building_type: mo.ui.radio):
    # Conservative (high-end) NYC defaults; they reset whenever building_type
    # is recreated: on a type change, a reset, or a pasted listing.
    _defaults = (
        {
            "buyer_attorney": 5_000,
            "lender_attorney": 1_500,
            "lender_fees": 4_000,  # origination, application, appraisal, credit
            "building_fees": 2_000,  # application, move-in, right-of-first-refusal waiver
            "recording_and_misc": 1_500,  # recording, transfer filings, title closer, bank checks
        }
        if building_type.value == "Condo"
        else {
            "buyer_attorney": 5_000,
            "lender_attorney": 1_500,
            "lender_fees": 4_000,  # origination, application, appraisal, credit
            "building_fees": 2_500,  # board application, managing agent, recognition agreement
            "recording_and_misc": 1_000,  # lien search, UCC filing, bank checks
        }
    )

    def _flat(key: str) -> mo.ui.number:
        return mo.ui.number(start=0, step=250, value=_defaults[key], full_width=True)

    closing_fee_inputs: mo.ui.dictionary = mo.ui.dictionary(
        {key: _flat(key) for key in _defaults}
    )
    return (closing_fee_inputs,)


@app.cell(hide_code=True)
def _(defaults: Defaults):
    # The assumptions that don't depend on building type, kept apart so
    # switching it (or pasting a listing) doesn't reset them.
    _ = defaults

    # Labels live here rather than on the inputs so the display can align them
    # in a column.
    closing_labels: dict[str, str] = {
        "buyer_attorney": "Buyer's attorney",
        "lender_attorney": "Lender's attorney",
        "lender_fees": "Lender fees (application, appraisal, credit)",
        "building_fees": "Building fees",
        "recording_and_misc": "Recording, searches, and misc.",
        "points": "Points (% of loan)",
        "buyer_broker": "Buyer's broker (% of price)",
        "title_insurance": "Title insurance (% of price)",
        "escrow_months": "Property tax escrow (months collected upfront)",
        "tax_adjustment_months": "Seller reimbursement: property tax (months)",
        "fee_adjustment_months": "Seller reimbursement: fees (months)",
        "moving": "Moving and setup",
    }

    closing_rate_inputs: mo.ui.dictionary = mo.ui.dictionary(
        {
            "points": mo.ui.number(
                start=0, stop=4, step=0.125, value=0, full_width=True
            ),
            "buyer_broker": mo.ui.number(
                start=0, stop=6, step=0.25, value=0, full_width=True
            ),
            "title_insurance": mo.ui.number(
                start=0, stop=2, step=0.05, value=0.6, full_width=True
            ),
            "escrow_months": mo.ui.number(
                start=0, stop=12, step=1, value=6, full_width=True
            ),
            # NYC property tax is billed semiannually, so the seller may have
            # prepaid months you'll own; same for the current month's fees.
            "tax_adjustment_months": mo.ui.number(
                start=0, stop=6, step=1, value=3, full_width=True
            ),
            "fee_adjustment_months": mo.ui.number(
                start=0, stop=3, step=1, value=1, full_width=True
            ),
            "moving": mo.ui.number(start=0, step=500, value=5_000, full_width=True),
        }
    )
    return closing_labels, closing_rate_inputs


@app.cell(hide_code=True)
def _(
    building_type: mo.ui.radio,
    closing_fee_inputs: mo.ui.dictionary,
    closing_rate_inputs: mo.ui.dictionary,
    condo_or_coop_fees: mo.ui.slider,
    coop_interest_portion: mo.ui.slider,
    down_payment_display: mo.ui.radio,
    down_payment_input_amount: mo.ui.slider,
    down_payment_input_percentage: mo.ui.slider,
    emergency_fund: mo.ui.number,
    home_price: mo.ui.slider,
    homeowners_insurance: mo.ui.slider,
    monthly_expenses: mo.ui.slider,
    mortgage_rate: mo.ui.slider,
    property_tax_display: mo.ui.radio,
    property_tax_input_amount: mo.ui.slider,
    property_tax_input_percentage: mo.ui.slider,
    spouse_1_inputs: mo.ui.dictionary,
    spouse_2_inputs: mo.ui.dictionary,
    upfront_cash: mo.ui.number,
    upkeep: mo.ui.slider,
):
    def _wages(inputs: mo.ui.dictionary) -> dict[str, float]:
        values = inputs.value
        income = number(values["income"])
        contribution_401k = employee_deferral(
            income, percent=number(values["contribution_percent"])
        )
        # Premiums come out of pay, so they can't exceed what's left of it.
        health_insurance = min(
            number(values["health_insurance"]) * 12,
            max(income - contribution_401k, 0),
        )
        return {
            "income": income,
            "contribution_401k": contribution_401k,
            "health_insurance": health_insurance,
            # 401(k) deferrals are still subject to FICA; health premiums aren't.
            "fica_wages": income - health_insurance,
        }

    _spouses = [_wages(spouse_1_inputs), _wages(spouse_2_inputs)]

    household: Household = Household(
        gross_income=sum(spouse["income"] for spouse in _spouses),
        contribution_401k=sum(spouse["contribution_401k"] for spouse in _spouses),
        health_insurance=sum(spouse["health_insurance"] for spouse in _spouses),
        fica_wages_per_person=[spouse["fica_wages"] for spouse in _spouses],
        monthly_expenses=monthly_expenses.value,
        available_cash=number(upfront_cash.value),
        emergency_fund=number(emergency_fund.value),
    )

    _down_payment_is_percent = down_payment_display.value == "Percentage"
    _property_tax_is_percent = property_tax_display.value == "Percentage"
    home: Home = Home(
        price=home_price.value,
        down_payment=(
            down_payment_input_percentage
            if _down_payment_is_percent
            else down_payment_input_amount
        ).value,
        down_payment_is_percent=_down_payment_is_percent,
        rate_percent=mortgage_rate.value,
        is_condo=building_type.value == "Condo",
        monthly_fees=condo_or_coop_fees.value,
        property_tax=(
            property_tax_input_percentage
            if _property_tax_is_percent
            else property_tax_input_amount
        ).value,
        property_tax_is_percent=_property_tax_is_percent,
        coop_interest_monthly=coop_interest_portion.value,
        insurance_monthly=homeowners_insurance.value,
        upkeep_percent=upkeep.value,
        closing=ClosingAssumptions(
            **{
                key: number(value)
                for key, value in (
                    closing_fee_inputs.value | closing_rate_inputs.value
                ).items()
            }
        ),
    )

    result: Result = evaluate(household, home)
    return home, household, result


@app.cell(hide_code=True)
def _(home: Home, household: Household):
    # Highest price at which each card stays green, or at least not red,
    # holding every other input fixed.
    def _max_price(
        verdict: Callable[[Result], Verdict], allow_tight: bool
    ) -> float | None:
        return max_affordable_price(
            household,
            home,
            lambda result: verdict(result).passes(allow_tight=allow_tight),
        )

    _checks: dict[str, Callable[[Result], Verdict]] = {
        "Monthly budget": lambda result: result.monthly_verdict,
        "Cash at closing": lambda result: result.closing_verdict,
    }
    if not home.is_condo:
        _checks["Board debt-to-income"] = lambda result: result.board_dti_verdict
        _checks["Board liquidity"] = lambda result: result.liquidity_verdict

    max_prices: dict[str, tuple[float | None, float | None]] = {
        name: (_max_price(verdict, False), _max_price(verdict, True))
        for name, verdict in _checks.items()
    }
    return (max_prices,)


@app.cell(hide_code=True)
def _(
    home: Home,
    household: Household,
    max_prices: dict[str, tuple[float | None, float | None]],
    result: Result,
):
    def _card(
        value: str, label: str, caption: str, kind: CardKind = "neutral"
    ) -> mo.Html:
        return mo.callout(mo.stat(value=value, label=label, caption=caption), kind=kind)

    def _verdict_card(value: str, label: str, verdict: Verdict) -> mo.Html:
        return _card(value, label, verdict.label, verdict.kind)

    def _row(*cards: mo.Html) -> mo.Html:
        return mo.hstack(list(cards), widths="equal", gap=1)

    def _price(amount: float | None) -> str:
        if amount is None:
            return f"under {money(PRICE_SEARCH_STEP)}"
        # The search stops at its limit, so the true ceiling may be higher.
        return money(amount) + ("+" if amount >= PRICE_SEARCH_LIMIT else "")

    def _lowest(prices: tuple[float | None, ...]) -> float | None:
        known = [price for price in prices if price is not None]
        return min(known) if len(known) == len(prices) else None

    def _ratio(value: float, format_spec: str, unit: str = "") -> str:
        return "—" if math.isinf(value) else f"{value:{format_spec}}{unit}"

    _green, _not_red = zip(*max_prices.values())
    _price_lines = [
        "| | Stays green up to | Turns red above |",
        "|:---|---:|---:|",
        *(
            f"| {name} | {_price(green)} | {_price(not_red)} |"
            for name, (green, not_red) in max_prices.items()
        ),
        f"| **Highest price** | **{_price(_lowest(_green))}** | **{_price(_lowest(_not_red))}** |",
    ]

    # Inputs entered in dollars don't scale with price during the search.
    _fixed = [
        (
            f"{'common charges' if home.is_condo else 'maintenance'} "
            f"({money(home.monthly_fees)}/month)"
        ),
        *(
            []
            if home.property_tax_is_percent
            else [f"property tax ({money(home.property_tax)}/month)"]
        ),
        *(
            []
            if home.down_payment_is_percent
            else [
                (
                    f"the down payment ({money(home.down_payment)}, raised to "
                    f"{MIN_DOWN_PAYMENT_SHARE:.0%} of price where that's more)"
                )
            ]
        ),
    ]
    _held_fixed = (
        f"Holding every other input fixed, in {money(PRICE_SEARCH_STEP)} steps, "
        f"so these stay the same at every price: {', '.join(_fixed)}."
    )

    _footnotes = [
        (
            "\\* Available cash and cash left after closing exclude any "
            "emergency funds, which stay untouched."
        ),
        (
            "† Assumes the tax savings from itemizing arrive in each paycheck. "
            "In practice, the tax savings may arrive in a refund, making monthly "
            "budgeting a little tighter. Also assumes that monthly expenses are ONLY "
            "paid out of monthly wages, not with excess cash on hand (such as "
            "leftover savings post-closing)."
        ),
    ]
    _board_row: list[mo.Html] = []
    if not home.is_condo:
        _board_row = [
            _row(
                _verdict_card(
                    _ratio(result.board_dti, ".0%"),
                    "Board debt-to-income‡",
                    result.board_dti_verdict,
                ),
                _verdict_card(
                    _ratio(result.liquidity_months, ".0f", " months"),
                    "Liquidity after closing‡",
                    result.liquidity_verdict,
                ),
            )
        ]
        _footnotes.append(
            "‡ Co-op boards set their own limits. Most want the monthly payment "
            "to be at most 25–30% of gross income, counting any other debt "
            "payments too, and liquid savings after closing, including the "
            "emergency fund, to cover 1–2 years of payments. Many don't count "
            "retirement accounts, and some are stricter."
        )

    mo.vstack(
        [
            mo.md("# Can you afford it?"),
            _row(
                _card(
                    money(result.total_monthly_payment, markdown=False),
                    "Monthly payment",
                    "mortgage, fees, tax, insurance",
                ),
                _verdict_card(
                    money(result.monthly_leftover, markdown=False),
                    "Left over each month†",
                    result.monthly_verdict,
                ),
            ),
            _row(
                _card(
                    money(result.cash_needed_at_closing, markdown=False),
                    "Cash needed at closing",
                    f"of {money(household.available_cash, markdown=False)} available*",
                ),
                _verdict_card(
                    money(result.closing_cushion, markdown=False),
                    "Cash left after closing*",
                    result.closing_verdict,
                ),
            ),
            *_board_row,
            mo.md("  \n".join(_footnotes)).style(
                font_size="0.85rem", color="var(--muted-foreground, gray)"
            ),
            mo.md("### How high can you go?"),
            mo.md("\n".join(_price_lines)),
            mo.md(_held_fixed).style(
                font_size="0.85rem", color="var(--muted-foreground, gray)"
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(
    building_type: mo.ui.radio,
    condo_or_coop_fees: mo.ui.slider,
    coop_interest_portion: mo.ui.slider,
    down_payment_display: mo.ui.radio,
    down_payment_input_amount: mo.ui.slider,
    down_payment_input_percentage: mo.ui.slider,
    home: Home,
    home_price: mo.ui.slider,
    homeowners_insurance: mo.ui.slider,
    listing: Listing,
    listing_paste: mo.ui.anywidget,
    listing_text: str,
    mortgage_rate: mo.ui.slider,
    property_tax_display: mo.ui.radio,
    property_tax_input_amount: mo.ui.slider,
    property_tax_input_percentage: mo.ui.slider,
    result: Result,
):
    _fees_label = (
        "maintenance" if listing.building_type == "Co-op" else "common charges"
    )
    _found = [
        *([money(listing.price)] if listing.price else []),
        *([listing.building_type] if listing.building_type else []),
        *(
            [f"{money(listing.monthly_fees)}/mo {_fees_label}"]
            if listing.monthly_fees
            else []
        ),
        *(
            [f"{money(listing.monthly_taxes)}/mo taxes"]
            if listing.monthly_taxes
            else []
        ),
    ]
    _missing = [
        name
        for name, value in [
            ("price", listing.price),
            ("building type", listing.building_type),
            (_fees_label, listing.monthly_fees),
            # Co-op listings fold taxes into maintenance.
            *(
                []
                if listing.building_type == "Co-op"
                else [("taxes", listing.monthly_taxes)]
            ),
        ]
        if not value
    ]
    if not listing_text.strip():
        _listing_note = None
    elif listing.is_empty:
        _listing_note = mo.callout(
            mo.md("Couldn't find a price, fees, or taxes in that text."), kind="warn"
        )
    else:
        _listing_note = mo.callout(
            mo.vstack(
                [
                    mo.md(f"**{listing.address or 'Pasted listing'}**"),
                    mo.md(" · ".join(_found)),
                    mo.md(
                        (
                            f"Not found: {', '.join(_missing)}; kept the current values. "
                            if _missing
                            else ""
                        )
                        + "Filled in below, where you can adjust them."
                    ).style(font_size="0.8rem", color="var(--muted-foreground, gray)"),
                ],
                gap=0.25,
            ),
            kind="info",
        )

    if result.down_payment_raised:
        _down_payment_note = (
            f"Below the {MIN_DOWN_PAYMENT_SHARE:.0%} minimum, so using "
            f"{money(result.down_payment)}."
        )
    elif home.down_payment_is_percent:
        _down_payment_note = f"= {money(result.down_payment)}"
    else:
        _share = result.down_payment / home.price if home.price else 0.0
        _down_payment_note = f"= {_share:.1%} of price"

    _property_tax_note = (
        "Condo taxes are billed to you separately from common charges, "
        "so they're added to the monthly payment."
        if building_type.value == "Condo"
        else "Co-op taxes are already inside maintenance, so enter the tax "
        "portion of maintenance here. It counts toward the SALT deduction "
        "but isn't added to the monthly payment again. Unless a listing gives "
        f"it, this starts at {COOP_TAX_SHARE_OF_MAINTENANCE:.0%} of maintenance, "
        "a cautious guess; the building's financials have the real figure."
    )
    _coop_tax_warning = (
        mo.callout(
            mo.md(
                f"The tax portion ({money(result.monthly_property_tax)}/month) is "
                f"more than the whole maintenance fee ({money(home.monthly_fees)}), "
                "which overstates the SALT deduction."
            ),
            kind="warn",
        )
        if not home.is_condo and result.monthly_property_tax > home.monthly_fees
        else None
    )

    housing_panel: mo.Html = mo.vstack(
        [
            listing_paste,
            *([_listing_note] if _listing_note else []),
            home_price,
            mo.hstack(
                ["Down payment", down_payment_display], justify="start", align="end"
            ),
            down_payment_input_percentage
            if home.down_payment_is_percent
            else down_payment_input_amount,
            mo.md(_down_payment_note).style(font_size="0.85rem"),
            mortgage_rate,
            mo.hstack(["Building type", building_type], justify="start", align="end"),
            condo_or_coop_fees,
            mo.hstack(
                ["Property tax", property_tax_display], justify="start", align="end"
            ),
            property_tax_input_percentage
            if home.property_tax_is_percent
            else property_tax_input_amount,
            mo.md(_property_tax_note).style(font_size="0.85rem"),
            *([_coop_tax_warning] if _coop_tax_warning else []),
            *([coop_interest_portion] if building_type.value == "Co-op" else []),
            homeowners_insurance,
        ]
    )
    return (housing_panel,)


@app.cell(hide_code=True)
def _(
    emergency_fund: mo.ui.number,
    home: Home,
    housing_panel: mo.Html,
    income_panel: mo.ui.tabs,
    monthly_expenses: mo.ui.slider,
    reset_button: mo.ui.button,
    result: Result,
    upfront_cash: mo.ui.number,
    upkeep: mo.ui.slider,
):
    def _section(title: str, *items: object) -> mo.Html:
        return mo.vstack([mo.md(f"**{title}**").style(margin_top="0.75rem"), *items])

    _header = mo.hstack(
        [mo.md("### Inputs"), reset_button],
        justify="space-between",
        align="center",
    ).style(
        border_bottom="1px solid var(--slate-6, #e2e8f0)",
        padding_bottom="0.5rem",
        margin_bottom="0.25rem",
    )

    mo.sidebar(
        [
            _header,
            _section("Annual income", income_panel),
            _section(
                "Available cash",
                mo.md(
                    "Budget for down payment, closing costs, etc. Excludes any emergency funds."
                ).style(font_size="0.85rem"),
                upfront_cash,
                *(
                    []
                    if home.is_condo
                    else [
                        emergency_fund,
                        mo.md(
                            "Never spent on the purchase, but co-op boards count "
                            "it toward liquidity after closing."
                        ).style(font_size="0.85rem"),
                    ]
                ),
            ),
            _section("Housing", housing_panel),
            _section(
                "Monthly expenses",
                mo.md(
                    "Typical credit card bill plus padding, rather than an itemized budget, at least for now."
                ).style(font_size="0.85rem"),
                monthly_expenses,
                upkeep,
                mo.md(
                    f"= {money(result.monthly_upkeep)}/month, set aside for upkeep"
                ).style(font_size="0.85rem"),
            ),
        ],
        width="520px",
    )
    return


@app.cell(hide_code=True)
def _(home: Home, result: Result):
    _rows = [
        ("Mortgage (principal and interest)", result.monthly_mortgage_payment, ""),
        (
            "Common charges" if home.is_condo else "Maintenance",
            home.monthly_fees,
            "" if home.is_condo else "includes property tax",
        ),
        *([("Property tax", result.monthly_property_tax, "")] if home.is_condo else []),
        ("Homeowner's insurance", home.insurance_monthly, ""),
    ]
    _lines = [
        "| | Monthly | |",
        "|:---|---:|:---|",
        *(f"| {label} | {money(amount)} | {note} |" for label, amount, note in _rows),
        (
            f"| **Total monthly payment** | **{money(result.total_monthly_payment)}** "
            f"| on a {money(result.loan_amount)} loan |"
        ),
    ]
    mo.vstack([mo.md("### Monthly payment"), mo.md("\n".join(_lines))])
    return


@app.cell(hide_code=True)
def _(household: Household, result: Result):
    mo.vstack(
        [
            mo.md("### Monthly budget"),
            mo.md(f"""
    | | Monthly | |
    |:---|---:|:---|
    | Take-home pay | {money(result.monthly_net)} | after taxes, 401(k), and health insurance |
    | Monthly payment | {money(-result.total_monthly_payment)} | |
    | Monthly expenses | {money(-household.monthly_expenses)} | |
    | Upkeep | {money(-result.monthly_upkeep)} | |
    | **Left over** | **{money(result.monthly_leftover)}** | |
    """),
        ]
    )
    return


@app.cell(hide_code=True)
def _(
    closing_fee_inputs: mo.ui.dictionary,
    closing_labels: dict[str, str],
    closing_rate_inputs: mo.ui.dictionary,
    home: Home,
    result: Result,
):
    def _rows(items: dict[str, float]) -> str:
        return "\n".join(
            f"| {name} | {money(amount)} |" for name, amount in items.items() if amount
        )

    _share = result.closing_costs_total / home.price if home.price else 0.0

    _condo_only = ["title_insurance", "escrow_months", "tax_adjustment_months"]
    _assumptions = mo.vstack(
        [
            mo.hstack(
                [mo.md(closing_labels[_key]), _input],
                widths=[3, 2],
                align="center",
            )
            for _key, _input in [
                *closing_fee_inputs.items(),
                *closing_rate_inputs.items(),
            ]
            if home.is_condo or _key not in _condo_only
        ]
    ).style(max_width="560px")

    mo.vstack(
        [
            mo.md("### Closing costs"),
            mo.md(f"""
    | Closing cost | Amount |
    |:---|---:|
    {_rows(result.closing_cost_items)}
    | **Total closing costs** | **{money(result.closing_costs_total)}** ({_share:.1%} of price) |

    | Prepaid item | Amount |
    |:---|---:|
    {_rows(result.prepaid_items)}
    | **Total prepaid items** | **{money(result.prepaid_total)}** |

    | Cash at closing | Amount |
    |:---|---:|
    | Down payment | {money(result.down_payment)} |
    | Closing costs | {money(result.closing_costs_total)} |
    | Prepaid items | {money(result.prepaid_total)} |
    | Moving and setup | {money(result.moving_costs)} |
    | **Cash needed at closing** | **{money(result.cash_needed_at_closing)}** |
    """),
            mo.accordion({"Closing cost assumptions": _assumptions}),
        ]
    )
    return


@app.cell(hide_code=True)
def _(household: Household, result: Result):
    _taxes = result.taxes
    _gross = household.gross_income

    def _share_of_gross(amount: float) -> str:
        return f"{amount / _gross:.2%}" if _gross else ""

    def _section(
        heading: str,
        rows: list[tuple[str, float, str]],
        total: tuple[str, float, str],
    ) -> list[str]:
        """rows and total are (label, amount, note) tuples; the total row is bolded."""
        _label, _amount, _note = total
        return [
            f"| **{heading}** | | |",
            *(
                f"| {label} | {money(amount)} | {note} |"
                for label, amount, note in rows
            ),
            f"| **{_label}** | **{money(_amount)}** | {_note} |",
        ]

    _state_and_city = _taxes.state_tax + _taxes.city_tax
    _lines = [
        "| | Amount | |",
        "|:---|---:|:---|",
        *_section(
            "Income",
            [
                ("Gross annual income", _gross, ""),
                ("401(k) contributions", household.contribution_401k, ""),
                ("Health insurance premiums", household.health_insurance, ""),
            ],
            ("Total pre-tax deductions", household.pretax_deductions, ""),
        ),
        *_section(
            "Federal",
            [
                ("SALT deduction (after cap)", _taxes.salt_deduction, ""),
                (
                    "Mortgage interest deduction (first year)",
                    _taxes.mortgage_interest_deduction,
                    "",
                ),
                (
                    "Federal deduction",
                    _taxes.federal_deduction,
                    "itemized" if _taxes.federal_itemizes else "standard",
                ),
                ("Federal taxable income", _taxes.federal_taxable_income, ""),
            ],
            (
                "Federal income tax",
                _taxes.federal_tax,
                _share_of_gross(_taxes.federal_tax),
            ),
        ),
        *_section(
            "FICA",
            [
                ("FICA wages", sum(household.fica_wages_per_person), ""),
                (
                    "Social Security tax",
                    result.social_security,
                    _share_of_gross(result.social_security),
                ),
                ("Medicare tax", result.medicare, _share_of_gross(result.medicare)),
            ],
            ("Total FICA tax", result.fica, _share_of_gross(result.fica)),
        ),
        *_section(
            "New York",
            [
                (
                    "NY itemized deduction",
                    _taxes.ny_itemized,
                    f"standard is {money(NY_MFJ_2026.standard_deduction)}",
                ),
                (
                    "NY deduction",
                    _taxes.ny_deduction,
                    "itemized" if _taxes.ny_itemizes else "standard",
                ),
                ("NYS taxable income", _taxes.ny_taxable_income, ""),
                ("NYS tax", _taxes.state_tax, _share_of_gross(_taxes.state_tax)),
                ("NYC tax", _taxes.city_tax, _share_of_gross(_taxes.city_tax)),
            ],
            ("Total NY tax", _state_and_city, _share_of_gross(_state_and_city)),
        ),
        *_section(
            "Summary",
            [
                ("Total income tax", _taxes.total, _share_of_gross(_taxes.total)),
                ("Total FICA tax", result.fica, _share_of_gross(result.fica)),
            ],
            ("Total tax", result.total_tax, _share_of_gross(result.total_tax)),
        ),
    ]
    _details = [mo.md("\n".join(_lines))]
    if result.points_tax_savings:
        _details.append(
            mo.md(
                f"One-time tax savings from points (year 1 only, not in the monthly figures): **{money(result.points_tax_savings)}**"
            )
        )
    mo.accordion({"Tax details": mo.vstack(_details)})
    return


if __name__ == "__main__":
    app.run()
