import { useEffect, useState } from "react";

import { Heatmap } from "../features/analytics/components/Heatmap";
import { KpiCard } from "../features/analytics/components/KpiCard";
import { PeriodPicker } from "../features/analytics/components/PeriodPicker";
import { RankingList } from "../features/analytics/components/RankingList";
import { delta, formatInt, formatPercent } from "../features/analytics/format";
import { getAnalytics } from "../lib/api";
import type { Analytics } from "../types";

type State = { status: "loading" } | { status: "error" } | { status: "ready"; data: Analytics };

export function AnalisesPage() {
  const [period, setPeriod] = useState(30);
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    getAnalytics(period).then((data) => {
      if (!active) return;
      setState(data === null ? { status: "error" } : { status: "ready", data });
    });
    return () => {
      active = false;
    };
  }, [period]);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-primary">Análises</h1>
          <p className="mt-1 text-sm text-secondary">
            Quantas conversas viram passeios vendidos, como a IA e a equipe atendem e o que mais (e
            menos) sai.
          </p>
        </div>
        <PeriodPicker
          options={state.status === "ready" ? state.data.periodos_disponiveis : [7, 30, 90]}
          active={period}
          onChange={setPeriod}
        />
      </div>

      {state.status === "loading" && <p className="mt-8 text-muted">Carregando…</p>}
      {state.status === "error" && (
        <p role="alert" className="mt-8 text-sm text-status-error">
          Não foi possível carregar as análises.
        </p>
      )}

      {state.status === "ready" && <AnalisesContent data={state.data} />}
    </main>
  );
}

function AnalisesContent({ data }: Readonly<{ data: Analytics }>) {
  const { atual, anterior } = data;
  const conversasDelta = delta(atual.conversas, anterior.conversas, "pct", "up");
  const pessoasDelta = delta(
    data.pessoas_em_passeios,
    data.pessoas_em_passeios_anterior,
    "pct",
    "up"
  );
  const iaDelta = delta(atual.resolvidas_so_ia_pct, anterior.resolvidas_so_ia_pct, "pp", "up");
  const respostaDelta =
    atual.primeira_resposta_humana_min === null || anterior.primeira_resposta_humana_min === null
      ? null
      : delta(
          atual.primeira_resposta_humana_min,
          anterior.primeira_resposta_humana_min,
          "min",
          "down"
        );

  return (
    <div className="mt-6 flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          hero
          label="Conversas que viraram venda"
          value={formatPercent(atual.taxa_conversao_pct)}
          sub={`${formatInt(atual.vendas)} vendas em ${formatInt(atual.conversas)} conversas`}
          delta={delta(atual.taxa_conversao_pct, anterior.taxa_conversao_pct, "pp", "up")}
        />
        <KpiCard
          label="Conversas"
          value={formatInt(atual.conversas)}
          sub="iniciadas por turistas"
          delta={conversasDelta}
        />
        <KpiCard
          label="Pessoas em passeios"
          value={formatInt(data.pessoas_em_passeios)}
          sub="em reservas pagas"
          delta={pessoasDelta}
        />
        <KpiCard
          label="Resolvidas só pela IA"
          value={formatPercent(atual.resolvidas_so_ia_pct)}
          sub="sem ajuda de uma pessoa"
          delta={iaDelta}
        />
        <KpiCard
          label="1ª resposta humana"
          value={
            atual.primeira_resposta_humana_min === null
              ? "—"
              : `${formatInt(atual.primeira_resposta_humana_min)} min`
          }
          sub="mediana; a IA responde em segundos"
          delta={respostaDelta}
        />
      </div>

      {RANKING_ROWS.map(([left, right]) => (
        <div key={left.title} className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <RankingList title={left.title} description={left.description} rows={data[left.field]} />
          <RankingList
            title={right.title}
            description={right.description}
            rows={data[right.field]}
          />
        </div>
      ))}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RankingList
          title="Idiomas dos turistas"
          description="Conversas por idioma detectado pela IA."
          rows={data.idiomas}
        />
        <Heatmap mapa={data.mapa_calor} />
      </div>
    </div>
  );
}

type RankingField = "destinos" | "quem_atendeu" | "por_pessoa" | "passeios";

const RANKING_ROWS: ReadonlyArray<
  readonly [
    { title: string; description: string; field: RankingField },
    { title: string; description: string; field: RankingField },
  ]
> = [
  [
    {
      title: "O que aconteceu com as conversas",
      description: "Onde cada conversa terminou. Em destaque, as que viraram venda.",
      field: "destinos",
    },
    {
      title: "Quem atendeu",
      description: "Parte das conversas resolvida só pela IA, ou com ajuda de uma pessoa.",
      field: "quem_atendeu",
    },
  ],
  [
    {
      title: "Conversas atendidas por pessoa",
      description: "Carga de trabalho da equipe e as vendas fechadas.",
      field: "por_pessoa",
    },
    {
      title: "Passeios: o que mais e o que menos sai",
      description: "Pessoas em reservas pagas, com a ocupação média das saídas.",
      field: "passeios",
    },
  ],
];
