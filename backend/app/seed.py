"""Popula o catálogo inicial de passeios. Rodar com: python -m app.seed"""

import asyncio

from app.db.base import Base
from app.db.session import async_session_factory, engine
from app.models.tour import DifficultyLevel, Tour

TOURS = [
    Tour(
        id="lagoa-azul-bonita",
        nome="Lagoa Azul e Lagoa Bonita (passeio clássico 4x4 + caminhada nas dunas)",
        descricao=(
            "O passeio mais famoso: 4x4 até as dunas e caminhada de ~25min na areia quente até "
            "as lagoas mais bonitas da região. Exige preparo físico por causa da caminhada na "
            "areia fofa sob sol forte."
        ),
        dificuldade_fisica=DifficultyLevel.ALTA,
        caminhada_areia_minutos=25,
        acessivel_idosos=False,
        acessivel_cadeirantes=False,
        acessivel_criancas_pequenas=False,
        duracao_horas=4,
        faixa_etaria_recomendada="8 a 65 anos, sem limitação de mobilidade",
        preco_reais=150,
    ),
    Tour(
        id="vale-do-paraiso",
        nome="Vale do Paraíso",
        descricao=(
            "Dunas mais próximas do centro de Barreirinhas, caminhada curta (~10min) até o "
            "mirante e a lagoa principal. Bom para quem quer ver dunas sem caminhada longa."
        ),
        dificuldade_fisica=DifficultyLevel.MEDIA,
        caminhada_areia_minutos=10,
        acessivel_idosos=False,
        acessivel_cadeirantes=False,
        acessivel_criancas_pequenas=True,
        duracao_horas=3,
        faixa_etaria_recomendada="6 a 70 anos com mobilidade razoável",
        preco_reais=120,
    ),
    Tour(
        id="passeio-bugre-orla",
        nome="Passeio de bugre pela orla e mirante das dunas",
        descricao=(
            "Passeio motorizado com caminhada mínima (~5min em piso firme até o mirante). "
            "Feito majoritariamente sentado no veículo. Melhor opção para quem tem dificuldade "
            "de locomoção."
        ),
        dificuldade_fisica=DifficultyLevel.BAIXA,
        caminhada_areia_minutos=5,
        acessivel_idosos=True,
        acessivel_cadeirantes=True,
        acessivel_criancas_pequenas=True,
        duracao_horas=2.5,
        faixa_etaria_recomendada=(
            "todas as idades, incluindo idosos e pessoas com mobilidade reduzida"
        ),
        preco_reais=100,
    ),
    Tour(
        id="rio-preguicas-pequenos-lencois",
        nome="Rio Preguiças + Pequenos Lençóis + Vassouras (passeio de barco)",
        descricao=(
            "Maior parte do tempo sentado em uma lancha pelo rio Preguiças, com paradas curtas "
            "em dunas e no farol de Mandacaru. Boa opção para idosos que preferem não caminhar "
            "muito, mas o embarque no barco tem alguns degraus."
        ),
        dificuldade_fisica=DifficultyLevel.BAIXA,
        caminhada_areia_minutos=8,
        acessivel_idosos=True,
        acessivel_cadeirantes=False,
        acessivel_criancas_pequenas=True,
        duracao_horas=6,
        faixa_etaria_recomendada=(
            "todas as idades, incluindo idosos; não recomendado para cadeirantes por causa do "
            "embarque no barco"
        ),
        preco_reais=180,
    ),
    Tour(
        id="trilha-das-emendas",
        nome="Trilha das Emendas",
        descricao=(
            "Trilha longa entre dunas com pouca sombra, recomendada só para quem tem bom "
            "condicionamento físico. Não indicada para idosos, crianças pequenas ou pessoas com "
            "medo de altura em alguns trechos de subida."
        ),
        dificuldade_fisica=DifficultyLevel.ALTA,
        caminhada_areia_minutos=90,
        acessivel_idosos=False,
        acessivel_cadeirantes=False,
        acessivel_criancas_pequenas=False,
        duracao_horas=5,
        faixa_etaria_recomendada="12 a 55 anos, bom preparo físico",
        preco_reais=130,
    ),
]


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        for tour in TOURS:
            await session.merge(tour)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
