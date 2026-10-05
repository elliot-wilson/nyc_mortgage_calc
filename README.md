# Mortgage

A [marimo](https://marimo.io) notebook for deciding whether we can afford an NYC condo
(or co-op): the monthly payment against our take-home pay and budget, the cash needed at
closing against our savings, and the highest price that keeps both comfortable.

## Running it

```bash
uv run marimo run monthly_income.py
```

Use `uv run marimo edit monthly_income.py` to change the notebook.

## Type checking

```bash
uv run marimo check --fix monthly_income.py && uv run pyright
```

Pyright fails on any untyped parameter, including notebook cell parameters. Annotate every
value shared between cells where it's defined (e.g. `result: Result = evaluate(...)`) and
marimo writes that type into the signature of each cell that uses it. It does this when
saving from the editor or on `marimo check --fix`. Imports live in the notebook's
`app.setup` block so those annotations resolve. The plain modules are checked in strict
mode.

## Layout

| File | What it does |
|---|---|
| `monthly_income.py` | The notebook: inputs in the sidebar, results in the main column |
| `affordability.py` | Evaluates a purchase (payment, closing cash, taxes, verdicts) and searches for the maximum affordable price; the green/yellow/red thresholds live here |
| `household_tax.py` | Federal, NYS, and NYC income tax plus FICA for the household, including the housing deductions |
| `closing_costs.py` | NYS mansion tax and NYC mortgage recording tax |
| `mortgage.py` | Monthly payment and first-year interest for a 30-year fixed loan |
| `fed_tax.py`, `nys_tax.py`, `nyc_tax.py`, `fica_tax.py`, `retirement_401k.py` | 2026 tax schedules and limits for married filing jointly |
