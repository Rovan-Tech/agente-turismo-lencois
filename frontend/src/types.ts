export type ConversationStatus = "aberta" | "precisa_atencao" | "resolvida";

export interface ConversationSummary {
  id: string;
  whatsapp_phone: string;
  status: ConversationStatus;
  idioma_detectado: string | null;
  updated_at: string;
}

export interface ConversationMessage {
  id: string;
  direction: "entrada" | "saida";
  tipo: "texto" | "audio_transcrito";
  conteudo: string;
  idioma: string | null;
  created_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[];
}
