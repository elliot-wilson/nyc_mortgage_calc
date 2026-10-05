import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium", app_title="Can we afford it?")

with app.setup(hide_code=True):
    from collections.abc import Callable
    from typing import Literal

    import marimo as mo

    from affordability import (
        MIN_DOWN_PAYMENT_SHARE,
        Home,
        Household,
        Result,
        Verdict,
        evaluate,
        max_affordable_price,
    )
    from nys_tax import MFJ_2026 as NY_MFJ_2026
    from retirement_401k import employee_deferral

    CardKind = Literal["neutral", "success", "warn", "danger"]

    def number(value: object) -> float:
        """A numeric UI value as a float; an emptied number field reads as None."""
        if value is None:
            return 0.0
        if not isinstance(value, int | float):
            raise TypeError(f"Expected a number, got {value!r}")
        return float(value)


@app.cell(hide_code=True)
def _():
    # Every cell that creates inputs references this button, so clicking it
    # reruns those cells and recreates each input at its default.
    reset_button: mo.ui.button = mo.ui.button(
        value=0,
        on_click=lambda count: count + 1,
        label="::lucide:rotate-ccw:: Reset",
        tooltip="Reset every input to its default",
    )
    return (reset_button,)


@app.cell(hide_code=True)
def _(reset_button: mo.ui.button):
    _ = reset_button  # rerun on reset, recreating these inputs at their defaults

    def _wage_inputs(default_income_value: int) -> mo.ui.dictionary:
        return mo.ui.dictionary(
            {
                "income": mo.ui.slider(
                    start=0,
                    stop=600_000,
                    step=10_000,
                    value=default_income_value,
                    include_input=True,
                    label="Annual wages",
                ),
                "contribution_percent": mo.ui.slider(
                    start=0,
                    stop=50,
                    step=0.5,
                    value=8,
                    include_input=True,
                    label="401(k) contribution (% of gross)",
                ),
            }
        )

    spouse_1_inputs: mo.ui.dictionary = _wage_inputs(default_income_value=220_000)
    spouse_2_inputs: mo.ui.dictionary = _wage_inputs(default_income_value=0)
    return spouse_1_inputs, spouse_2_inputs


@app.cell(hide_code=True)
def _(spouse_1_inputs: mo.ui.dictionary, spouse_2_inputs: mo.ui.dictionary):
    def _panel(inputs: mo.ui.dictionary) -> mo.Html:
        return mo.vstack(
            [
                inputs["income"],
                inputs["contribution_percent"],
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
def _(reset_button: mo.ui.button):
    _ = reset_button  # rerun on reset, recreating these inputs at their defaults
    upfront_cash: mo.ui.number = mo.ui.number(
        start=300_000,
        step=1_000,
        stop=500_000,
        value=340_000,
        label="Available cash",
    )
    return (upfront_cash,)


@app.cell(hide_code=True)
def _(reset_button: mo.ui.button):
    _ = reset_button  # rerun on reset, recreating these inputs at their defaults
    monthly_expenses: mo.ui.slider = mo.ui.slider(
        start=2_000,
        step=100,
        stop=10_000,
        value=3_500,
        include_input=True,
        label="Monthly expenses",
    )
    health_insurance: mo.ui.number = mo.ui.number(
        start=0,
        step=1,
        label="Health insurance",
    )
    return health_insurance, monthly_expenses


@app.cell(hide_code=True)
def _(reset_button: mo.ui.button):
    _ = reset_button  # rerun on reset, recreating these inputs at their defaults
    home_price: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=2_000_000,
        step=10_000,
        value=1_250_000,
        include_input=True,
        label="Home price",
    )

    down_payment_input_percentage: mo.ui.slider = mo.ui.slider(
        start=MIN_DOWN_PAYMENT_SHARE * 100,
        stop=50,
        step=0.5,
        value=20,
        include_input=True,
        label="Down payment (% of price)",
    )

    down_payment_input_amount: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=2_000_000,
        step=10_000,
        value=250_000,
        include_input=True,
        label="Down payment (amount)",
    )

    down_payment_display: mo.ui.radio = mo.ui.radio(
        options=["Percentage", "Amount"], value="Percentage", inline=True
    )

    mortgage_rate: mo.ui.slider = mo.ui.slider(
        start=0.0,
        stop=15.0,
        step=0.125,
        include_input=True,
        label="Mortgage rate",
        value=7.25,
    )
    return (
        down_payment_display,
        down_payment_input_amount,
        down_payment_input_percentage,
        home_price,
        mortgage_rate,
    )


