# Mortgage

A [marimo](https://marimo.io) notebook for deciding whether you can afford an NYC condo
(or co-op): the monthly payment against your take-home pay and budget, the cash needed at
closing against your savings, and the highest price that keeps both comfortable.

## Running it

```bash
uv run marimo run app.py
```

Use `uv run marimo edit app.py` to change the notebook.

## Type checking

```bash
uv run marimo check --fix app.py && uv run pyright
```

## Tests

```bash
uv run pytest
```

Pyright fails on any untyped parameter, including notebook cell parameters. Annotate every
value shared between cells where it's defined (e.g. `result: Result = evaluate(...)`) and
marimo writes that type into the signature of each cell that uses it. It does this when
saving from the editor or on `marimo check --fix`. Imports live in the notebook's
`app.setup` block so those annotations resolve. The plain modules are checked in strict
mode.

## Publishing

Every push to `main` publishes the notebook to GitHub Pages as a static, interactive site
(`.github/workflows/pages.yml`). The workflow type-checks the code, then runs
`marimo export html-wasm`, which runs the Python in the browser via Pyodide, so there's
no server and inputs never leave the visitor's browser. The default input values are
visible to anyone with the link.

To preview the site locally:

```bash
uv run marimo export html-wasm app.py --output _site --mode run
python -m http.server --directory _site
```

One-time setup: in the repository's **Settings → Pages**, set **Source** to **GitHub
Actions**. Pages on a free GitHub account requires a public repository.

## Layout

| File | What it does |
|---|---|
| `app.py` | The notebook: inputs in the sidebar, results in the main column |
| `affordability.py` | Evaluates a purchase (payment, closing cash, taxes, co-op board checks, verdicts) and searches for the maximum affordable price; the green/yellow/red thresholds live here |
| `household_tax.py` | Federal, NYS, and NYC income tax plus FICA for the household, including the housing deductions |
| `listing.py` | Reads the price, fees, and taxes from a StreetEasy listing's copied page text |
| `paste_box.py` | The paste target for listings: sends pasted text to the notebook without showing it |
| `closing_costs.py` | NYS mansion tax and NYC mortgage recording tax |
| `mortgage.py` | Monthly payment and first-year interest for a 30-year fixed loan |
| `fed_tax.py`, `nys_tax.py`, `nyc_tax.py`, `fica_tax.py`, `retirement_401k.py` | 2026 tax schedules and limits for married filing jointly |
| `tax_brackets.py` | Bracket tax and the mortgage-debt limit, shared by the schedules |
