import type { z } from "zod";

import type {
  ConversationDetailSchema,
  ConversationHeaderSchema,
  ConversationMessageSchema,
  ConversationStatusSchema,
  ConversationSummarySchema,
  HandlingSchema,
  LastMessageSchema,
  MeSchema,
  SuggestedTourSchema,
} from "./lib/schemas";

// Tipos das respostas de conversas: derivados dos schemas Zod (lib/schemas.ts).
export type ConversationStatus = z.infer<typeof ConversationStatusSchema>;
export type ConversationMessage = z.infer<typeof ConversationMessageSchema>;
/** Campos comuns a tudo que a API devolve sobre uma conversa. */
export type ConversationHeader = z.infer<typeof ConversationHeaderSchema>;
/** Última mensagem da conversa, truncada pela API para a prévia da lista. */
export type LastMessage = z.infer<typeof LastMessageSchema>;
export type ConversationSummary = z.infer<typeof ConversationSummarySchema>;
export type ConversationDetail = z.infer<typeof ConversationDetailSchema>;
export type Handling = z.infer<typeof HandlingSchema>;
/** A pessoa logada no painel (Cloudflare Access). */
export type Me = z.infer<typeof MeSchema>;
/** Passeio do catálogo que o assistente recomendou nesta conversa. */
export type SuggestedTour = z.infer<typeof SuggestedTourSchema>;

export type DifficultyLevel = "baixa" | "media" | "alta";

export interface Tour {
  id: string;
  nome: string;
  descricao: string;
  dificuldade_fisica: DifficultyLevel;
  caminhada_areia_minutos: number;
  acessivel_idosos: boolean;
  acessivel_cadeirantes: boolean;
  acessivel_criancas_pequenas: boolean;
  duracao_horas: number;
  faixa_etaria_recomendada: string;
  preco_reais: number;
  ativo: boolean;
}

/** Payload de `POST /api/tours`: `ativo` é opcional (o backend assume `true`). */
export type TourCreateInput = Omit<Tour, "ativo"> & { ativo?: boolean };

/** Payload de `PUT /api/tours/{id}`: substituição completa, `ativo` é obrigatório. */
export type TourUpdateInput = Omit<Tour, "id">;
