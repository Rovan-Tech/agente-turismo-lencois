import type { ConversationDetail, ConversationMessage, Tour } from "../types";

/**
 * Dados 100% fictícios da demonstração. Os telefones usam o DDD `00`, que não existe: nenhum
 * número real pode aparecer aqui (um teste confere). Os horários são relativos a "agora", para o
 * painel parecer vivo e a janela de 24 h do WhatsApp se comportar como no produto.
 */

const MINUTE_MS = 60_000;

function ago(minutes: number): string {
  return new Date(Date.now() - minutes * MINUTE_MS).toISOString();
}

type Author = ConversationMessage["autor"];

function message(
  id: string,
  author: Author,
  text: string,
  minutesAgo: number,
  language: string
): ConversationMessage {
  return {
    id,
    direction: author === "turista" ? "entrada" : "saida",
    tipo: "texto",
    conteudo: text,
    idioma: language,
    autor: author,
    created_at: ago(minutesAgo),
  };
}

type Access = { elderly: boolean; wheelchair: boolean; smallKids: boolean };

/** Atributos do passeio que não são identificação (agrupados para a função não passar de 7 parâmetros). */
type TourSpecs = {
  level: Tour["dificuldade_fisica"];
  sandMinutes: number;
  access: Access;
  hours: number;
  ages: string;
  price: number;
};

function tour(
  id: string,
  nome: string,
  descricao: string,
  { level, sandMinutes, access, hours, ages, price }: TourSpecs
): Tour {
  return {
    id,
    nome,
    descricao,
    dificuldade_fisica: level,
    caminhada_areia_minutos: sandMinutes,
    acessivel_idosos: access.elderly,
    acessivel_cadeirantes: access.wheelchair,
    acessivel_criancas_pequenas: access.smallKids,
    duracao_horas: hours,
    faixa_etaria_recomendada: ages,
    preco_reais: price,
    ativo: true,
  };
}

const EVERYONE: Access = { elderly: true, wheelchair: true, smallKids: true };
const NOT_WHEELCHAIR: Access = { elderly: true, wheelchair: false, smallKids: true };

export const DEMO_TOURS: Tour[] = [
  tour(
    "demo-lagoa-azul",
    "Lagoa Azul de 4x4",
    "Travessia de 4x4 e caminhada curta pelas dunas, com parada para banho.",
    {
      level: "media",
      sandMinutes: 25,
      access: NOT_WHEELCHAIR,
      hours: 4,
      ages: "a partir de 4 anos",
      price: 150,
    }
  ),
  tour(
    "demo-bugre-orla",
    "Passeio de bugre pela orla",
    "Caminhada mínima, acessível a idosos e cadeirantes, com mirante das dunas.",
    {
      level: "baixa",
      sandMinutes: 5,
      access: EVERYONE,
      hours: 2.5,
      ages: "todas as idades",
      price: 100,
    }
  ),
  tour(
    "demo-rio-barco",
    "Rio e pequenos Lençóis (barco)",
    "Passeio de barco pelo rio, com paradas em vilarejos e nas dunas menores.",
    {
      level: "baixa",
      sandMinutes: 8,
      access: NOT_WHEELCHAIR,
      hours: 6,
      ages: "todas as idades",
      price: 180,
    }
  ),
  tour(
    "demo-trilha-longa",
    "Trilha longa das dunas",
    "Trilha de dia inteiro com areia fofa e sol forte. Exige bom preparo físico.",
    {
      level: "alta",
      sandMinutes: 90,
      access: { elderly: false, wheelchair: false, smallKids: false },
      hours: 5,
      ages: "12 a 55 anos",
      price: 130,
    }
  ),
];

const BASE = { passeio_sugerido: null, atendente_nome: null, atendente_sub: null } as const;

