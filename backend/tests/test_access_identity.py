"""Primeiro nome da pessoa logada, derivado das claims do JWT verificado (ADR-0008)."""

import pytest

from app.core.access_jwt import first_name_from_claims


@pytest.mark.parametrize(
    ("claims", "expected"),
    [
        ({"name": "Patrick Fernandes"}, "Patrick"),
        ({"name": "PATRICK"}, "Patrick"),
        ({"email": "patrick.fernandes@rovantech.com"}, "Patrick"),
        ({"email": "ana_souza@exemplo.com"}, "Ana"),
        ({"email": "joão-pedro@exemplo.com"}, "João"),
        ({"email": "maria+vendas@exemplo.com"}, "Maria"),
        ({"name": "ab1", "email": "carla@exemplo.com"}, "Carla"),
        ({"name": "Jose\u0301 Silva"}, "José"),
    ],
    ids=[
        "name_claim",
        "upper_case",
        "email_dot",
        "email_underscore",
        "accents",
        "plus_tag",
        "unusable_name_falls_back_to_email",
        "decomposed_accent",
    ],
)
def test_first_name_from_claims_derives_a_capitalized_first_name(claims, expected):
    assert first_name_from_claims(claims) == expected


@pytest.mark.parametrize(
    "claims",
    [
        {},
        {"email": "vendas123@exemplo.com"},
        {"email": "123@exemplo.com"},
        {"email": "contato@exemplo.com"},
        {"email": "admin@exemplo.com"},
        {"email": "a@exemplo.com"},
        {"email": "x" * 31 + "@exemplo.com"},
        {"email": "o'neil@exemplo.com"},
        {"name": "<script>", "email": None},
        {"name": 42, "email": ["lista"]},
        {"email": "sem-arroba"},
        {"email": "@exemplo.com"},
    ],
    ids=[
        "no_claims",
        "digits",
        "only_digits",
        "generic_mailbox",
        "admin_mailbox",
        "single_letter",
        "too_long",
        "symbol_inside",
        "markup",
        "wrong_types",
        "no_at_sign",
        "empty_local_part",
    ],
)
def test_first_name_from_claims_without_a_usable_name_returns_none(claims):
    assert first_name_from_claims(claims) is None
