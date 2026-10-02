import { expect, test, type Page } from "@playwright/test";

import { bookThreePeopleWithBoleto } from "./booking";

interface FakeBooking {
  id: string;
  tour_id: string;
  data: string;
  pessoas: number;
  forma_pagamento: string;
  status_pagamento: string;
  telefone: string | null;
  created_at: string;
}

const TOUR_ID = "passeio-teste";
const CAPACIDADE = 10;

function daysInMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

/** Estado mutável compartilhado pelos handlers de rota de um teste. */
interface BookingFixture {
  bookings: FakeBooking[];
  nextId: number;
}

async function mockToursList(page: Page) {
  await page.route("**/api/tours**", async (route) => {
    await route.fulfill({
      json: [
        {
          id: TOUR_ID,
          nome: "Passeio de teste",
          acessivel_idosos: false,
          acessivel_cadeirantes: false,
          acessivel_criancas_pequenas: false,
          descricao: "Passeio criado só para este teste E2E de agendamento.",
          dificuldade_fisica: "alta",
          caminhada_areia_minutos: 60,
          duracao_horas: 4,
          faixa_etaria_recomendada: "acima de 12 anos",
          preco_reais: 100,
          ativo: true,
        },
      ],
    });
  });
}

async function mockAgenda(page: Page, fixture: BookingFixture) {
  await page.route(`**/api/tours/${TOUR_ID}/agenda**`, async (route) => {
    const mes = new URL(route.request().url()).searchParams.get("mes")!;
    const [year, month] = mes.split("-").map(Number);
    const total = daysInMonth(year, month);
    const days = Array.from({ length: total }, (_, index) => {
      const data = `${mes}-${String(index + 1).padStart(2, "0")}`;
      const ocupadas = fixture.bookings
        .filter((booking) => booking.data === data)
        .reduce((sum, booking) => sum + booking.pessoas, 0);
      return { data, capacidade: CAPACIDADE, ocupadas };
    });
    await route.fulfill({ json: days });
  });
}

async function mockDayBookings(page: Page, fixture: BookingFixture) {
  await page.route(`**/api/tours/${TOUR_ID}/agendamentos?data=*`, async (route) => {
    const data = new URL(route.request().url()).searchParams.get("data");
    await route.fulfill({ json: fixture.bookings.filter((booking) => booking.data === data) });
  });
}

async function mockCreateBooking(page: Page, fixture: BookingFixture) {
  await page.route(`**/api/tours/${TOUR_ID}/agendamentos`, async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    const payload = route.request().postDataJSON();
    const occupied = fixture.bookings
      .filter((booking) => booking.data === payload.data)
      .reduce((sum, booking) => sum + booking.pessoas, 0);
    if (occupied + payload.pessoas > CAPACIDADE) {
      await route.fulfill({ status: 409, json: { detail: "não há vagas suficientes nesse dia" } });
      return;
    }
    const created: FakeBooking = {
      id: `booking-${fixture.nextId++}`,
      tour_id: TOUR_ID,
      data: payload.data,
      pessoas: payload.pessoas,
      forma_pagamento: payload.forma_pagamento,
      status_pagamento: "pago",
      telefone: payload.telefone ?? null,
      created_at: new Date().toISOString(),
    };
    fixture.bookings = [...fixture.bookings, created];
    await route.fulfill({
      status: 201,
      json: { ...created, capacidade: CAPACIDADE, ocupadas: occupied + payload.pessoas },
    });
  });
}

async function mockBookingBackend(page: Page, fixture: BookingFixture) {
  await page.clock.setFixedTime(new Date("2026-09-28T09:00:00"));
  await mockToursList(page);
  await mockAgenda(page, fixture);
  await mockDayBookings(page, fixture);
  await mockCreateBooking(page, fixture);
}

/** Abre a página do passeio (sem passar pelo catálogo) já com o dia de hoje sem agendamentos. */
async function openEmptyBookingPage(page: Page, fixture: BookingFixture) {
  await mockBookingBackend(page, fixture);
  await page.goto(`/passeios/${TOUR_ID}`);
  await expect(page.getByText("Nenhum agendamento pago para este dia ainda.")).toBeVisible();
}

test("books a tour, decrements the seats instantly and lists it as paid", async ({ page }) => {
  const fixture: BookingFixture = { bookings: [], nextId: 1 };
  await mockBookingBackend(page, fixture);

  await page.goto("/passeios");
  await page.getByRole("link", { name: "Agendamentos" }).click();

  await expect(page.getByRole("heading", { name: "Agendamentos do passeio" })).toBeVisible();
  await expect(page.getByText(`${CAPACIDADE} vagas`)).toBeVisible();
  await expect(page.getByText("Nenhum agendamento pago para este dia ainda.")).toBeVisible();

  await bookThreePeopleWithBoleto(page);

  await expect(page.getByText(`${CAPACIDADE - 3} vagas`)).toBeVisible();
  await expect(page.getByText("Telefone não informado")).toBeVisible();
  await expect(page.getByText("3 pessoas · Boleto")).toBeVisible();
  await expect(page.getByText("Pago")).toBeVisible();
});

test("switching the calendar day shows that day's own bookings and occupancy", async ({ page }) => {
  const fixture: BookingFixture = {
    nextId: 1,
    bookings: [
      {
        id: "booking-other-day",
        tour_id: TOUR_ID,
        data: "2026-09-05",
        pessoas: 4,
        forma_pagamento: "pix",
        status_pagamento: "pago",
        telefone: null,
        created_at: new Date().toISOString(),
      },
    ],
  };
  await openEmptyBookingPage(page, fixture);

  await page.getByRole("button", { name: "Dia 5:", exact: false }).click();

  await expect(page.getByText("4 pessoas · Pix")).toBeVisible();
});

test("books a tour using only the keyboard to pick the payment method and confirm", async ({
  page,
}) => {
  const fixture: BookingFixture = { bookings: [], nextId: 1 };
  await openEmptyBookingPage(page, fixture);

  await page.getByRole("radio", { name: "Pix" }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("radio", { name: "Boleto" })).toBeChecked();

  await page.getByRole("button", { name: "Simular pagamento aprovado" }).focus();
  await page.keyboard.press("Enter");

  await expect(page.getByText("1 pessoa · Boleto")).toBeVisible();
  await expect(page.getByText("Pago")).toBeVisible();
});