export function buildDemoConversations(): ConversationDetail[] {
  return [
    {
      ...BASE,
      id: "demo-c1",
      whatsapp_phone: "5500900000001",
      status: "precisa_atencao",
      idioma_detectado: "en",
      atendimento: "ia",
      passeio_sugerido: DEMO_TOURS[1],
      created_at: ago(60 * 24 * 3),
      updated_at: ago(4),
      messages: [
        message(
          "c1m1",
          "turista",
          "Hi! My mother uses a wheelchair. Can she do any of the tours?",
          12,
          "en"
        ),
        message(
          "c1m2",
          "ia",
          "Yes! The coastal buggy tour has minimal walking and is wheelchair accessible. It costs R$ 100 and lasts 2.5 hours.",
          11,
          "en"
        ),
        message(
          "c1m3",
          "turista",
          "Great. Can I talk to someone from your team about the pickup?",
          4,
          "en"
        ),
      ],
    },
    {
      ...BASE,
      id: "demo-c2",
      whatsapp_phone: "5500900000002",
      status: "aberta",
      idioma_detectado: "pt",
      atendimento: "ia",
      passeio_sugerido: DEMO_TOURS[2],
      created_at: ago(60 * 24 * 2),
      updated_at: ago(35),
      messages: [
        message(
          "c2m1",
          "turista",
          "Somos um casal de idosos, qual passeio vocês recomendam?",
          40,
          "pt"
        ),
        message(
          "c2m2",
          "ia",
          "Recomendo o passeio de barco pelo rio: pouca caminhada, 6 horas e R$ 180 por pessoa. É tranquilo para quem tem mais de 70 anos.",
          39,
          "pt"
        ),
        message("c2m3", "turista", "Perfeito, e tem sombra durante o passeio?", 35, "pt"),
      ],
    },
    {
      ...BASE,
      id: "demo-c3",
      whatsapp_phone: "5500900000003",
      status: "aberta",
      idioma_detectado: "es",
      atendimento: "ia",
      passeio_sugerido: DEMO_TOURS[0],
      created_at: ago(60 * 24),
      updated_at: ago(180),
      messages: [
        message("c3m1", "turista", "¿Cuánto cuesta el paseo a la Laguna Azul?", 190, "es"),
        message(
          "c3m2",
          "ia",
          "El paseo a la Laguna Azul en 4x4 cuesta R$ 150 por persona y dura cerca de 4 horas.",
          189,
          "es"
        ),
      ],
    },
    {
      ...BASE,
      id: "demo-c4",
      whatsapp_phone: "5500900000004",
      status: "precisa_atencao",
      idioma_detectado: "pt",
      atendimento: "ia",
      created_at: ago(60 * 24 * 5),
      updated_at: ago(60 * 30),
      messages: [
        message(
          "c4m1",
          "turista",
          "Vocês fazem passeio noturno com observação de estrelas?",
          60 * 30,
          "pt"
        ),
        message(
          "c4m2",
          "ia",
          "Não tenho essa informação. Um atendente da equipe vai responder.",
          60 * 30 - 1,
          "pt"
        ),
      ],
    },
    {
      ...BASE,
      id: "demo-c5",
      whatsapp_phone: "5500900000005",
      status: "resolvida",
      idioma_detectado: "pt",
      atendimento: "ia",
      passeio_sugerido: DEMO_TOURS[3],
      created_at: ago(60 * 24 * 9),
      updated_at: ago(60 * 24 * 4),
      messages: [
        message(
          "c5m1",
          "turista",
          "A trilha longa é boa para quem tem 14 anos?",
          60 * 24 * 4 + 10,
          "pt"
        ),
        message(
          "c5m2",
          "ia",
          "Sim, desde que a criança tenha bom preparo físico: são 90 minutos de caminhada na areia.",
          60 * 24 * 4 + 9,
          "pt"
        ),
        message(
          "c5m3",
          "atendente",
          "Oi! Confirmei a vaga para sábado. Qualquer dúvida é só chamar.",
          60 * 24 * 4,
          "pt"
        ),
      ],
    },
  ];
}
