"""Métricas da tela Análises: agregações sobre conversas, mensagens e agendamentos.

Cada métrica cobre um dos três períodos que a tela oferece (7/30/90 dias) e também o período
imediatamente anterior, de mesmo tamanho, para o delta mostrado ao lado. "Assuntos mais
perguntados" e "motivo da transferência pra pessoa" (do desenho do redesign) ficaram de fora:
exigiriam uma classificação nova por IA que não existe hoje (dívida em docs/tech-debt.md).

Simplificações assumidas (sem dado melhor disponível):
- "Virou venda": o telefone (não a conversa específica) tem alguma reserva paga, em qualquer data.
  Reaproveitar a mesma conversa por telefone é raro neste produto (single-tenant), então a
  diferença para "esta conversa gerou esta reserva" é desprezível.
- "1ª resposta humana": da última mensagem do turista antes da primeira mensagem do atendente até
  essa mensagem (não há registro de quando a conversa passou a precisar de atenção).
- Mapa de calor: única exceção ao "datas em UTC, só a exibição converte" (`reliability-data.md`) —
  a agência é de um único lugar (Lençóis Maranhenses) e a grade por dia/horário só serve pra
  escalar a equipe na hora local dela, então o bucket é calculado no fuso da agência.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, PaymentStatus
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageAuthor, MessageDirection
from app.models.tour import Tour

PERIODOS_DIAS = (7, 30, 90)
AGENCY_TZ = ZoneInfo("America/Fortaleza")  # fuso fixo da agência (sem horário de verão no Brasil)
HEAT_DAY_LABELS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
HEAT_HOUR_BUCKETS = ((6, 9), (9, 12), (12, 15), (15, 18), (18, 21), (21, 24))
HEAT_HOUR_LABELS = ("6-9h", "9-12h", "12-15h", "15-18h", "18-21h", "21-24h")


class InvalidPeriodError(Exception):
    """O período pedido não é um dos três que a tela oferece (7, 30 ou 90 dias)."""


@dataclass(slots=True, frozen=True)
class _ConversationFacts:
    """O que cada conversa do período precisa, já resolvido, para todas as métricas."""

    phone: str
    status: ConversationStatus
    idioma: str | None
    created_at: datetime
    teve_atendente: bool
    atendente_sub: str | None
    minutos_ate_atendente: float | None


def _period_bounds(period_days: int, now: datetime) -> tuple[datetime, datetime, datetime]:
    """(início do período anterior, início do atual, fim) — os dois períodos têm o mesmo tamanho."""
    end = now
    start = end - timedelta(days=period_days)
    prev_start = start - timedelta(days=period_days)
    return prev_start, start, end


def _handling_facts(conversation: Conversation, messages: list[Message]) -> _ConversationFacts:
    """Resolve, a partir das mensagens, se e quando uma pessoa da equipe respondeu primeiro."""
    primeiro = next((m for m in messages if m.autor == MessageAuthor.ATENDENTE), None)
    minutos = None
    if primeiro is not None:
        perguntas = [
            m
            for m in messages
            if m.created_at < primeiro.created_at and m.direction == MessageDirection.ENTRADA
        ]
        if perguntas:
            minutos = (primeiro.created_at - perguntas[-1].created_at).total_seconds() / 60
    return _ConversationFacts(
        phone=conversation.whatsapp_phone,
        status=conversation.status,
        idioma=conversation.idioma_detectado,
        created_at=conversation.created_at,
        teve_atendente=primeiro is not None,
        atendente_sub=primeiro.autor_sub if primeiro else None,
        minutos_ate_atendente=minutos,
    )


async def _load_conversations(
    db: AsyncSession, start: datetime, end: datetime
) -> list[_ConversationFacts]:
    """Conversas criadas em `[start, end)`, com os fatos de atendimento humano já resolvidos."""
    conversations = (
        (
            await db.execute(
                select(Conversation).where(
                    Conversation.created_at >= start, Conversation.created_at < end
                )
            )
        )
        .scalars()
        .all()
    )
    if not conversations:
        return []
    ids = [c.id for c in conversations]
    messages = (
        (
            await db.execute(
                select(Message)
                .where(Message.conversation_id.in_(ids))
                .order_by(Message.conversation_id, Message.created_at)
            )
        )
        .scalars()
        .all()
    )
    by_conversation: dict[str, list[Message]] = {}
    for message in messages:
        by_conversation.setdefault(message.conversation_id, []).append(message)
    return [
        _handling_facts(conversation, by_conversation.get(conversation.id, []))
        for conversation in conversations
    ]


async def _booking_status_by_phone(db: AsyncSession, phones: set[str]) -> dict[str, PaymentStatus]:
    """Para cada telefone, `PAGO` se tiver alguma reserva paga, senão `PENDENTE` se tiver alguma."""
    if not phones:
        return {}
    rows = (
        await db.execute(
            select(Booking.telefone, Booking.status_pagamento).where(Booking.telefone.in_(phones))
        )
    ).all()
    best: dict[str, PaymentStatus] = {}
    for phone, status in rows:
        if phone is not None and best.get(phone) != PaymentStatus.PAGO:
            best[phone] = status
    return best


def _destino(facts: _ConversationFacts, booking_status: PaymentStatus | None) -> str:
    """Onde a conversa terminou, pro bloco "O que aconteceu com as conversas"."""
    if booking_status == PaymentStatus.PAGO:
        return "Virou venda"
    if booking_status == PaymentStatus.PENDENTE:
        return "Reserva criada, não paga"
    if facts.status == ConversationStatus.RESOLVIDA:
        return "Resolvida, sem reserva"
    return "Em andamento"


def _bar(
    label: str, value: float, total: float | None, sub: str | None = None
) -> dict[str, object]:
    """Uma linha de barra horizontal: rótulo, valor e que fração do total ele representa.

    O tamanho visual da barra (relativo ao maior valor da lista) é conta do front; `total=None`
    quando a lista não tem um "total" com sentido (ex.: pessoas em cada passeio).
    """
    pct = round(value / total * 100, 1) if total else None
    return {"rotulo": label, "quantidade": value, "percentual": pct, "sub": sub}


def _destinos(destinos: list[str], total: int) -> list[dict[str, object]]:
    counts: dict[str, int] = {}
    for destino in destinos:
        counts[destino] = counts.get(destino, 0) + 1
    order = ["Virou venda", "Em andamento", "Reserva criada, não paga", "Resolvida, sem reserva"]
    return [_bar(label, counts[label], total) for label in order if label in counts]


def _quem_atendeu(facts: list[_ConversationFacts]) -> list[dict[str, object]]:
    total = len(facts)
    com_apoio = sum(1 for f in facts if f.teve_atendente)
    return [
        _bar("Só a IA", total - com_apoio, total),
        _bar("Com apoio humano", com_apoio, total),
    ]


def _por_pessoa(
    facts: list[_ConversationFacts], destino_by_phone: dict[str, str]
) -> list[dict[str, object]]:
    by_sub: dict[str, list[_ConversationFacts]] = {}
    for fact in facts:
        if fact.atendente_sub:
            by_sub.setdefault(fact.atendente_sub, []).append(fact)
    rows = []
    for sub, group in sorted(by_sub.items(), key=lambda kv: len(kv[1]), reverse=True):
        tempos = [f.minutos_ate_atendente for f in group if f.minutos_ate_atendente is not None]
        vendas = sum(1 for f in group if destino_by_phone.get(f.phone) == "Virou venda")
        mediana = round(statistics.median(tempos), 1) if tempos else None
        sub_label = f"{mediana} min até a 1ª resposta" if mediana is not None else "sem dado"
        rows.append(_bar(sub, len(group), len(facts), f"{sub_label} · {vendas} vendas"))
    return rows


def _idiomas(
    facts: list[_ConversationFacts], destino_by_phone: dict[str, str]
) -> list[dict[str, object]]:
    by_lang: dict[str, list[_ConversationFacts]] = {}
    for fact in facts:
        by_lang.setdefault(fact.idioma or "não detectado", []).append(fact)
    rows = []
    for lang, group in sorted(by_lang.items(), key=lambda kv: len(kv[1]), reverse=True):
        vendas = sum(1 for f in group if destino_by_phone.get(f.phone) == "Virou venda")
        taxa = round(vendas / len(group) * 100, 1) if group else 0.0
        rows.append(_bar(lang.upper(), len(group), len(facts), f"{taxa}% viraram venda"))
    return rows


def _as_aware_utc(moment: datetime) -> datetime:
    """SQLite devolve data sem fuso; sem isso, `.astimezone()` leria como hora local da máquina."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _heatmap(facts: list[_ConversationFacts]) -> dict[str, object]:
    grade = [[0] * len(HEAT_HOUR_BUCKETS) for _ in HEAT_DAY_LABELS]
    for fact in facts:
        local = _as_aware_utc(fact.created_at).astimezone(AGENCY_TZ)
        day = local.weekday()
        for bucket_index, (start_hour, end_hour) in enumerate(HEAT_HOUR_BUCKETS):
            if start_hour <= local.hour < end_hour:
                grade[day][bucket_index] += 1
                break
    return {"dias": list(HEAT_DAY_LABELS), "faixas": list(HEAT_HOUR_LABELS), "valores": grade}


