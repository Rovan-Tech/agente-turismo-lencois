import { expect, type Page } from "@playwright/test";

/** Agenda 3 pessoas pagando no boleto, a partir da página do passeio já aberta. */
export async function bookThreePeopleWithBoleto(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Aumentar número de pessoas" }).click();
  await page.getByRole("button", { name: "Aumentar número de pessoas" }).click();
  // O rádio é visualmente escondido (`sr-only`) atrás do rótulo estilizado que o cobre por inteiro,
  // então o clique do mouse vai no rótulo (o teste "books a tour using only the keyboard…" cobre o
  // teclado).
  await page
    .locator("label")
    .filter({ has: page.getByRole("radio", { name: "Boleto" }) })
    .click();
  await expect(page.getByRole("radio", { name: "Boleto" })).toBeChecked();
  await page.getByRole("button", { name: "Simular pagamento aprovado" }).click();
}
