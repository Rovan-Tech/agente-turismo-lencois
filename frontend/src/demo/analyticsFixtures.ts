import type { Analytics } from "../types";

/**
 * Análises de demonstração: números fixos e plausíveis, não uma agregação ao vivo (ADR-0007). As
 * categorias usam os mesmos rótulos que `app/services/analytics.py` devolve de verdade.
 */
function bar(rotulo: string, quantidade: number, percentual: number | null, sub: string | null) {
  return { rotulo, quantidade, percentual, sub };
}

const BASE: Record<
  number,
  { conv: number; sales: number; people: number; ai: number; resp: number }
> = {
  7: { conv: 96, sales: 22, people: 64, ai: 69, resp: 7 },
  30: { conv: 412, sales: 87, people: 263, ai: 71, resp: 6 },
  90: { conv: 1180, sales: 236, people: 701, ai: 68, resp: 8 },
};

const PREV_FACTOR = 0.89;

function summary(period: number) {
  const b = BASE[period];
  const rate = (b.sales / b.conv) * 100;
  return {
    atual: {
      conversas: b.conv,
      vendas: b.sales,
      taxa_conversao_pct: Math.round(rate * 10) / 10,
      resolvidas_so_ia_pct: b.ai,
      primeira_resposta_humana_min: b.resp,
    },
    anterior: {
      conversas: Math.round(b.conv * PREV_FACTOR),
      vendas: Math.round(b.sales * PREV_FACTOR),
      taxa_conversao_pct: Math.round(rate * PREV_FACTOR * 10) / 10,
      resolvidas_so_ia_pct: Math.round(b.ai * 0.95),
      primeira_resposta_humana_min: b.resp + 1,
    },
    pessoas_em_passeios: b.people,
    pessoas_em_passeios_anterior: Math.round(b.people * PREV_FACTOR),
  };
}

export function demoAnalytics(period: number): Analytics {
  const b = BASE[period] ?? BASE[30];
  const s = summary(period in BASE ? period : 30);
  const semVenda = b.conv - b.sales;
  return {
    periodo_dias: period,
    periodos_disponiveis: [7, 30, 90],
    ...s,
    destinos: [
      bar("Virou venda", b.sales, Math.round((b.sales / b.conv) * 1000) / 10, null),
      bar("Em andamento", Math.round(semVenda * 0.35), null, null),
      bar("Resolvida, sem reserva", Math.round(semVenda * 0.5), null, null),
      bar("Reserva criada, não paga", Math.round(semVenda * 0.15), null, null),
    ],
    quem_atendeu: [
      bar("Só a IA", b.ai, b.ai, null),
      bar("Com apoio humano", 100 - b.ai, 100 - b.ai, null),
    ],
    por_pessoa: [
      bar(
        "Bia",
        Math.round(b.conv * 0.08),
        null,
        `4 min até a 1ª resposta · ${Math.round(b.sales * 0.12)} vendas`
      ),
      bar(
        "Patrick",
        Math.round(b.conv * 0.12),
        null,
        `7 min até a 1ª resposta · ${Math.round(b.sales * 0.19)} vendas`
      ),
      bar(
        "Leandro",
        Math.round(b.conv * 0.09),
        null,
        `9 min até a 1ª resposta · ${Math.round(b.sales * 0.12)} vendas`
      ),
    ],
    passeios: [
      bar("Lagoa Azul de 4x4", Math.round(b.people * 0.35), null, "ocupação média de 78%"),
      bar("Rio Preguiças de lancha", Math.round(b.people * 0.27), null, "ocupação média de 70%"),
      bar("Pequenos Lençóis", Math.round(b.people * 0.22), null, "ocupação média de 61%"),
      bar("Lagoa Bonita ao pôr do sol", Math.round(b.people * 0.16), null, "ocupação média de 44%"),
    ],
    idiomas: [
      bar("PT", Math.round(b.conv * 0.6), 60, null),
      bar("ES", Math.round(b.conv * 0.18), 18, null),
      bar("EN", Math.round(b.conv * 0.13), 13, null),
      bar("FR", Math.round(b.conv * 0.06), 6, null),
      bar("Outros", Math.round(b.conv * 0.03), 3, null),
    ],
    mapa_calor: {
      dias: ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"],
      faixas: ["6-9h", "9-12h", "12-15h", "15-18h", "18-21h", "21-24h"],
      valores: [
        [1, 3, 3, 4, 6, 4],
        [1, 2, 3, 4, 5, 3],
        [1, 3, 3, 3, 6, 4],
        [1, 3, 4, 4, 7, 5],
        [2, 4, 4, 6, 9, 6],
        [2, 5, 6, 7, 10, 6],
        [3, 6, 6, 8, 9, 5],
      ],
    },
  };
}
