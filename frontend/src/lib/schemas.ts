import { z } from "zod";

/**
 * Contratos das respostas da API de conversas. Tudo que chega do servidor passa por aqui antes de
 * virar dado da tela; os tipos (`z.infer`) saem destes schemas, então tipo e validação não divergem.
 * Datas chegam em texto ISO 8601 com fuso (UTC) e só a exibição converte.
 */

export const ConversationStatusSchema = z.enum(["aberta", "precisa_atencao", "resolvida"]);

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
  created_at: z.string(),
});

export const ConversationHeaderSchema = z.object({
  id: z.string(),
  whatsapp_phone: z.string(),
  status: ConversationStatusSchema,
  idioma_detectado: z.string().nullable(),
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
