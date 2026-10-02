import { IS_DEMO } from "../lib/demo";
import type { Me } from "../types";
import { UserIcon } from "./icons";

/** O Cloudflare Access encerra a sessão neste caminho da própria origem do painel. */
export const LOGOUT_URL = "/cdn-cgi/access/logout";

const LINK = "font-semibold text-link hover:underline";

/**
 * Quem está logado e o botão para sair. `me` só existe atrás do login (Cloudflare Access): sem ele
 * (desenvolvimento com o token fixo, ou a consulta falhou) fica o nome genérico e nenhum "Sair",
 * que levaria a um endereço que não existe fora do Access.
 */
export function UserMenu({ me }: { me: Me | null }) {
  return (
    <span className="flex items-center gap-3">
      <span className="flex items-center gap-2 font-medium text-primary">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-subtle text-neutral-subtle">
          <UserIcon />
        </span>
        {me?.nome ?? "Equipe"}
      </span>
      {me && !IS_DEMO && (
        <a href={LOGOUT_URL} className={LINK}>
          Sair
        </a>
      )}
    </span>
  );
}

/** Versão do celular: só o "Sair" (o nome e o avatar não cabem ao lado da marca). */
export function MobileSignOut({ me }: { me: Me | null }) {
  return me && !IS_DEMO ? (
    <a href={LOGOUT_URL} className={`text-sm ${LINK}`}>
      Sair
    </a>
  ) : null;
}
