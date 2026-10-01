"""Atendimento humano: assumir e devolver a conversa, com o aviso ao turista (ADR-0008)."""

import logging
from datetime import UTC, datetime, timedelta

import pytest

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import MessageAuthor
from tests.access_support import NO_BEARER, panel_headers
from tests.handoff_support import (
    PHONE,
    all_messages,
    assert_refused,
    give_back,
    make_conversation,
    meta_html_error,
    meta_rejection,
    take_over,
)

pytestmark = pytest.mark.asyncio


def _url(conversation: Conversation, action: str = "") -> str:
    return f"/api/conversations/{conversation.id}{action}"


# --- Assumir: o turista é avisado, com o primeiro nome vindo do login ---------------------------


async def test_take_over_announces_a_person_to_the_tourist_and_switches_to_human(
    client, db_session, access, conversation, outbox
):
    response = await take_over(client, access, conversation)

    assert response.status_code == 200
    assert response.json()["atendimento"] == "humano"
    assert response.json()["atendente_nome"] == "Pessoa"
    [(to, text)] = outbox.sent
    assert to == PHONE
    assert "pessoa da nossa equipe: Pessoa" in text
    announcement = (await all_messages(db_session))[-1]
    assert (announcement.autor, announcement.autor_sub) == (MessageAuthor.ATENDENTE, "pessoa-123")
    assert announcement.conteudo == text


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("pt", "Agora quem está falando com você é uma pessoa da nossa equipe: Pessoa"),
        ("en", "You are now talking to a person from our team: Pessoa"),
        ("es", "Ahora te atiende una persona de nuestro equipo: Pessoa"),
        (None, "You are now talking to a person from our team: Pessoa"),
    ],
    ids=["pt", "en", "es", "unknown_is_trilingual"],
)
async def test_announcement_follows_the_language_of_the_conversation(
    client, db_session, access, outbox, language, expected
):
    conversation = await make_conversation(db_session, language=language)

    await take_over(client, access, conversation)

    assert expected in outbox.sent[0][1]


async def test_announcement_uses_the_first_name_from_the_login_email(
    client, access, conversation, outbox
):
    await take_over(
        client, access, conversation, access.token(email="patrick.fernandes@rovantech.com")
    )

    assert "equipe: Patrick." in outbox.sent[0][1]
    assert "Fernandes" not in outbox.sent[0][1]


async def test_announcement_without_a_usable_name_says_a_person_of_the_team(
    client, access, conversation, outbox
):
    await take_over(client, access, conversation, access.token(email="vendas123@rovantech.com"))

    assert "uma pessoa da nossa equipe. Pode continuar" in outbox.sent[0][1]
    assert "vendas" not in outbox.sent[0][1].lower()


async def test_take_over_never_stores_logs_or_sends_the_email(
    client, db_session, access, conversation, outbox, caplog
):
    caplog.set_level(logging.DEBUG, logger="app")
    await take_over(
        client, access, conversation, access.token(email="patrick.fernandes@rovantech.com")
    )

    await db_session.refresh(conversation)
    stored = [m.conteudo for m in await all_messages(db_session)] + [conversation.humano_nome]
    assert all("rovantech" not in str(value) for value in stored)
    assert "rovantech" not in outbox.sent[0][1]
    logged = " ".join((caplog.text, *(str(vars(record)) for record in caplog.records)))
    assert "pessoa-123" in logged
    assert "rovantech" not in logged


# --- Assumir: as recusas -----------------------------------------------------------------------


async def test_take_over_again_by_the_same_person_does_not_resend_the_announcement(
    client, db_session, access, conversation, outbox
):
    await take_over(client, access, conversation)
    long_ago = datetime.now(UTC) - timedelta(hours=1)
    conversation.humano_atividade_em = long_ago
    await db_session.commit()

    again = await take_over(client, access, conversation)

    await db_session.refresh(conversation)
    assert (again.status_code, len(outbox.sent)) == (200, 1)
    assert conversation.humano_atividade_em.replace(tzinfo=UTC) > long_ago + timedelta(minutes=30)


async def test_take_over_a_conversation_held_by_another_person_is_409(
    client, access, conversation, outbox
):
    await take_over(client, access, conversation, access.token(email="ana.souza@rovantech.com"))

    response = await take_over(client, access, conversation, access.token(sub="outra-pessoa"))

    assert response.status_code == 409
    assert "Ana" in response.json()["detail"]
    assert len(outbox.sent) == 1


async def test_take_over_a_resolved_conversation_is_refused(client, db_session, access, outbox):
    conversation = await make_conversation(db_session, status=ConversationStatus.RESOLVIDA)

    response = await take_over(client, access, conversation)

    assert_refused(response, outbox)


