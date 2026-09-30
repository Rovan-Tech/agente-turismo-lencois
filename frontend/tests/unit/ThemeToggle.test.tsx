import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ThemeToggle } from "../../src/components/ThemeToggle";

describe("ThemeToggle", () => {
  it("offers dark mode while the theme is light", () => {
    render(<ThemeToggle theme="light" onToggle={() => {}} />);

    expect(screen.getByRole("button", { name: "Usar modo escuro" })).toBeInTheDocument();
  });

  it("offers light mode while the theme is dark", () => {
    render(<ThemeToggle theme="dark" onToggle={() => {}} />);

    expect(screen.getByRole("button", { name: "Usar modo claro" })).toBeInTheDocument();
  });

  it("asks to switch when clicked", () => {
    const onToggle = vi.fn();
    render(<ThemeToggle theme="light" onToggle={onToggle} />);

    fireEvent.click(screen.getByRole("button", { name: "Usar modo escuro" }));

    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});