@app.cell(hide_code=True)
def _(reset_button: mo.ui.button):
    _ = reset_button  # rerun on reset, recreating these inputs at their defaults
    building_type: mo.ui.radio = mo.ui.radio(
        options=["Condo", "Co-op"], value="Condo", inline=True
    )

    condo_or_coop_fees: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=5_000,
        step=1,
        include_input=True,
        label="Condo or co-op fees (monthly)",
        value=1000,
    )

    property_tax_input_percentage: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=3,
        step=0.05,
        value=0.9,
        include_input=True,
        label="Property tax (annual % of price)",
    )

    property_tax_input_amount: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=5_000,
        step=1,
        value=950,
        include_input=True,
        label="Property tax (monthly)",
    )

    property_tax_display: mo.ui.radio = mo.ui.radio(
        options=["Percentage", "Amount"], value="Amount", inline=True
    )

    # Shown on the co-op's year-end letter; deductible like mortgage interest.
    coop_interest_portion: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=5_000,
        step=25,
        value=250,
        include_input=True,
        label="Co-op interest (monthly)",
    )

    # HO-6 "walls-in" coverage; the building's master policy is in the fees.
    homeowners_insurance: mo.ui.slider = mo.ui.slider(
        start=0,
        stop=500,
        step=5,
        value=50,
        include_input=True,
        label="Insurance (monthly)",
    )
    return (
        building_type,
        condo_or_coop_fees,
        coop_interest_portion,
        homeowners_insurance,
        property_tax_display,
        property_tax_input_amount,
        property_tax_input_percentage,
    )


@app.cell(hide_code=True)
def _(building_type: mo.ui.radio):
    # Conservative (high-end) NYC defaults; they reset when the building type
    # changes, including on a full reset (which recreates building_type).
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

    # Labels live here rather than on the inputs so the display can align them
    # in a column.
    closing_labels: dict[str, str] = {
        "buyer_attorney": "Our attorney",
        "lender_attorney": "Lender's attorney",
        "lender_fees": "Lender fees (application, appraisal, credit)",
        "building_fees": "Building fees",
        "recording_and_misc": "Recording, searches, and misc.",
        "points": "Points (% of loan)",
        "buyer_broker": "Our broker (% of price)",
        "title_insurance": "Title insurance (% of price)",
        "escrow_months": "Property tax escrow (months collected upfront)",
        "tax_adjustment_months": "Seller reimbursement: property tax (months)",
        "fee_adjustment_months": "Seller reimbursement: fees (months)",
        "moving": "Moving and setup",
    }

    closing_inputs: mo.ui.dictionary = mo.ui.dictionary(
        {
            "buyer_attorney": _flat("buyer_attorney"),
            "lender_attorney": _flat("lender_attorney"),
            "lender_fees": _flat("lender_fees"),
            "building_fees": _flat("building_fees"),
            "recording_and_misc": _flat("recording_and_misc"),
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
            # prepaid months we'll own; same for the current month's fees.
            "tax_adjustment_months": mo.ui.number(
                start=0, stop=6, step=1, value=3, full_width=True
            ),
            "fee_adjustment_months": mo.ui.number(
                start=0, stop=3, step=1, value=1, full_width=True
            ),
            "moving": mo.ui.number(start=0, step=500, value=5_000, full_width=True),
        }
    )
    return closing_inputs, closing_labels


