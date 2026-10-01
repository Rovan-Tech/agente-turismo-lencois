/** Dados simulados compartilhados pelos testes E2E (a API real não sobe nestes testes). */
export const SUGGESTED_TOUR = {
  id: "lagoa-azul-barco",
  nome: "Lagoa Azul de barco",
  descricao: "Travessia de barco com parada para banho.",
  dificuldade_fisica: "media",
  caminhada_areia_minutos: 25,
  acessivel_idosos: true,
  acessivel_cadeirantes: false,
  acessivel_criancas_pequenas: true,
  duracao_horas: 2.5,
  faixa_etaria_recomendada: "a partir de 4 anos",
  preco_reais: 180.5,
};

/** Campos de atendimento de uma conversa que a IA responde (nenhuma pessoa assumiu). */
export const HANDLING_BY_AI = { atendimento: "ia", atendente_nome: null, atendente_sub: null };
