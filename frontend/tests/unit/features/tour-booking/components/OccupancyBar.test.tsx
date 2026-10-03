import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OccupancyBar } from "../../../../../src/features/tour-booking/components/OccupancyBar";

describe("OccupancyBar", () => {
  it("shows the remaining seats as an accessible progressbar", () => {
    render(<OccupancyBar ocupadas={10} capacidade={41} />);

    const bar = screen.getByRole("progressbar", { name: "Ocupação de hoje: 31 vagas" });
    expect(bar).toHaveAttribute("value", "24");
    expect(bar).toHaveAttribute("max", "100");
    expect(screen.getByText("31 vagas")).toBeInTheDocument();
  });

  it("names the day it describes in the accessible name", () => {
    render(<OccupancyBar ocupadas={10} capacidade={41} dayLabel="amanhã" />);

    expect(screen.getByRole("progressbar", { name: "Ocupação de amanhã: 31 vagas" })).toBeVisible();
  });

  it("says 1 vaga in the singular when only one seat remains", () => {
    render(<OccupancyBar ocupadas={40} capacidade={41} />);

    expect(screen.getByText("1 vaga")).toBeInTheDocument();
  });

  it("says Esgotado, never just a color, when there are no seats left", () => {
    render(<OccupancyBar ocupadas={41} capacidade={41} />);

    expect(screen.getByText("Esgotado")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("value", "100");
  });
});
