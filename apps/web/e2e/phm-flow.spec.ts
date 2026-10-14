import { expect, test } from "@playwright/test";

test("Doctor can open the demonstration child", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("doctor@demo.local");
  await page.getByLabel("Password").fill("doctor123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Priority actions")).toBeVisible({ timeout: 15000 });
  await page.getByRole("link", { name: "Children" }).click();
  await page.getByPlaceholder("Search child ID").fill("C-1042");
  await expect(page.getByText("C-1042")).toBeVisible();
});
