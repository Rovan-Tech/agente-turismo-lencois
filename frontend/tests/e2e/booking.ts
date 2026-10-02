import type { Page } from "@playwright/test";

/** Agenda 3 pessoas pagando no boleto, a partir da página do passeio já aberta. */
export async function bookThreePeopleWithBoleto(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Aumentar número de pessoas" }).click();
  await page.getByRole("button", { name: "Aumentar número de pessoas" }).click();
  // `force`: o rádio é visualmente escondido (`sr-only`) atrás do rótulo estilizado que o cobre
  // por inteiro — o mesmo padrão que "books a tour using only the keyboard…" valida pelo teclado,
  // sem o hit-test do mouse.
  await page.getByRole("radio", { name: "Boleto" }).check({ force: true });
  await page.getByRole("button", { name: "Simular pagamento aprovado" }).click();
}
