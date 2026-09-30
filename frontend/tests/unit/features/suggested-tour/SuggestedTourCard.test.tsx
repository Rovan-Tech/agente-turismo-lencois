import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SuggestedTourCard } from "../../../../src/features/suggested-tour/components/SuggestedTourCard";
import { SAMPLE_SUGGESTED_TOUR } from "../../fixtures";

describe("SuggestedTourCard", () => {
  it("shows the tour name, description, attributes and price", () => {
    render(<SuggestedTourCard tour={SAMPLE_SUGGESTED_TOUR} />);

    expect(screen.getByRole("heading", { name: "Passeio sugerido pela IA" })).toBeInTheDocument();
    expect(screen.getByText("Mirante Vila Acessível")).toBeInTheDocument();
    expect(screen.getByText(/Caminho pavimentado/)).toBeInTheDocument();
    expect(screen.getByText("Dificuldade baixa")).toBeInTheDocument();
    expect(screen.getByText("1h")).toBeInTheDocument();
    expect(screen.getByText("Acessível p/ cadeirantes")).toBeInTheDocument();
    expect(screen.getByText("Acessível p/ idosos")).toBeInTheDocument();
    expect(screen.getByText("R$ 120")).toBeInTheDocument();
    expect(screen.getByText("por pessoa")).toBeInTheDocument();
  });

  it("only shows the accessibility chips the tour really has", () => {
    render(<SuggestedTourCard tour={{ ...SAMPLE_SUGGESTED_TOUR, acessivel_cadeirantes: false }} />);

    expect(screen.queryByText("Acessível p/ cadeirantes")).toBeNull();
    expect(screen.queryByText("Acessível p/ crianças pequenas")).toBeNull();
    expect(screen.getByText("Acessível p/ idosos")).toBeInTheDocument();
  });

  it("hides the elderly chip when the tour is not suitable for them", () => {
    render(<SuggestedTourCard tour={{ ...SAMPLE_SUGGESTED_TOUR, acessivel_idosos: false }} />);

    expect(screen.queryByText("Acessível p/ idosos")).toBeNull();
    expect(screen.getByText("Acessível p/ cadeirantes")).toBeInTheDocument();
  });

  it("says so when the assistant has not suggested a tour yet", () => {
    render(<SuggestedTourCard tour={null} />);

    expect(screen.getByRole("heading", { name: "Passeio sugerido pela IA" })).toBeInTheDocument();
    expect(
      screen.getByText("A IA ainda não sugeriu um passeio nesta conversa.")
    ).toBeInTheDocument();
  });

  it("renders catalog text as plain text, never as HTML", () => {
    const hostile = "<img src=x onerror=alert(1)>Passeio";
    const { container } = render(
      <SuggestedTourCard tour={{ ...SAMPLE_SUGGESTED_TOUR, nome: hostile, descricao: hostile }} />
    );

    expect(container.querySelector("img")).toBeNull();
    expect(screen.getAllByText(hostile)).toHaveLength(2);
  });
});
