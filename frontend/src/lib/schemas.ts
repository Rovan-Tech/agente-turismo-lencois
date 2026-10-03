import { z } from "zod";

/**
 * Contratos das respostas da API de conversas. Tudo que chega do servidor passa por aqui antes de
 * virar dado da tela; os tipos (`z.infer`) saem destes schemas, então tipo e validação não divergem.
 * Datas chegam em texto ISO 8601 com fuso (UTC) e só a exibição converte.
 */

export const ConversationStatusSchema = z.enum(["aberta", "precisa_atencao", "resolvida"]);

export const HandlingSchema = z.enum(["ia", "humano"]);

export const MessageAuthorSchema = z.enum(["turista", "ia", "atendente"]);

export const SuggestedTourSchema = z.object({
  id: z.string(),
  nome: z.string(),
  descricao: z.string(),
  dificuldade_fisica: z.enum(["baixa", "media", "alta"]),
  caminhada_areia_minutos: z.number(),
  acessivel_idosos: z.boolean(),
  acessivel_cadeirantes: z.boolean(),
  acessivel_criancas_pequenas: z.boolean(),
  duracao_horas: z.number(),
  faixa_etaria_recomendada: z.string(),
  preco_reais: z.number(),
});

export const ConversationMessageSchema = z.object({
  id: z.string(),
  direction: z.enum(["entrada", "saida"]),
  tipo: z.enum(["texto", "audio_transcrito"]),
  conteudo: z.string(),
  idioma: z.string().nullable(),
  autor: MessageAuthorSchema,
  created_at: z.string(),
});

export const ConversationHeaderSchema = z.object({
  id: z.string(),
  whatsapp_phone: z.string(),
  status: ConversationStatusSchema,
  idioma_detectado: z.string().nullable(),
  // Quem responde agora; o nome e o `sub` só vêm preenchidos quando é uma pessoa (`humano`).
  atendimento: HandlingSchema,
  atendente_nome: z.string().nullable(),
  atendente_sub: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const LastMessageSchema = ConversationMessageSchema.pick({
  conteudo: true,
  tipo: true,
  direction: true,
  created_at: true,
});

export const ConversationSummarySchema = ConversationHeaderSchema.extend({
  ultima_mensagem: LastMessageSchema.nullable(),
});

export const ConversationDetailSchema = ConversationHeaderSchema.extend({
  passeio_sugerido: SuggestedTourSchema.nullable(),
  messages: z.array(ConversationMessageSchema),
});

export const ConversationListSchema = z.array(ConversationSummarySchema);

/**
 * Contratos do agendamento com pagamento simulado (nenhum gateway real é integrado).
 * `data` chega em texto ISO 8601 (`YYYY-MM-DD`), sem hora: só a exibição formata.
 */

export const PaymentMethodSchema = z.enum(["pix", "boleto", "cartao"]);

export const PaymentStatusSchema = z.enum(["pendente", "pago"]);

export const DayOccupancySchema = z.object({
  data: z.string(),
  capacidade: z.number(),
  ocupadas: z.number(),
});

export const DayOccupancyListSchema = z.array(DayOccupancySchema);

/** Vagas de um passeio ativo num dia (`GET /api/tours/vagas?dia=`). */
export const TourAvailabilitySchema = z.object({
  tour_id: z.string(),
  capacidade: z.number(),
  ocupadas: z.number(),
});

export const TourAvailabilityListSchema = z.array(TourAvailabilitySchema);

export const BookingSchema = z.object({
  id: z.string(),
  tour_id: z.string(),
  data: z.string(),
  pessoas: z.number(),
  forma_pagamento: PaymentMethodSchema,
  status_pagamento: PaymentStatusSchema,
  telefone: z.string().nullable(),
  created_at: z.string(),
});

export const BookingListSchema = z.array(BookingSchema);

export const BookingCreatedSchema = BookingSchema.extend({
  capacidade: z.number(),
  ocupadas: z.number(),
});

/** Quem está logado: o `sub` identifica a pessoa e `nome` é o primeiro nome que o turista verá. */
export const MeSchema = z.object({ sub: z.string(), nome: z.string().nullable() });

export const TranslateResponseSchema = z.object({ traducao: z.string() });

/** Os três idiomas que o Groq traduz (ver `docs/decisoes-de-arquitetura.md`). */
export type TargetLanguage = "pt" | "en" | "es";

export const AnalyticsSummarySchema = z.object({
  conversas: z.number(),
  vendas: z.number(),
  taxa_conversao_pct: z.number(),
  resolvidas_so_ia_pct: z.number(),
  primeira_resposta_humana_min: z.number().nullable(),
});

/** Uma linha de ranking (destino, idioma, passeio…); `percentual` é nulo sem um total com sentido. */
export const AnalyticsBarSchema = z.object({
  rotulo: z.string(),
  quantidade: z.number(),
  percentual: z.number().nullable(),
  sub: z.string().nullable(),
});

export const AnalyticsHeatmapSchema = z.object({
  dias: z.array(z.string()),
  faixas: z.array(z.string()),
  valores: z.array(z.array(z.number())),
});

export const AnalyticsSchema = z.object({
  periodo_dias: z.number(),
  periodos_disponiveis: z.array(z.number()),
  atual: AnalyticsSummarySchema,
  anterior: AnalyticsSummarySchema,
  pessoas_em_passeios: z.number(),
  pessoas_em_passeios_anterior: z.number(),
  destinos: z.array(AnalyticsBarSchema),
  quem_atendeu: z.array(AnalyticsBarSchema),
  por_pessoa: z.array(AnalyticsBarSchema),
  passeios: z.array(AnalyticsBarSchema),
  idiomas: z.array(AnalyticsBarSchema),
  mapa_calor: AnalyticsHeatmapSchema,
});