@app.cell(hide_code=True)
def _(
    building_type: mo.ui.radio,
    closing_inputs: mo.ui.dictionary,
    condo_or_coop_fees: mo.ui.slider,
    coop_interest_portion: mo.ui.slider,
    down_payment_display: mo.ui.radio,
    down_payment_input_amount: mo.ui.slider,
    down_payment_input_percentage: mo.ui.slider,
    health_insurance: mo.ui.number,
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
):
    def _wages(inputs: mo.ui.dictionary) -> dict[str, float]:
        values = inputs.value
        income = number(values["income"])
        contribution_401k = employee_deferral(
            income, percent=number(values["contribution_percent"])
        )
        return {
            "income": income,
            "contribution_401k": contribution_401k,
            "pretax_deductions": contribution_401k,
            "fica_wages": max(income - contribution_401k, 0),
        }

    _spouses = [_wages(spouse_1_inputs), _wages(spouse_2_inputs)]

    household: Household = Household(
        gross_income=sum(spouse["income"] for spouse in _spouses),
        pretax_deductions=sum(spouse["pretax_deductions"] for spouse in _spouses),
        contribution_401k=sum(spouse["contribution_401k"] for spouse in _spouses),
        fica_wages_per_person=[spouse["fica_wages"] for spouse in _spouses],
        monthly_expenses=monthly_expenses.value,
        health_insurance=number(health_insurance.value),
        available_cash=number(upfront_cash.value),
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
        closing={key: number(value) for key, value in closing_inputs.value.items()},
    )

    result: Result = evaluate(household, home)
    return home, household, result


@app.cell(hide_code=True)
def _(home: Home, household: Household):
    # Highest price at which each card stays green, or at least not red,
    # holding every other input fixed.
    def _max_price(
        verdict: Callable[[Result], Verdict], allowed: set[str]
    ) -> float | None:
        return max_affordable_price(
            household, home, lambda result: verdict(result).kind in allowed
        )

    def _monthly(result: Result) -> Verdict:
        return result.monthly_verdict

    def _closing(result: Result) -> Verdict:
        return result.closing_verdict

    max_prices: dict[str, tuple[float | None, float | None]] = {
        "Monthly budget": (
            _max_price(_monthly, {"success"}),
            _max_price(_monthly, {"success", "warn"}),
        ),
        "Cash at closing": (
            _max_price(_closing, {"success"}),
            _max_price(_closing, {"success", "warn"}),
        ),
    }
    return (max_prices,)


