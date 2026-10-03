import type { Booking } from "../../../types";
import { formatDateLabel, paymentMethodLabel } from "../format";

/** Agendamentos pagos de um dia: telefone, pessoas e forma de pagamento (atendente autenticado). */
export function DayBookingsList({
  data,
  bookings,
}: Readonly<{ data: string; bookings: Booking[] }>) {
  return (
    <section aria-labelledby="day-bookings-title" className="flex flex-col gap-2">
      <h2 id="day-bookings-title" className="font-display font-semibold text-primary">
        Agendamentos de {formatDateLabel(data)}
      </h2>
      {bookings.length === 0 ? (
        <p className="text-sm text-muted">Nenhum agendamento pago para este dia ainda.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {bookings.map((booking) => (
            <li
              key={booking.id}
              className="flex items-center justify-between gap-3 rounded-md border border-subtle bg-surface p-3"
            >
              <div className="flex flex-col">
                <span className="text-sm font-medium text-primary">
                  {booking.telefone ?? "Telefone não informado"}
                </span>
                <span className="text-xs text-muted">
                  {booking.pessoas === 1 ? "1 pessoa" : `${booking.pessoas} pessoas`} ·{" "}
                  {paymentMethodLabel(booking.forma_pagamento)}
                </span>
              </div>
              <span className="rounded-full bg-status-success px-2 py-1 text-xs font-medium text-status-success">
                Pago
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
