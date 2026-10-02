import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/** Acessibilidade (WCAG 2.2 AA): a tela não pode ter nenhuma violação. */
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

export async function expectNoViolations(page: Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  const summary = violations.map((violation) => ({
    rule: violation.id,
    impact: violation.impact,
    help: violation.help,
    targets: violation.nodes.map((node) => node.target.join(" ")),
  }));
  expect(summary).toEqual([]);
}

/** Troca para o tema `theme` pelo botão da tela (o claro já é o padrão). */
export async function switchTheme(page: Page, theme: "light" | "dark") {
  if (theme === "light") return;
  await page.getByRole("button", { name: "Usar modo escuro" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
}
