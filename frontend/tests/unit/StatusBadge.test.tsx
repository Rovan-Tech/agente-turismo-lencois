import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "../../src/components/StatusBadge";

describe("StatusBadge", () => {
  it("shows the Portuguese label for each status", () => {
    render(<StatusBadge status="aberta" />);
    expect(screen.getByRole("status")).toHaveTextContent("Aberta");
  });

  it("highlights conversations that need human attention", () => {
    render(<StatusBadge status="precisa_atencao" />);
    const badge = screen.getByRole("status");
    expect(badge).toHaveTextContent("Precisa de atenção");
    expect(badge.className).toContain("bg-action-secondary");
  });

  it("shows resolved status", () => {
    render(<StatusBadge status="resolvida" />);
    expect(screen.getByRole("status")).toHaveTextContent("Resolvida");
  });
});