@app.cell(hide_code=True)
def _(
    home: Home,
    household: Household,
    max_prices: dict[str, tuple[float | None, float | None]],
    result: Result,
):
    def _money(amount: float) -> str:
        return f"−${-amount:,.0f}" if amount < 0 else f"${amount:,.0f}"

    def _card(
        value: str, label: str, caption: str, kind: CardKind = "neutral"
    ) -> mo.Html:
        return mo.callout(mo.stat(value=value, label=label, caption=caption), kind=kind)

    def _row(*cards: mo.Html) -> mo.Html:
        return mo.hstack(list(cards), widths="equal", gap=1)

    def _price(amount: float | None) -> str:
        return "under \\$10,000" if amount is None else f"\\${amount:,.0f}"

    def _lowest(prices: tuple[float | None, ...]) -> float | None:
        known = [price for price in prices if price is not None]
        return min(known) if len(known) == len(prices) else None

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
    _held_fixed = "Holding every other input fixed, in \\$10,000 steps." + (
        ""
        if home.property_tax_is_percent
        else f" Property tax stays at \\${home.property_tax:,.0f}/month."
    )

    _monthly = result.monthly_verdict
    _closing = result.closing_verdict
    mo.vstack(
        [
            mo.md("# Can we afford it?"),
            _row(
                _card(
                    _money(result.total_monthly_payment),
                    "Monthly payment",
                    "mortgage, fees, tax, insurance",
                ),
                _card(
                    _money(result.monthly_leftover),
                    "Left over each month†",
                    _monthly.label,
                    _monthly.kind,
                ),
            ),
            _row(
                _card(
                    _money(result.cash_needed_at_closing),
                    "Cash needed at closing",
                    f"of {_money(household.available_cash)} available*",
                ),
                _card(
                    _money(result.closing_cushion),
                    "Cash left after closing*",
                    _closing.label,
                    _closing.kind,
                ),
            ),
            mo.md(
                "\\* Available cash and cash left after closing exclude any "
                "emergency funds, which stay untouched.  \n"
                "† Assumes the tax savings from itemizing arrive in each paycheck. "
                "In practice, the tax savings may arrive in a refund, making monthly "
                "budgeting a little tighter."
            ).style(font_size="0.85rem", color="var(--muted-foreground, gray)"),
            mo.md("### How high can we go?"),
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
    mortgage_rate: mo.ui.slider,
    property_tax_display: mo.ui.radio,
    property_tax_input_amount: mo.ui.slider,
    property_tax_input_percentage: mo.ui.slider,
    result: Result,
):
    if result.down_payment_raised:
        _down_payment_note = (
            f"Below the {MIN_DOWN_PAYMENT_SHARE:.0%} minimum, so using "
            f"\\${result.down_payment:,.0f}."
        )
    elif home.down_payment_is_percent:
        _down_payment_note = f"= \\${result.down_payment:,.0f}"
    else:
        _share = result.down_payment / home.price if home.price else 0.0
        _down_payment_note = f"= {_share:.1%} of price"

    _property_tax_note = (
        "Condo taxes are billed to you separately from common charges, "
        "so they're added to the monthly payment."
        if building_type.value == "Condo"
        else "Co-op taxes are already inside maintenance, so enter the tax "
        "portion of maintenance here. It counts toward the SALT deduction "
        "but isn't added to the monthly payment again."
    )

    housing_panel: mo.Html = mo.vstack(
        [
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
            *([coop_interest_portion] if building_type.value == "Co-op" else []),
            homeowners_insurance,
        ]
    )
    return (housing_panel,)


@app.cell(hide_code=True)
def _(
    health_insurance: mo.ui.number,
    housing_panel: mo.Html,
    income_panel: mo.ui.tabs,
    monthly_expenses: mo.ui.slider,
    reset_button: mo.ui.button,
    upfront_cash: mo.ui.number,
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
            ),
            _section("Housing", housing_panel),
            _section(
                "Monthly expenses",
                mo.md(
                    "Typical credit card bill plus padding, rather than an itemized budget, at least for now."
                ).style(font_size="0.85rem"),
                monthly_expenses,
                health_insurance,
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
        *(f"| {label} | \\${amount:,.0f} | {note} |" for label, amount, note in _rows),
        f"| **Total monthly payment** | **\\${result.total_monthly_payment:,.0f}** | on a \\${result.loan_amount:,.0f} loan |",
    ]
    mo.vstack([mo.md("### Monthly payment"), mo.md("\n".join(_lines))])
    return


@app.cell(hide_code=True)
def _(household: Household, result: Result):
    _leftover = (
        f"−\\${-result.monthly_leftover:,.0f}"
        if result.monthly_leftover < 0
        else f"\\${result.monthly_leftover:,.0f}"
    )

    mo.vstack(
        [
            mo.md("### Monthly budget"),
            mo.md(f"""
    | | Monthly |
    |:---|---:|
    | Net take-home pay | \\${result.monthly_net:,.0f} |
    | Housing payment | −\\${result.total_monthly_payment:,.0f} |
    | Other expenses | −\\${household.monthly_expenses:,.0f} |
    | Health insurance | −\\${household.health_insurance:,.0f} |
    | **Left over** | **{_leftover}** |
    """),
        ]
    )
    return


@app.cell(hide_code=True)
def _(
    closing_inputs: mo.ui.dictionary,
    closing_labels: dict[str, str],
    home: Home,
    result: Result,
):
    def _rows(items: dict[str, float]) -> str:
        return "\n".join(
            f"| {name} | \\${amount:,.0f} |" for name, amount in items.items() if amount
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
            for _key, _input in closing_inputs.items()
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
    | **Total closing costs** | **\\${result.closing_costs_total:,.0f}** ({_share:.1%} of price) |

    | Prepaid item | Amount |
    |:---|---:|
    {_rows(result.prepaid_items)}
    | **Total prepaid items** | **\\${result.prepaid_total:,.0f}** |

    | Cash at closing | Amount |
    |:---|---:|
    | Down payment | \\${result.down_payment:,.0f} |
    | Closing costs | \\${result.closing_costs_total:,.0f} |
    | Prepaid items | \\${result.prepaid_total:,.0f} |
    | Moving and setup | \\${result.moving_costs:,.0f} |
    | **Cash needed at closing** | **\\${result.cash_needed_at_closing:,.0f}** |
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
                f"| {label} | \\${amount:,.0f} | {note} |"
                for label, amount, note in rows
            ),
            f"| **{_label}** | **\\${_amount:,.0f}** | {_note} |",
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
                    f"standard is \\${NY_MFJ_2026.standard_deduction:,.0f}",
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
                f"One-time tax savings from points (year 1 only, not in the monthly figures): **\\${result.points_tax_savings:,.0f}**"
            )
        )
    mo.accordion({"Tax details": mo.vstack(_details)})
    return


if __name__ == "__main__":
    app.run()
