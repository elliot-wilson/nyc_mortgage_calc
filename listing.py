"""Read a StreetEasy sale listing's numbers from its page text.

The text is whatever the browser copies after select-all on the listing page,
so this matches the labels StreetEasy shows rather than its HTML. Anything it
can't find comes back as None, and the notebook keeps its own value.
"""

import re
from dataclasses import dataclass
from typing import Literal

BuildingType = Literal["Condo", "Co-op"]

# The asking price is the first line holding nothing but a dollar amount; the
# monthly figures all end in "/mo", and neighborhood medians are like "$2.15M".
_PRICE = re.compile(r"^\s*\$([\d,]+)\s*$", re.MULTILINE)
# StreetEasy calls condo fees "Common charges" and co-op fees "Maintenance fees".
_FEES = re.compile(
    r"\b(?:Common charges|Maintenance)(?: fees)?\s*\$([\d,]+)\s*/\s*mo", re.I
)
_TAXES = re.compile(r"\bTaxes\s*\$([\d,]+)\s*/\s*mo", re.I)
# The building type sits alone on a line under the beds and baths. A condop's
# taxes are billed separately like a condo's, so it's treated as one.
_BUILDING_TYPE = re.compile(r"^\s*(Condo|Condop|Co-op)\s*$", re.MULTILINE | re.I)


@dataclass(frozen=True)
class Listing:
    address: str | None = None
    price: int | None = None
    building_type: BuildingType | None = None
    monthly_fees: int | None = None  # common charges or maintenance
    monthly_taxes: int | None = None

    @property
    def is_empty(self) -> bool:
        return self == Listing()


def _dollars(pattern: re.Pattern[str], text: str) -> int | None:
    match = pattern.search(text)
    return int(match.group(1).replace(",", "")) if match else None


def _address(text: str) -> str | None:
    """The listing's heading, which is the line just above the asking price."""
    price = _PRICE.search(text)
    if price is None:
        return None
    above = [line.strip() for line in text[: price.start()].splitlines()]
    return next((line for line in reversed(above) if line), None)


def parse_listing(text: str) -> Listing:
    building_type = _BUILDING_TYPE.search(text)
    return Listing(
        address=_address(text),
        price=_dollars(_PRICE, text),
        building_type=(
            None
            if building_type is None
            else "Co-op"
            if building_type.group(1).lower() == "co-op"
            else "Condo"
        ),
        monthly_fees=_dollars(_FEES, text),
        monthly_taxes=_dollars(_TAXES, text),
    )
