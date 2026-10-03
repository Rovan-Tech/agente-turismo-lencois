/** Textos que o servidor manda ao turista quando uma pessoa assume ou devolve a conversa. */

const LANGUAGES = ["pt", "en", "es"] as const;

const ANNOUNCEMENT = {
  pt: [
    "Olá! Agora quem está falando com você é uma pessoa da nossa equipe",
    "Pode continuar por aqui.",
  ],
  en: ["Hello! You are now talking to a person from our team", "You can keep writing here."],
  es: [
    "¡Hola! Ahora te atiende una persona de nuestro equipo",
    "Puedes seguir escribiendo por aquí.",
  ],
} as const;

const GIVE_BACK = {
  pt: "A partir de agora o nosso assistente virtual volta a ajudar você. Se quiser falar com uma pessoa, é só pedir.",
  en: "From now on our virtual assistant will help you again. If you want to talk to a person, just ask.",
  es: "A partir de ahora nuestro asistente virtual vuelve a ayudarte. Si quieres hablar con una persona, solo pídelo.",
} as const;

export const FOLLOW_UP: Record<string, string> = {
  pt: "Perfeito, obrigado! Vou conversar aqui com o grupo e já volto.",
  en: "Perfect, thank you! I'll talk it over with my group and get back to you.",
  es: "Perfecto, ¡gracias! Lo hablo con mi grupo y vuelvo enseguida.",
};

/** Tradução de demonstração: um texto fixo por idioma, não uma IA traduzindo o que foi digitado. */
export const TRANSLATION_DEMO: Record<string, string> = {
  pt: "Esta é uma tradução de demonstração. Na versão real, a IA traduz o texto digitado.",
  en: "This is a demo translation. In the real product, the AI translates what was typed.",
  es: "Esta es una traducción de demostración. En el producto real, la IA traduce lo escrito.",
};

export const WINDOW_CLOSED =
  "A última mensagem do turista tem mais de 24 horas: o WhatsApp só permite responder dentro desse prazo. Espere o turista escrever de novo.";

function languagesOf(language: string | null): readonly (typeof LANGUAGES)[number][] {
  return language === "pt" || language === "en" || language === "es" ? [language] : LANGUAGES;
}

export function announcementText(language: string | null, firstName: string | null): string {
  const suffix = firstName ? `: ${firstName}` : "";
  return languagesOf(language)
    .map((code) => `${ANNOUNCEMENT[code][0]}${suffix}. ${ANNOUNCEMENT[code][1]}`)
    .join("\n");
}

export function giveBackText(language: string | null): string {
  return languagesOf(language)
    .map((code) => GIVE_BACK[code])
    .join("\n");
}
