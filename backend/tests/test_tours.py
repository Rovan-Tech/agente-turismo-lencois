import pytest


@pytest.mark.asyncio
async def test_list_tours_returns_only_active(client, db_session, sample_tours):
    sample_tours[1].ativo = False
    for tour in sample_tours:
        db_session.add(tour)
    await db_session.commit()

    response = await client.get("/api/tours")
    assert response.status_code == 200
    ids = {t["id"] for t in response.json()}
    assert ids == {"passeio-bugre-orla", "rio-preguicas"}


@pytest.mark.asyncio
async def test_get_unknown_conversation_returns_404(client):
    response = await client.get("/api/conversations/nao-existe")
    assert response.status_code == 404
