import type { ButtonHTMLAttributes } from "react";

/** Botão de ação principal (tokens do design system); desabilitado, cai para o tom neutro. */
export function PrimaryButton({
  className = "",
  ...props
}: Readonly<ButtonHTMLAttributes<HTMLButtonElement>>) {
  return (
    <button
      type="button"
      className={`rounded-md bg-action px-4 py-2 text-sm font-medium text-on-action hover:bg-action-hover active:bg-action-active disabled:bg-subtle disabled:text-muted ${className}`}
      {...props}
    />
  );
}
