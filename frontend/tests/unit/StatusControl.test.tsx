import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { StatusControl } from "../../src/components/StatusControl";
import type { ConversationStatus } from "../../src/types";

function renderControl(status: ConversationStatus, busy = false) {
  const onChange = vi.fn();
  render(<StatusControl status={status} busy={busy} onChange={onChange} />);
  return onChange;
}

/** O nome do Testing Library casa o texto inteiro: "Resolvida" não casa com "Marcar como resolvida". */
const option = (name: string) => screen.getByRole("button", { name });

describe("StatusControl", () => {
  it.each([
    ["aberta", "Aberta"],
    ["precisa_atencao", "Precisa de atenção"],
    ["resolvida", "Resolvida"],
  ] as const)("marks only the current status (%s) as pressed", (status, label) => {
    renderControl(status);

    expect(option(label)).toHaveAttribute("aria-pressed", "true");
    expect(screen.getAllByRole("button", { pressed: true })).toHaveLength(1);
  });

  it.each([
    ["aberta", "Precisa de atenção", "precisa_atencao"],
    ["aberta", "Resolvida", "resolvida"],
    ["resolvida", "Aberta", "aberta"],
    ["precisa_atencao", "Aberta", "aberta"],
  ] as const)("changes from %s to %s", (current, label, expected) => {
    const onChange = renderControl(current);

    fireEvent.click(option(label));

    expect(onChange).toHaveBeenCalledWith(expected);
  });

  it("does nothing when the current status is clicked again", () => {
    const onChange = renderControl("resolvida");

    fireEvent.click(option("Resolvida"));

    expect(option("Resolvida")).toHaveAttribute("aria-disabled", "true");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("blocks every option while the request is in flight but keeps them focusable", () => {
    const onChange = renderControl("aberta", true);

    fireEvent.click(option("Resolvida"));

    expect(option("Resolvida")).toHaveAttribute("aria-disabled", "true");
    expect(option("Resolvida")).not.toBeDisabled();
    expect(onChange).not.toHaveBeenCalled();
  });
});
