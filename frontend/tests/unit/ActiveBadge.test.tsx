import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ActiveBadge } from "../../src/components/ActiveBadge";

describe("ActiveBadge", () => {
  it("shows Ativo for an active tour", () => {
    render(<ActiveBadge ativo={true} />);
    expect(screen.getByRole("status")).toHaveTextContent("Ativo");
  });

  it("shows Inativo for a deactivated tour", () => {
    render(<ActiveBadge ativo={false} />);
    expect(screen.getByRole("status")).toHaveTextContent("Inativo");
  });
});
