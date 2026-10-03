import { expect, test } from "@playwright/test";

interface FakeTour {
  id: string;
  ativo: boolean;
  preco_reais: number;
  duracao_horas: number;
  [key: string]: unknown;
}

test("creates and edits a tour through the catalog page", async ({ page }) => {
  let tours: FakeTour[] = [];

  await page.route("**/api/tours**", async (route) => {
    const request = route.request();
    const method = request.method();

    if (method === "GET") {
      await route.fulfill({ json: tours });
      return;
    }

    if (method === "POST") {
      const created = { ativo: true, ...request.postDataJSON() } as FakeTour;
      tours = [...tours, created];
      await route.fulfill({ status: 201, json: created });
      return;
    }

    if (method === "PUT") {
      const id = new URL(request.url()).pathname.split("/").pop();
      tours = tours.map((tour) =>
        tour.id === id ? { ...tour, ...request.postDataJSON(), id } : tour
      );
      await route.fulfill({ json: tours.find((tour) => tour.id === id) });
      return;
    }

    await route.continue();
  });

  await page.goto("/passeios");

  await expect(page.getByRole("heading", { name: "Passeios", exact: true })).toBeVisible();
  await expect(page.getByText("Nenhum passeio cadastrado.")).toBeVisible();

  await page.getByRole("button", { name: "Novo passeio" }).click();
  await page.getByLabel("Id", { exact: true }).fill("passeio-teste");
  await page.getByLabel("Nome").fill("Passeio de teste");
  await page.getByLabel("Descrição").fill("Descrição do passeio de teste");
  await page.getByLabel("Faixa etária recomendada").fill("todas as idades");
  await page.getByRole("button", { name: "Salvar" }).click();

  await expect(page.getByText("Passeio de teste")).toBeVisible();
  await expect(page.getByText("Ativo")).toBeVisible();

  await page.getByRole("button", { name: "Editar" }).click();
  await page.getByLabel("Preço (R$)").fill("199.9");
  await page.getByRole("button", { name: "Salvar" }).click();

  await expect(page.getByText(/R\$\s*199,90/)).toBeVisible();
});
