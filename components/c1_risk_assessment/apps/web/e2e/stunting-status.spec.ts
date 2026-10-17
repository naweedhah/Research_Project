import { expect, test } from "@playwright/test";

test.skip(!process.env.PLAYWRIGHT_BASE_URL, "Point PLAYWRIGHT_BASE_URL at this workspace web server before running.");

test("Stunting-positive visit displays Stunting while acute status stays Normal", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("doctor@demo.local");
  await page.getByLabel("Password").fill("doctor123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.goto("/children/9cb0d03e-f8e0-4fd2-ad1c-00642b86064d");

  const status = page.getByTestId("measure-status");
  await expect(status).toContainText("Stunting", { timeout: 20000 });
  await expect(status).not.toContainText("Normal");

  const assessment = page.locator("#ai-assessment");
  await expect(assessment).toContainText("Stunting");
  await expect(assessment.getByText("Normal", { exact: true })).toHaveCount(0);

  await expect(page.getByTestId("measure-age")).toContainText("4 mo");
  await expect(page.getByTestId("measure-weight")).toContainText("10.5");
  await expect(page.getByTestId("measure-height")).toContainText("82.0");

  await page.goto("/children/9cb0d03e-f8e0-4fd2-ad1c-00642b86064d?tab=ai");
  await expect(page.getByText("Acute malnutrition status", { exact: false })).toBeVisible();
  await expect(page.getByText("Acute status represents the model's Normal/MAM/SAM acute-malnutrition output")).toBeVisible();
  const details = page.getByText("Acute malnutrition status").locator("xpath=..");
  await expect(details).toContainText("Normal");
  await expect(page.getByText("Predicted malnutrition type").locator("xpath=..").last()).toContainText("Stunting");
});
