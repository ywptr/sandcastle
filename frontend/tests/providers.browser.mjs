// Optional browser harness; API fixtures, no provider calls or real credentials.
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || "playwright");
import assert from "node:assert/strict";
import fs from "node:fs";
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const origin = process.env.WORKSPACE_ORIGIN || "https://192.168.0.99:5182";
const out = process.env.WORKSPACE_SCREENSHOTS || "/tmp/sc0002-visuals";
fs.mkdirSync(out, { recursive: true });
const page = await browser.newPage({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const providers = ["openai", "anthropic", "google"].map((provider) => ({ provider, supported: true, enabled: false, has_credentials: false, config: { default_model: null } }));
const roles = ["creative_writer", "story_importer", "narrative_media_translator"].map((role) => ({ role, provider: null, model: null, selected_provider: null, selected_model: null, available: false }));
const writes = [];
let fail = false;
await page.route("**/api/**", async (route) => {
    const request = route.request(), path = new URL(request.url()).pathname;
    if (!path.startsWith("/api/")) return route.continue();
    let data;
    if (path === "/api/auth/me") data = { user_id: "ui-fixture", email: "writer@example.test", name: "Settings preview" };
    else if (path === "/api/stories") data = [];
    else if (path === "/api/styles") data = [];
    else if (path === "/api/settings/llm/providers") data = providers;
    else if (path === "/api/settings/llm/roles") { for (const role of roles) {
        const selected = role.provider ? providers.find((p) => p.provider === role.provider) : providers.find((p) => p.enabled && p.has_credentials && p.config.default_model);
        role.available = !!(selected?.enabled && selected?.has_credentials && selected?.config.default_model);
        role.selected_provider = role.available ? selected.provider : null; role.selected_model = role.available ? role.model || selected.config.default_model : null;
    } data = roles; }
    else if (path.startsWith("/api/settings/llm/providers/")) {
        const provider = providers.find((p) => path.includes(p.provider));
        if (request.method() === "PUT") {
            const body = request.postDataJSON(); writes.push(body);
            if (fail) return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Settings unavailable" }) });
            if ("enabled" in body) provider.enabled = body.enabled; if (body.config) provider.config = body.config;
            if (body.credentials) provider.has_credentials = true;
        } else if (request.method() === "DELETE") { provider.has_credentials = false; provider.enabled = false; }
        data = provider;
    } else if (path.startsWith("/api/settings/llm/roles/")) {
        const role = roles.find((r) => path.endsWith(r.role)), body = request.postDataJSON();
        Object.assign(role, { provider: body.provider, model: body.model, selected_provider: body.provider || "openai", selected_model: "test-model", available: true }); data = roles;
    } else throw Error("Unexpected fixture route");
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(data) });
});
try {
    await page.goto(origin, { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Settings", exact: true }).click();
    await page.getByRole("button", { name: "AI", exact: true }).click();
    assert.equal(await page.getByRole("radio", { name: "Sandcastle Default", exact: false }).isDisabled(), true);
    assert.equal(await page.getByRole("button", { name: "Advanced routing", exact: true }).count(), 0);
    await page.getByRole("button", { name: "My AI Providers", exact: true }).click();
    const openai = page.locator(".provider-card").filter({ has: page.getByRole("heading", { name: "OpenAI", exact: true }) });
    const secret = "invalid-browser-fixture-key";
    await openai.getByRole("button", { name: "Configure OpenAI", exact: true }).click();
    assert.equal(await openai.getByLabel("OpenAI API key", { exact: true }).getAttribute("type"), "password");
    await openai.getByLabel("Enable OpenAI", { exact: true }).check();
    await openai.getByLabel("Default model for OpenAI").fill("test-model");
    await openai.getByLabel("OpenAI API key", { exact: true }).fill(secret);
    await openai.getByRole("button", { name: "Save OpenAI", exact: true }).click();
    await openai.getByText("Personal provider saved.", { exact: false }).waitFor();
    assert.equal(await openai.getByLabel("OpenAI API key", { exact: true }).inputValue(), "");
    assert.equal(writes[0].credentials.api_key, secret);
    await openai.getByLabel("Enable OpenAI", { exact: true }).uncheck();
    await openai.getByRole("button", { name: "Save OpenAI", exact: true }).click();
    await openai.getByText("Personal provider saved.", { exact: false }).waitFor();
    assert.equal("credentials" in writes.at(-1), false);
    await openai.getByLabel("Enable OpenAI", { exact: true }).check();
    await openai.getByRole("button", { name: "Save OpenAI", exact: true }).click();
    await openai.getByText("Personal provider saved.", { exact: false }).waitFor();
    await openai.getByLabel("OpenAI API key", { exact: true }).fill("rotated-fixture-secret");
    await openai.getByRole("button", { name: "Save OpenAI", exact: true }).click();
    await openai.getByText("Personal provider saved.", { exact: false }).waitFor();
    assert.equal(writes.at(-1).credentials.api_key, "rotated-fixture-secret");
    await page.getByRole("button", { name: "General", exact: true }).click();
    await page.getByLabel("Settings detail").selectOption("difficult");
    await page.getByRole("button", { name: "AI", exact: true }).click();
    await page.getByRole("button", { name: "Advanced routing", exact: true }).click();
    for (const label of ["Creative writing", "Story import", "Production planning"]) {
        await page.getByLabel(label + " provider", { exact: true }).selectOption("openai");
        await page.getByRole("button", { name: `Save ${label.toLowerCase()} preference`, exact: true }).click();
        await page.locator("form").filter({ has: page.getByLabel(label + " provider", { exact: true }) }).getByText("Routing preference saved.", { exact: true }).waitFor();
    }
    await page.getByLabel("Story import provider", { exact: true }).selectOption("");
    await page.getByRole("button", { name: "Save story import preference", exact: true }).click();
    assert.equal(await page.getByLabel("Story import provider", { exact: true }).inputValue(), "");
    await page.screenshot({ path: out + "/ai-routing-desktop.png", fullPage: true });
    await page.getByRole("button", { name: "My AI Providers", exact: true }).click();
    await openai.getByRole("button", { name: "Disable OpenAI", exact: true }).click();
    await openai.getByText("Routing affected:", { exact: false }).waitFor();
    await openai.getByRole("button", { name: "Enable OpenAI", exact: true }).click();
    await openai.getByRole("button", { name: "Configure OpenAI", exact: true }).click();
    assert.equal(await page.evaluate((s) => document.body.textContent.includes(s) || JSON.stringify(localStorage).includes(s) || JSON.stringify(sessionStorage).includes(s), secret), false);
    await page.screenshot({ path: out + "/ai-providers-desktop.png", fullPage: true });
    for (const width of [390, 320]) {
        await page.setViewportSize({ width, height: 900 });
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
        if (width === 390) await page.screenshot({ path: out + "/ai-providers-mobile.png", fullPage: true });
    }
    fail = true;
    await openai.getByLabel("OpenAI API key", { exact: true }).fill(secret);
    await openai.getByRole("button", { name: "Save OpenAI", exact: true }).click();
    await openai.getByRole("alert").waitFor();
    assert.equal(await openai.getByLabel("OpenAI API key", { exact: true }).inputValue(), "");
    fail = false;
    await openai.getByRole("button", { name: "Remove OpenAI credential", exact: true }).click();
    assert.equal(providers[0].has_credentials, true);
    await openai.getByRole("button", { name: "Confirm removal for OpenAI" }).click();
    await openai.getByText("Credential removed.", { exact: false }).waitFor();
    assert.equal(providers[0].has_credentials, false);
    await openai.getByText("Not connected", { exact: true }).waitFor();
    await page.getByRole("button", { name: "General", exact: true }).click();
    await page.getByLabel("Settings detail").selectOption("normal");
    await page.getByRole("button", { name: "AI", exact: true }).click();
    assert.equal(await page.getByRole("button", { name: "Advanced routing", exact: true }).count(), 0);
    await page.getByRole("heading", { name: "Current task selection", exact: true }).waitFor();
    await page.getByRole("button", { name: "General", exact: true }).click();
    await page.getByLabel("Settings detail").selectOption("impossible");
    await page.getByRole("button", { name: "AI", exact: true }).click();
    assert.equal(await page.getByRole("radio", { name: "Sandcastle Default", exact: false }).isDisabled(), true);
    await page.screenshot({ path: out + "/ai-mode-mobile.png", fullPage: true });
    await page.getByRole("button", { name: "Advanced routing", exact: true }).click();
    await page.getByLabel("Creative writing model override", { exact: true }).waitFor();
    assert.equal(await page.getByLabel("Creative writing model override", { exact: true }).isVisible(), true);
    await page.getByRole("button", { name: "Account", exact: true }).click();
    await page.getByText("Your identity and sign-in are managed by IS.", { exact: false }).waitFor();
    await page.getByRole("button", { name: "Back to studio", exact: true }).click();
    await page.getByRole("heading", { name: "What do you want to create?" }).waitFor();
    assert.deepEqual(errors, []);
    console.log("PASS: provider settings save/omit/enable/disable/removal, role preferences, error input clearing, no browser storage, mobile overflow, studio return. Fixture-only, no live provider calls.");
} finally { await browser.close(); }
