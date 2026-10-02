import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { BookingCalendar } from "../features/tour-booking/components/BookingCalendar";
import { DayBookingsList } from "../features/tour-booking/components/DayBookingsList";
import { NewBookingPanel } from "../features/tour-booking/components/NewBookingPanel";
import { OccupancyBar } from "../features/tour-booking/components/OccupancyBar";
import { ChevronLeftIcon } from "../components/icons";
import { createBooking, getDayBookings, getTourAgenda } from "../lib/api";
import type { Booking, DayOccupancy } from "../types";

function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function currentYearMonth(): string {
  return todayIso().slice(0, 7);
}

type AgendaState =
  { status: "loading" } | { status: "error" } | { status: "ready"; days: DayOccupancy[] };
type BookingsState =
  { status: "loading" } | { status: "error" } | { status: "ready"; bookings: Booking[] };

export function TourBookingPage() {
  const { id } = useParams<{ id: string }>();
  const [yearMonth, setYearMonth] = useState(currentYearMonth());
  const [selectedDate, setSelectedDate] = useState(todayIso());
  const [agenda, setAgenda] = useState<AgendaState>({ status: "loading" });
  const [dayBookings, setDayBookings] = useState<BookingsState>({ status: "loading" });
  // A primeira busca (mês atual) sempre inclui hoje; guardamos esse dia à parte pra "vagas de
  // hoje" não depender de qual mês o atendente está navegando no calendário agora.
  const [today, setToday] = useState<DayOccupancy | null>(null);

  useEffect(() => {
    if (!id) return;
    let active = true;
    setAgenda({ status: "loading" });
    getTourAgenda(id, yearMonth).then((days) => {
      if (!active) return;
      setAgenda(days === null ? { status: "error" } : { status: "ready", days });
      const todayDay = days?.find((day) => day.data === todayIso());
      if (todayDay) setToday(todayDay);
    });
    return () => {
      active = false;
    };
  }, [id, yearMonth]);

  useEffect(() => {
    if (!id) return;
    let active = true;
    setDayBookings({ status: "loading" });
    getDayBookings(id, selectedDate).then((bookings) => {
      if (active) {
        setDayBookings(bookings === null ? { status: "error" } : { status: "ready", bookings });
      }
    });
    return () => {
      active = false;
    };
  }, [id, selectedDate]);

  async function handleCreateBooking(payload: Parameters<typeof createBooking>[1]) {
    if (!id) return { ok: false, message: "passeio não encontrado" };
    const result = await createBooking(id, payload);
    if (!result.ok) return { ok: false, message: result.message };

    setDayBookings((current) =>
      current.status === "ready"
        ? { status: "ready", bookings: [...current.bookings, result.data] }
        : current
    );
    setAgenda((current) =>
      current.status === "ready"
        ? {
            status: "ready",
            days: current.days.map((day) =>
              day.data === payload.data ? { ...day, ocupadas: result.data.ocupadas } : day
            ),
          }
        : current
    );
    if (payload.data === todayIso()) {
      setToday((current) => (current ? { ...current, ocupadas: result.data.ocupadas } : current));
    }
    return { ok: true };
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-8">
      <Link
        to="/passeios"
        className="flex w-fit items-center gap-1 text-sm font-semibold text-link hover:underline"
      >
        <ChevronLeftIcon />
        Passeios
      </Link>

      <h1 className="mt-3 font-display text-2xl font-semibold text-primary">
        Agendamentos do passeio
      </h1>

      <section aria-labelledby="today-occupancy-title" className="mt-6">
        <h2
          id="today-occupancy-title"
          className="text-xs font-semibold uppercase tracking-wide text-secondary"
        >
          Vagas de hoje
        </h2>
        {today && (
          <div className="mt-2 max-w-sm">
            <OccupancyBar ocupadas={today.ocupadas} capacidade={today.capacidade} />
          </div>
        )}
        {!today && agenda.status === "error" && (
          <p role="alert" className="mt-2 text-sm text-status-error">
            Não foi possível carregar as vagas de hoje.
          </p>
        )}
        {!today && agenda.status !== "error" && (
          <p className="mt-2 text-sm text-muted">Carregando…</p>
        )}
      </section>

      <div className="mt-8 grid gap-8 md:grid-cols-2">
        <div className="flex flex-col gap-8">
          {agenda.status === "loading" && <p className="text-muted">Carregando calendário…</p>}
          {agenda.status === "error" && (
            <p role="alert" className="text-sm text-status-error">
              Não foi possível carregar o calendário deste passeio.
            </p>
          )}
          {agenda.status === "ready" && (
            <BookingCalendar
              yearMonth={yearMonth}
              days={agenda.days}
              selectedDate={selectedDate}
              onSelectDate={setSelectedDate}
              onChangeMonth={setYearMonth}
            />
          )}

          {dayBookings.status === "loading" && (
            <p className="text-muted">Carregando agendamentos…</p>
          )}
          {dayBookings.status === "error" && (
            <p role="alert" className="text-sm text-status-error">
              Não foi possível carregar os agendamentos deste dia.
            </p>
          )}
          {dayBookings.status === "ready" && (
            <DayBookingsList data={selectedDate} bookings={dayBookings.bookings} />
          )}
        </div>

        <NewBookingPanel data={selectedDate} onSubmit={handleCreateBooking} />
      </div>
    </main>
  );
}
