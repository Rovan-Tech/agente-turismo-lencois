export type ConversationStatus = "aberta" | "precisa_atencao" | "resolvida";

export interface ConversationMessage {
  id: string;
  direction: "entrada" | "saida";
  tipo: "texto" | "audio_transcrito";
  conteudo: string;
  idioma: string | null;
  created_at: string;
}

/** Campos comuns a tudo que a API devolve sobre uma conversa. */
export interface ConversationHeader {
  id: string;
  whatsapp_phone: string;
  status: ConversationStatus;
  idioma_detectado: string | null;
  created_at: string;
  updated_at: string;
}

/** Última mensagem da conversa, truncada pela API para a prévia da lista. */
export type LastMessage = Pick<
  ConversationMessage,
  "conteudo" | "tipo" | "direction" | "created_at"
>;

export interface ConversationSummary extends ConversationHeader {
  ultima_mensagem: LastMessage | null;
}

export interface ConversationDetail extends ConversationHeader {
  messages: ConversationMessage[];
}

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
