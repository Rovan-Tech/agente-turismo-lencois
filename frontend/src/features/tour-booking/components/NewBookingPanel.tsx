import { useState } from "react";

import type { BookingCreateInput, PaymentMethod } from "../../../types";
import { paymentMethodLabel } from "../format";

const PAYMENT_METHODS: PaymentMethod[] = ["pix", "boleto", "cartao"];
const MIN_PEOPLE = 1;
const MAX_PEOPLE = 50;

interface NewBookingPanelProps {
  data: string;
  onSubmit: (payload: BookingCreateInput) => Promise<{ ok: boolean; message?: string }>;
}

/** Visual estático da simulação de pagamento — nunca um campo de número de cartão, real ou fake. */
function PaymentPreview({ method }: { method: PaymentMethod }) {
  if (method === "pix") {
    return (
      <p className="rounded-md border border-dashed border-subtle bg-subtle p-3 font-mono text-xs text-secondary">
        00020126 QR CODE PIX SIMULADO 5204000053039865802BR
      </p>
    );
  }
  if (method === "boleto") {
    return (
      <p className="rounded-md border border-dashed border-subtle bg-subtle p-3 font-mono text-xs tracking-widest text-secondary">
        ||| | ||| || | ||||| | || BOLETO SIMULADO | || ||| | |||
      </p>
    );
  }
  return (
    <p className="rounded-md border border-dashed border-subtle bg-subtle p-3 text-xs text-secondary">
      Cartão de teste — nenhum dado de cartão é coletado nesta simulação.
    </p>
  );
}

/** Painel de novo agendamento: pessoas, forma de pagamento simulada e "simular pagamento aprovado". */
export function NewBookingPanel({ data, onSubmit }: NewBookingPanelProps) {
  const [pessoas, setPessoas] = useState(1);
  const [formaPagamento, setFormaPagamento] = useState<PaymentMethod>("pix");
  const [telefone, setTelefone] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setStatus("loading");
    // O atendente digita no formato que quiser ("(98) 99999-8888"); só dígitos (e um `+` inicial
    // de DDI) vão pro backend, que só aceita esse formato.
    const normalizedPhone = telefone.replace(/[^\d+]/g, "");
    const payload: BookingCreateInput = {
      data,
      pessoas,
      forma_pagamento: formaPagamento,
      ...(normalizedPhone ? { telefone: normalizedPhone } : {}),
    };
    const result = await onSubmit(payload);
    if (!result.ok) {
      setStatus("error");
      setErrorMessage(result.message ?? "não foi possível criar o agendamento");
      return;
    }
    setStatus("idle");
    setPessoas(1);
    setTelefone("");
  }

  return (
    <form
      onSubmit={handleSubmit}
      aria-labelledby="new-booking-title"
      className="flex flex-col gap-4 rounded-md border border-subtle bg-surface p-4"
    >
      <div className="flex items-center justify-between">
        <h2 id="new-booking-title" className="font-display font-semibold text-primary">
          Novo agendamento
        </h2>
        <span className="rounded-full bg-status-warning px-2 py-1 text-xs font-medium text-status-warning">
          Simulação — nenhum pagamento real é processado
        </span>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="booking-pessoas" className="text-sm text-secondary">
          Pessoas
        </label>
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="Diminuir número de pessoas"
            onClick={() => setPessoas((current) => Math.max(MIN_PEOPLE, current - 1))}
            className="rounded-md border border-subtle px-3 py-1 text-primary hover:bg-neutral-subtle"
          >
            −
          </button>
          <input
            id="booking-pessoas"
            type="number"
            min={MIN_PEOPLE}
            max={MAX_PEOPLE}
            value={pessoas}
            onChange={(event) => setPessoas(Number(event.target.value))}
            className="w-16 rounded-md border border-subtle p-1 text-center text-primary"
          />
          <button
            type="button"
            aria-label="Aumentar número de pessoas"
            onClick={() => setPessoas((current) => Math.min(MAX_PEOPLE, current + 1))}
            className="rounded-md border border-subtle px-3 py-1 text-primary hover:bg-neutral-subtle"
          >
            +
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="booking-telefone" className="text-sm text-secondary">
          Telefone (opcional)
        </label>
        <input
          id="booking-telefone"
          type="tel"
          inputMode="tel"
          placeholder="(98) 99999-8888"
          value={telefone}
          onChange={(event) => setTelefone(event.target.value)}
          className="rounded-md border border-subtle p-2 text-primary"
        />
      </div>

      <fieldset className="flex flex-col gap-1">
        <legend className="text-sm text-secondary">Forma de pagamento</legend>
        <div className="flex gap-2">
          {PAYMENT_METHODS.map((method) => (
            <label key={method} className="flex-1">
              <input
                type="radio"
                name="forma-pagamento"
                value={method}
                checked={formaPagamento === method}
                onChange={() => setFormaPagamento(method)}
                className="peer sr-only"
              />
              <span className="block cursor-pointer rounded-md border border-subtle px-3 py-2 text-center text-sm font-medium text-secondary peer-checked:border-attention peer-checked:bg-accent-subtle peer-checked:text-accent-subtle peer-focus-visible:ring-2 peer-focus-visible:ring-focus">
                {paymentMethodLabel(method)}
              </span>
            </label>
          ))}
        </div>
      </fieldset>
      <PaymentPreview method={formaPagamento} />

      {status === "error" && (
        <p role="alert" className="text-sm text-status-error">
          {errorMessage}
        </p>
      )}

      <button
        type="submit"
        disabled={status === "loading"}
        className="rounded-md bg-action px-4 py-2 font-medium text-on-action hover:bg-action-hover disabled:bg-subtle disabled:text-muted"
      >
        {status === "loading" ? "Simulando pagamento…" : "Simular pagamento aprovado"}
      </button>
    </form>
  );
}
