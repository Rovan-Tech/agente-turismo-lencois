import { fireEvent, screen } from "@testing-library/react";

import type { Tour } from "../../src/types";

export const SAMPLE_TOUR: Tour = {
  id: "passeio-bugre-orla",
  nome: "Passeio de bugre",
  descricao: "Caminhada mínima pela orla.",
  dificuldade_fisica: "baixa",
  caminhada_areia_minutos: 5,
  acessivel_idosos: true,
  acessivel_cadeirantes: true,
  acessivel_criancas_pequenas: true,
  duracao_horas: 2.5,
  faixa_etaria_recomendada: "todas as idades",
  preco_reais: 100,
  ativo: true,
};

/** Preenche os campos obrigatórios de `TourForm` para um passeio novo. */
export function fillTourFormRequiredFields(id: string, nome: string) {
  fireEvent.change(screen.getByLabelText("Id"), { target: { value: id } });
  fireEvent.change(screen.getByLabelText("Nome"), { target: { value: nome } });
  fireEvent.change(screen.getByLabelText("Descrição"), { target: { value: "Descrição" } });
  fireEvent.change(screen.getByLabelText("Faixa etária recomendada"), {
    target: { value: "todas as idades" },
  });
}
