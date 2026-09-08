"""Local VAT/IBAN/BIC validation belongs to the shared parties models."""

import pytest
from django.core.exceptions import ValidationError

from tests.messaging_models import Bank, BankAccount, Party


@pytest.mark.parametrize(("country", "value", "canonical"), [
    ("de", "DE136695976", "DE136695976"),
    ("NL", "NL123456782B12", "NL123456782B12"),
    ("LV", "LV40003521600", "LV40003521600"),
])
def test_vat_uses_country_validator(country, value, canonical):
    party = Party(tax_country=country, vat=value)
    party.clean()
    assert party.vat == canonical
    assert party.tax_country == country.upper()


@pytest.mark.parametrize(("country", "value"), [("DE", "DE136695977"), ("", "123"), ("ZZ", "123")])
def test_invalid_vat_is_rejected(country, value):
    with pytest.raises(ValidationError):
        Party(tax_country=country, vat=value).clean()


def test_iban_canonicalization_and_bank_country():
    bank = Bank(pk=1, name="Bank", bic="DEUTDEFF")
    bank.clean()
    account = BankAccount(bank=bank, account_number="DE89 3704 0044 0532 0130 00")
    account.clean()
    assert account.account_number == "DE89370400440532013000"
    bank.country = "NL"
    with pytest.raises(ValidationError):
        account.clean()


def test_bad_bic_and_iban_are_rejected():
    with pytest.raises(ValidationError):
        Bank(name="Bank", bic="INVALID").clean()
    with pytest.raises(ValidationError):
        BankAccount(account_number="DE00370400440532013000").clean()
