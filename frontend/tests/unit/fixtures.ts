import { fireEvent, screen } from "@testing-library/react";

import type { ApiResult } from "../../src/lib/api";
import type {
  Booking,
  ConversationDetail,
  ConversationHeader,
  ConversationSummary,
  DayOccupancy,
  SuggestedTour,
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
  atendimento: "ia",
  atendente_nome: null,
  atendente_sub: null,
  created_at: "2026-09-25T12:00:00Z",
  updated_at: "2026-09-25T12:01:00Z",
};

export const SAMPLE_SUGGESTED_TOUR: SuggestedTour = {
  id: "passeio-bugre-orla",
  nome: "Mirante Vila Acessível",
  descricao: "Caminho pavimentado, sem trecho de areia. Indicado para cadeirantes e idosos.",
  dificuldade_fisica: "baixa",
  caminhada_areia_minutos: 0,
  acessivel_idosos: true,
  acessivel_cadeirantes: true,
  acessivel_criancas_pequenas: false,
  duracao_horas: 1,
  faixa_etaria_recomendada: "todas as idades",
  preco_reais: 120,
};

export const SAMPLE_CONVERSATION: ConversationDetail = {
  ...SAMPLE_HEADER,
  passeio_sugerido: null,
  messages: [
    {
      id: "m1",
      direction: "entrada",
      tipo: "texto",
      conteudo: "quero um passeio",
      idioma: "pt",
      autor: "turista",
      created_at: "2026-09-25T12:00:00Z",
    },
  ],
};

/** Conversa com a pessoa `pessoa-123` atendendo (a mesma que `ME` devolve). */
export const HANDLED_CONVERSATION: ConversationDetail = {
  ...SAMPLE_CONVERSATION,
  atendimento: "humano",
  atendente_nome: "Ana",
  atendente_sub: "pessoa-123",
};

export const ME = { sub: "pessoa-123", nome: "Ana" };

export const TRANSLATE_FAILURE: ApiResult<string> = {
  ok: false,
  status: 503,
  message: "indisponível",
};

export function summary(overrides: Partial<ConversationSummary> = {}): ConversationSummary {
  return { ...SAMPLE_HEADER, ultima_mensagem: null, ...overrides };
}

export const SAMPLE_DAY_OCCUPANCY: DayOccupancy = {
  data: "2026-09-28",
  capacidade: 41,
  ocupadas: 10,
};

export const SAMPLE_BOOKING: Booking = {
  id: "booking-1",
  tour_id: "passeio-bugre-orla",
  data: "2026-09-28",
  pessoas: 3,
  forma_pagamento: "pix",
  status_pagamento: "pago",
  telefone: "5598999998888",
  created_at: "2026-09-28T12:00:00Z",
};
