"""Federal, New York State, and NYC income tax for the household, with housing deductions."""

from dataclasses import dataclass

from fed_tax import MFJ_2026 as FED_MFJ_2026
from fed_tax import allowed_salt_deduction, federal_income_tax
from fed_tax import deductible_mortgage_interest as fed_mortgage_interest
from fica_tax import medicare_tax, social_security_tax
from nyc_tax import MFJ_2026 as NYC_MFJ_2026
from nyc_tax import nyc_tax
from nys_tax import MFJ_2026 as NY_MFJ_2026
from nys_tax import deductible_mortgage_interest as ny_mortgage_interest
from nys_tax import ny_itemized_deduction, nys_tax


@dataclass(frozen=True)
class IncomeTaxes:
    ny_itemized: float
    ny_deduction: float
    ny_taxable_income: float
    state_tax: float
    city_tax: float
    salt_deduction: float
    mortgage_interest_deduction: float
    federal_itemized: float
    federal_deduction: float
    federal_taxable_income: float
    federal_tax: float

    @property
    def total(self) -> float:
        return self.federal_tax + self.state_tax + self.city_tax

    @property
    def federal_itemizes(self) -> bool:
        return self.federal_itemized > FED_MFJ_2026.standard_deduction

    @property
    def ny_itemizes(self) -> bool:
        return self.ny_itemized > NY_MFJ_2026.standard_deduction


def income_taxes(
    *,
    agi: float,
    property_tax: float,
    mortgage_interest: float,
    loan_amount: float,
    coop_building_interest: float = 0.0,
) -> IncomeTaxes:
    """
    agi: federal AGI, which is also NY AGI for W-2 income without NY modifications.
    mortgage_interest: interest (plus any points) paid on our own loan this year.
    coop_building_interest: our share of a co-op's mortgage interest, passed
        through maintenance. Not subject to the debt limits, which apply to our loan.
    """
    ny_agi = agi

    # IT-196 line 5 wants income taxes paid during the year, i.e. withholding,
    # which payroll tables compute as if we took the standard deduction.
    standard_taxable = max(ny_agi - NY_MFJ_2026.standard_deduction, 0)
    income_taxes_withheld = nys_tax(ny_agi, standard_taxable, NY_MFJ_2026) + nyc_tax(
        standard_taxable, agi, NYC_MFJ_2026
    )

    ny_itemized = ny_itemized_deduction(
        federal_agi=agi,
        ny_agi=ny_agi,
        property_tax=property_tax,
        mortgage_interest=ny_mortgage_interest(
            mortgage_interest, loan_amount, NY_MFJ_2026
        )
        + coop_building_interest,
        state_and_local_income_taxes=income_taxes_withheld,
        tax_schedule=NY_MFJ_2026,
    )
    ny_deduction = max(NY_MFJ_2026.standard_deduction, ny_itemized)
    ny_taxable_income = max(ny_agi - ny_deduction, 0)

    state_tax = nys_tax(ny_agi, ny_taxable_income, NY_MFJ_2026)
    city_tax = nyc_tax(ny_taxable_income, agi, NYC_MFJ_2026)

    # Property tax belongs inside the SALT amount (it shares the cap);
    # mortgage interest gets added to itemized outside it.
    salt_deduction = allowed_salt_deduction(
        state_tax + city_tax + property_tax, agi, FED_MFJ_2026
    )
    mortgage_interest_deduction = (
        fed_mortgage_interest(mortgage_interest, loan_amount, FED_MFJ_2026)
        + coop_building_interest
    )
    federal_itemized = salt_deduction + mortgage_interest_deduction
    federal_deduction = max(FED_MFJ_2026.standard_deduction, federal_itemized)
    federal_taxable_income = max(agi - federal_deduction, 0)

    return IncomeTaxes(
        ny_itemized=ny_itemized,
        ny_deduction=ny_deduction,
        ny_taxable_income=ny_taxable_income,
        state_tax=state_tax,
        city_tax=city_tax,
        salt_deduction=salt_deduction,
        mortgage_interest_deduction=mortgage_interest_deduction,
        federal_itemized=federal_itemized,
        federal_deduction=federal_deduction,
        federal_taxable_income=federal_taxable_income,
        federal_tax=federal_income_tax(federal_taxable_income, FED_MFJ_2026),
    )


def fica_taxes(fica_wages_per_person: list[float]) -> tuple[float, float]:
    """(Social Security, Medicare). Social Security caps per person; Medicare's
    additional tax applies to combined wages."""
    social_security = sum(social_security_tax(wages) for wages in fica_wages_per_person)
    medicare = medicare_tax(sum(fica_wages_per_person))
    return social_security, medicare