def _paid_in_period(start: datetime, end: datetime) -> tuple[ColumnElement[bool], ...]:
    """Condições comuns às consultas de reservas pagas do período (evita repetir o `where`)."""
    return (
        Booking.status_pagamento == PaymentStatus.PAGO,
        Booking.created_at >= start,
        Booking.created_at < end,
    )


async def _tour_metrics(
    db: AsyncSession, start: datetime, end: datetime
) -> list[dict[str, object]]:
    """Pessoas em reservas pagas e ocupação média das saídas de cada passeio ativo, no período."""
    rows = (
        await db.execute(
            select(Booking.tour_id, Booking.data, func.sum(Booking.pessoas))
            .where(*_paid_in_period(start, end))
            .group_by(Booking.tour_id, Booking.data)
        )
    ).all()
    by_tour: dict[str, list[int]] = {}
    for tour_id, _data, total in rows:
        by_tour.setdefault(tour_id, []).append(int(total))
    tours = (await db.execute(select(Tour).where(Tour.ativo.is_(True)))).scalars().all()
    linhas: list[tuple[int, str, float]] = []
    for tour in tours:
        dias = by_tour.get(tour.id, [])
        if not dias:
            continue
        pessoas = sum(dias)
        ocupacao = round(sum(d / tour.capacidade_diaria for d in dias) / len(dias) * 100, 1)
        linhas.append((pessoas, tour.nome, ocupacao))
    linhas.sort(key=lambda linha: linha[0], reverse=True)
    return [
        _bar(nome, pessoas, None, f"ocupação média de {ocupacao}%")
        for pessoas, nome, ocupacao in linhas
    ]


