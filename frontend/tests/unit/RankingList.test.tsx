import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RankingList } from "../../src/features/analytics/components/RankingList";

describe("RankingList", () => {
  it("shows an empty state instead of an empty list", () => {
    render(<RankingList title="Idiomas" description="desc" rows={[]} />);

    expect(screen.getByText("Sem dados neste período.")).toBeInTheDocument();
  });

  it("shows each row's label, count, share and sub-text", () => {
    render(
      <RankingList
        title="Idiomas"
        description="desc"
        rows={[
          { rotulo: "PT", quantidade: 80, percentual: 80, sub: "informativo" },
          { rotulo: "EN", quantidade: 20, percentual: null, sub: null },
        ]}
      />
    );

    expect(screen.getByText("PT")).toBeInTheDocument();
    expect(screen.getByText("80 · 80%")).toBeInTheDocument();
    expect(screen.getByText("informativo")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
  });
});
