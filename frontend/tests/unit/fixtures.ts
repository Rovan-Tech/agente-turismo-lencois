import { fireEvent, screen } from "@testing-library/react";

import type {
  ConversationDetail,
  ConversationHeader,
  ConversationSummary,
  Tour,
} from "../../src/types";

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

const SAMPLE_HEADER: ConversationHeader = {
  id: "abc123",
  whatsapp_phone: "5598999998888",
  status: "aberta",
  idioma_detectado: "pt",
  created_at: "2026-09-25T12:00:00Z",
  updated_at: "2026-09-25T12:01:00Z",
};

export const SAMPLE_CONVERSATION: ConversationDetail = {
  ...SAMPLE_HEADER,
  messages: [
    {
      id: "m1",
      direction: "entrada",
      tipo: "texto",
      conteudo: "quero um passeio",
      idioma: "pt",
      created_at: "2026-09-25T12:00:00Z",
    },
  ],
};

export function summary(overrides: Partial<ConversationSummary> = {}): ConversationSummary {
  return { ...SAMPLE_HEADER, ultima_mensagem: null, ...overrides };
}
