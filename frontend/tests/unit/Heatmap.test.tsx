import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Heatmap } from "../../src/features/analytics/components/Heatmap";

describe("Heatmap", () => {
  it("renders a table with a row per day and a column per time bucket", () => {
    render(
      <Heatmap
        mapa={{
          dias: ["seg", "ter"],
          faixas: ["6-9h", "9-12h"],
          valores: [
            [1, 2],
            [0, 3],
          ],
        }}
      />
    );

    expect(screen.getByRole("rowheader", { name: "seg" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "9-12h" })).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
  });
});
