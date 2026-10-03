import type { DayOccupancy } from "../../../types";
import {
  dayOfMonth,
  formatMonthLabel,
  occupancyBadgeClass,
  occupancyLevel,
  remainingSeatsLabel,
} from "../format";

interface BookingCalendarProps {
  yearMonth: string;
  days: DayOccupancy[];
  selectedDate: string;
  onSelectDate: (data: string) => void;
  onChangeMonth: (yearMonth: string) => void;
}

function shiftMonth(yearMonth: string, delta: number): string {
  const [year, month] = yearMonth.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1 + delta, 1));
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
}

/** Calendário do mês com a ocupação de cada dia; clicar num dia troca o dia selecionado. */
export function BookingCalendar({
  yearMonth,
  days,
  selectedDate,
  onSelectDate,
  onChangeMonth,
}: Readonly<BookingCalendarProps>) {
  return (
    <section aria-labelledby="booking-calendar-title" className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <button
          type="button"
          aria-label="Mês anterior"
          onClick={() => onChangeMonth(shiftMonth(yearMonth, -1))}
          className="rounded-md px-2 py-1 text-sm text-secondary hover:bg-neutral-subtle"
        >
          ←
        </button>
        <h2 id="booking-calendar-title" className="font-display font-semibold text-primary">
          {formatMonthLabel(yearMonth)}
        </h2>
        <button
          type="button"
          aria-label="Próximo mês"
          onClick={() => onChangeMonth(shiftMonth(yearMonth, 1))}
          className="rounded-md px-2 py-1 text-sm text-secondary hover:bg-neutral-subtle"
        >
          →
        </button>
      </div>
      <div className="grid grid-cols-7 gap-1">
        {days.map((day) => {
          const level = occupancyLevel(day.ocupadas, day.capacidade);
          const isSelected = day.data === selectedDate;
          return (
            <button
              key={day.data}
              type="button"
              onClick={() => onSelectDate(day.data)}
              aria-pressed={isSelected}
              aria-label={`Dia ${dayOfMonth(day.data)}: ${remainingSeatsLabel(day.ocupadas, day.capacidade)}`}
              className={`flex flex-col items-center rounded-md border p-2 text-xs font-medium ${occupancyBadgeClass(level)} ${
                isSelected ? "border-attention ring-2 ring-focus" : "border-transparent"
              }`}
            >
              {dayOfMonth(day.data)}
            </button>
          );
        })}
      </div>
    </section>
  );
}