async def _pessoas_em_passeios(db: AsyncSession, start: datetime, end: datetime) -> int:
    total = (
        await db.execute(
            select(func.coalesce(func.sum(Booking.pessoas), 0)).where(*_paid_in_period(start, end))
        )
    ).scalar_one()
    return int(total)


def _summary(
    facts: list[_ConversationFacts], destino_by_phone: dict[str, str]
) -> dict[str, object]:
    total = len(facts)
    vendas = sum(1 for f in facts if destino_by_phone.get(f.phone) == "Virou venda")
    com_apoio = sum(1 for f in facts if f.teve_atendente)
    tempos = [f.minutos_ate_atendente for f in facts if f.minutos_ate_atendente is not None]
    return {
        "conversas": total,
        "vendas": vendas,
        "taxa_conversao_pct": round(vendas / total * 100, 1) if total else 0.0,
        "resolvidas_so_ia_pct": round((total - com_apoio) / total * 100, 1) if total else 0.0,
        "primeira_resposta_humana_min": round(statistics.median(tempos), 1) if tempos else None,
    }


async def compute_analytics(db: AsyncSession, period_days: int) -> dict[str, object]:
    """Monta o payload inteiro da tela Análises para um dos três períodos oferecidos.

    Raises:
        InvalidPeriodError: `period_days` não é 7, 30 nem 90.
    """
    if period_days not in PERIODOS_DIAS:
        raise InvalidPeriodError(period_days)
    now = datetime.now(UTC)
    prev_start, start, end = _period_bounds(period_days, now)
    current = await _load_conversations(db, start, end)
    previous = await _load_conversations(db, prev_start, start)
    phones = {f.phone for f in current} | {f.phone for f in previous}
    booking_status = await _booking_status_by_phone(db, phones)
    # Pra quem tem reserva, o destino só depende do pagamento, não da conversa específica
    # (`_destino` só olha `facts.status` quando não há reserva nenhuma).
    destino_by_phone = {
        phone: "Virou venda" if status == PaymentStatus.PAGO else "Reserva criada, não paga"
        for phone, status in booking_status.items()
    }
    destinos_atuais = [_destino(f, booking_status.get(f.phone)) for f in current]

    return {
        "periodo_dias": period_days,
        "periodos_disponiveis": list(PERIODOS_DIAS),
        "atual": _summary(current, destino_by_phone),
        "anterior": _summary(previous, destino_by_phone),
        "pessoas_em_passeios": await _pessoas_em_passeios(db, start, end),
        "pessoas_em_passeios_anterior": await _pessoas_em_passeios(db, prev_start, start),
        "destinos": _destinos(destinos_atuais, len(current)),
        "quem_atendeu": _quem_atendeu(current),
        "por_pessoa": _por_pessoa(current, destino_by_phone),
        "passeios": await _tour_metrics(db, start, end),
        "idiomas": _idiomas(current, destino_by_phone),
        "mapa_calor": _heatmap(current),
    }
