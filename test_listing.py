from listing import Listing, parse_listing

# Select-all text from a StreetEasy condo listing (370 Union St #2C,
# October 2026), trimmed to the parts around the numbers and the lines that
# could be mistaken for them.
CONDO_PAGE = """\
Skip Navigation
Open menu
Report listing
370 Union Street #2C
$1,345,000
for sale
- ft²

5 rooms

3 beds

1 bath

Condo

Carroll Gardens
Resale

Common charges

$512/mo

Estimated payment

$9,111/mo


LEGAL DISCLAIMER
Calculate
Taxes

$983/mo

Tax abatement

No info

Description
CONDO. NO BOARD APPROVAL. RENTALS PERMITTED. MOVE-IN READY.

About the building
Condo building in
Carroll Gardens
Date\tPrice/Event
9/24/2026

$1,345,000

Listed by Destination Real Estate
Median asking price

3 beds

$2.15M

Median asking base rent

3 beds

$7,975
More homes
Condos for sale
Co-ops for sale
"""

# Select-all text from a StreetEasy co-op listing (161 Henry St #7A,
# October 2026), trimmed the same way. Taxes are folded into maintenance.
COOP_PAGE = """\
Map
161 Henry Street #7A
$1,300,000
for sale
- ft²

4 rooms

2 beds

1 bath

Co-op

Brooklyn Heights
Resale

Request a tour
Report listing
Maintenance fees

$1,875/mo

Estimated payment

$9,236/mo


LEGAL DISCLAIMER
Calculate
Taxes

Included in maintenance fees

Tax abatement

No info

About the building
Co-op building in
Brooklyn Heights
"""


def test_condo() -> None:
    assert parse_listing(CONDO_PAGE) == Listing(
        address="370 Union Street #2C",
        price=1_345_000,
        building_type="Condo",
        monthly_fees=512,
        monthly_taxes=983,
    )


def test_coop() -> None:
    assert parse_listing(COOP_PAGE) == Listing(
        address="161 Henry Street #7A",
        price=1_300_000,
        building_type="Co-op",
        monthly_fees=1_875,
        monthly_taxes=None,
    )


def test_condop_counts_as_condo() -> None:
    assert parse_listing("$1,000,000\nCondop\n").building_type == "Condo"


def test_price_on_first_line_has_no_address() -> None:
    assert parse_listing("$1,000,000\nCondo\n").address is None


def test_labels_on_one_line() -> None:
    # Some browsers copy a label and its value onto the same line.
    listing = parse_listing("Common charges $512/mo Taxes $983 / mo")
    assert (listing.monthly_fees, listing.monthly_taxes) == (512, 983)


def test_unrelated_text() -> None:
    listing = parse_listing("Just some notes about the apartment, $2.15M nearby.")
    assert listing.is_empty
    assert parse_listing("").is_empty