@pytest.mark.parametrize("tourist_minutes_ago", [24 * 60 + 5, None], ids=["over_24h", "no_message"])
async def test_take_over_with_the_window_closed_is_409_and_keeps_ia(
    client, db_session, access, outbox, tourist_minutes_ago
):
    conversation = await make_conversation(db_session, tourist_minutes_ago=tourist_minutes_ago)

    response = await take_over(client, access, conversation)

    assert response.status_code == 409
    assert "24 horas" in response.json()["detail"]
    await db_session.refresh(conversation)
    assert (conversation.atendimento, outbox.sent) == ("ia", [])


async def test_take_over_meta_failure_keeps_ia_and_saves_nothing(
    client, db_session, access, conversation, outbox
):
    outbox.failure = meta_rejection()

    response = await take_over(client, access, conversation)

    assert response.status_code == 502
    assert "131047" in response.json()["detail"]
    assert "detalhe-interno-da-meta" not in response.text
    assert "PHONE_ID_SECRETO" not in response.text
    await db_session.refresh(conversation)
    assert conversation.atendimento == "ia"
    assert [m.autor for m in await all_messages(db_session)] == [MessageAuthor.TURISTA]


async def test_take_over_unknown_conversation_is_404(client, access, outbox):
    response = await client.post(
        "/api/conversations/nao-existe/assumir", headers=panel_headers(access.token())
    )

    assert response.status_code == 404


# --- Devolver para a IA ------------------------------------------------------------------------


async def test_give_back_returns_to_ia_and_tells_the_tourist(
    client, db_session, access, conversation, outbox
):
    await take_over(client, access, conversation)

    response = await give_back(client, access, conversation)

    assert response.status_code == 200
    assert response.json()["atendimento"] == "ia"
    await db_session.refresh(conversation)
    assert (conversation.humano_sub, conversation.humano_nome) == (None, None)
    assert "assistente virtual" in outbox.sent[-1][1]
    assert len(outbox.sent) == 2


async def test_give_back_with_the_window_closed_still_returns_to_ia_without_a_message(
    client, db_session, access, outbox
):
    conversation = await make_conversation(
        db_session,
        tourist_minutes_ago=24 * 60 + 5,
        atendimento="humano",
        humano_sub="pessoa-123",
        humano_nome="Pessoa",
        humano_desde=datetime.now(UTC),
        humano_atividade_em=datetime.now(UTC),
    )

    response = await give_back(client, access, conversation)

    assert response.json()["atendimento"] == "ia"
    assert outbox.sent == []


async def test_give_back_a_conversation_already_with_ia_sends_nothing(
    client, access, conversation, outbox
):
    response = await give_back(client, access, conversation)

    assert (response.status_code, outbox.sent) == (200, [])


async def test_resolving_a_conversation_returns_it_to_ia(
    client, db_session, access, conversation, outbox
):
    await take_over(client, access, conversation)

    response = await client.patch(
        _url(conversation, "/status"),
        json={"status": "resolvida"},
        headers=panel_headers(access.token()),
    )

    assert response.json()["atendimento"] == "ia"
    await db_session.refresh(conversation)
    assert conversation.humano_sub is None


# --- O painel lê o estado e quem é a pessoa logada ----------------------------------------------


async def test_summary_and_detail_expose_the_handling_state_and_the_message_author(
    client, access, conversation, outbox
):
    await take_over(client, access, conversation)
    headers = {**NO_BEARER, **panel_headers(access.token())}

    listed = (await client.get("/api/conversations", headers=headers)).json()[0]
    detail = (await client.get(_url(conversation), headers=headers)).json()

    assert (listed["atendimento"], listed["atendente_nome"]) == ("humano", "Pessoa")
    assert listed["atendente_sub"] == "pessoa-123"
    assert [m["autor"] for m in detail["messages"]] == ["turista", "atendente"]


async def test_me_tells_who_is_logged_in(client, access):
    response = await client.get("/api/me", headers=panel_headers(access.token()))

    assert response.json() == {"sub": "pessoa-123", "nome": "Pessoa"}


async def test_me_needs_a_person_login_not_the_static_token(client):
    response = await client.get("/api/me")

    assert response.status_code == 403


async def test_give_back_still_returns_to_ia_when_the_meta_refuses_the_notice(
    client, db_session, access, held, outbox
):
    outbox.failure = meta_rejection()

    response = await give_back(client, access, held)

    assert (response.status_code, response.json()["atendimento"]) == (200, "ia")
    await db_session.refresh(held)
    assert (held.humano_sub, [m.autor for m in await all_messages(db_session)]) == (
        None,
        [MessageAuthor.TURISTA],
    )


async def test_take_over_meta_failure_without_a_provider_code_still_says_it_failed(
    client, access, conversation, outbox
):
    outbox.failure = meta_html_error()

    response = await take_over(client, access, conversation)

    assert response.status_code == 502
    assert "WhatsApp" in response.json()["detail"]
    assert "código" not in response.json()["detail"]
