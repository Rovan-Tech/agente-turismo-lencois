from app.services import tour_matcher


def test_extract_criteria_detects_elderly_in_portuguese():
    criteria = tour_matcher.extract_criteria("Vou com meu avô de 78 anos, que usa bengala")
    assert criteria["acessivel_idosos"] is True


def test_extract_criteria_detects_elderly_in_english():
    criteria = tour_matcher.extract_criteria("traveling with my elderly mother")
    assert criteria["acessivel_idosos"] is True


def test_extract_criteria_detects_children_in_spanish():
    criteria = tour_matcher.extract_criteria("voy con mis dos hijos pequeños de 5 y 8 años")
    assert criteria["acessivel_criancas_pequenas"] is True


def test_extract_criteria_detects_price_ceiling():
    criteria = tour_matcher.extract_criteria("quero um passeio até R$150")
    assert criteria["preco_maximo"] == 150.0


def test_extract_criteria_detects_duration_ceiling():
    criteria = tour_matcher.extract_criteria("no máximo 3 horas de passeio")
    assert criteria["duracao_maxima_horas"] == 3.0


def test_extract_criteria_empty_for_generic_question():
    assert tour_matcher.extract_criteria("quais passeios vocês têm?") == {}


def test_filter_tours_by_elderly_accessibility(sample_tours):
    filtered = tour_matcher.filter_tours(sample_tours, {"acessivel_idosos": True})
    ids = {t.id for t in filtered}
    assert ids == {"passeio-bugre-orla", "rio-preguicas"}


def test_filter_tours_by_price_ceiling(sample_tours):
    filtered = tour_matcher.filter_tours(sample_tours, {"preco_maximo": 150})
    ids = {t.id for t in filtered}
    assert ids == {"passeio-bugre-orla", "trilha-das-emendas"}


def test_filter_tours_combines_criteria(sample_tours):
    filtered = tour_matcher.filter_tours(
        sample_tours, {"acessivel_idosos": True, "preco_maximo": 150}
    )
    assert [t.id for t in filtered] == ["passeio-bugre-orla"]


def test_select_candidate_tours_falls_back_to_full_catalog_when_no_match(sample_tours):
    candidates = tour_matcher.select_candidate_tours(
        sample_tours, "quero um passeio acessível para cadeirante e até R$50"
    )
    assert len(candidates) == len(sample_tours)


def test_select_candidate_tours_returns_full_catalog_without_criteria(sample_tours):
    candidates = tour_matcher.select_candidate_tours(sample_tours, "quais passeios vocês têm?")
    assert len(candidates) == len(sample_tours)


def test_select_candidate_tours_ignores_inactive_tours(sample_tours):
    sample_tours[1].ativo = False
    candidates = tour_matcher.select_candidate_tours(sample_tours, "quais passeios vocês têm?")
    assert "trilha-das-emendas" not in {t.id for t in candidates}
