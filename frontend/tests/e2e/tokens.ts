import type { Page } from "@playwright/test";

/** Cor que um token semântico tem NO tema atual (a sonda resolve a cadeia de `var()`). */
export const tokenColor = (page: Page, token: string) =>
  page.evaluate((name) => {
    const probe = document.createElement("div");
    probe.style.backgroundColor = `var(${name})`;
    document.body.append(probe);
    const color = getComputedStyle(probe).backgroundColor;
    probe.remove();
    return color;
  }, token);
