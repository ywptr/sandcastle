// B1 shell acceptance. All authenticated data/writes are browser fixtures, never real generation.
import assert from "node:assert/strict";
import fs from "node:fs";
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || "playwright");
const origin = process.env.WORKSPACE_ORIGIN || "https://192.168.0.99:5182";
const out = process.env.WORKSPACE_SCREENSHOTS || "/tmp/sandcastle-b1-visuals";
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const errors = [], unexpected = [], mutations = [], measurements = [];
const styles = JSON.parse(fs.readFileSync(new URL("../../backend/app/creative_direction/styles.json", import.meta.url)));
const story = { story_id: "s1", title: "The Cartographer’s Lantern", premise: "An apprentice maps a city that rearranges itself every night. One street has begun to remember her name.", objective: "Find the missing district before the final lantern fades.", language: "en", primary_genre: "fantasy", secondary_genres: ["mystery"], status: "draft" };
const scene = { scene_id: "sc1", sequence_number: 1, title: "The street that remembered", content: "Mara unfolded the map beneath the last lantern.", status: "draft" };
const config = { steps: ["scene_creation", "narrative_guidance", "canon_extraction", "canon_review", "continuity_check"].map(step_id => ({ step_id, enabled: true })), order: ["scene_creation", "narrative_guidance", "canon_extraction", "canon_review", "continuity_check"], guidance: { count: 3, recent_scene_count: 3 }, review: { require_before_media: true, review_new: true, review_conflicts: true, review_uncertain: true }, media: { aspect_ratio: "1:1", output_format: "webtoon" }, adaptation: { sensitivity_hints: [] }, references: { character_ids: null, place_ids: null, artifact_ids: [] } };
async function session(locale = "en-US", saved, hasStory = true) {
    const context = await browser.newContext({ locale, ignoreHTTPSErrors: true, viewport: { width: 1440, height: 900 } });
    if (saved) await context.addInitScript(value => { if (!localStorage.getItem("sandcastle.uiLocale")) localStorage.setItem("sandcastle.uiLocale", value); }, saved);
    const page = await context.newPage(); page.setDefaultTimeout(12000);
    page.on("pageerror", error => errors.push(error.message));
    let signedIn = true;
    await page.route("**/api/**", async route => {
        const request = route.request(), pathname = new URL(request.url()).pathname;
        if (!pathname.startsWith("/api/")) return route.continue();
        const path = pathname.slice(4);
        let data;
        if (request.method() !== "GET") mutations.push({ path, method: request.method() });
        if (path === "/auth/me") return route.fulfill({ status: signedIn ? 200 : 401, contentType: "application/json", body: JSON.stringify(signedIn ? { user_id: "shell-fixture", name: "Studio preview", email: "writer@example.test" } : { detail: "Not authenticated" }) });
        if (path === "/auth/logout") { signedIn = false; return route.fulfill({ status: 204 }); }
        if (request.method() !== "GET") { unexpected.push(request.method() + " " + path); return route.fulfill({ status: 500, json: { detail: "Unexpected fixture write" } }); }
        if (path === "/stories") data = hasStory ? [story] : [];
        else if (path === "/styles") data = styles;
        else if (path.endsWith("/characters")) data = [{ character_id: "c1", name: "Mara", description: "An apprentice cartographer.", appearance: "Dark curls.", outfit: "A blue coat.", personality: "Curious." }];
        else if (path.endsWith("/places")) data = [{ place_id: "p1", name: "The shifting market", description: "A street that moves at dawn.", appearance: "Amber lanterns.", atmosphere: "Restless." }];
        else if (path.endsWith("/canon/candidates")) data = [];
        else if (path.endsWith("/canon")) data = [{ canon_entry_id: "f1", type: "rule", key: "city.shift", value: "The city rearranges itself at dawn.", status: "approved" }];
        else if (path.endsWith("/scenes")) data = [scene];
        else if (path.endsWith("/actions") || path.endsWith("/adaptations") || path === "/universes" || path.endsWith("/references")) data = [];
        else if (path.endsWith("/creative-direction")) data = null;
        else if (path.endsWith("/workflow")) data = { story_id: "s1", difficulty: "easy", template_name: "Standard", workflow_template_id: "standard-story", template_version: 1, configuration: config, capabilities: [], step_definitions: config.steps.map(s => ({ ...s, label: s.step_id, available: true, required: s.step_id === "scene_creation", dependencies: [] })) };
        else if (path.endsWith("/guidance/profile")) data = { audience: "teen", maturity_rating: "mild", tone: null, genre: null, guidance_notes: null, average_rating: null, rating_count: 0, feedback_tags: [] };
        else if (path === "/artifacts") data = [{ artifact_id: "a1", display_name: "Lantern study", source: "external", media_type: "image" }];
        else if (path === "/settings/llm/providers") data = ["openai", "anthropic", "google"].map(provider => ({ provider, enabled: false, supported: true, has_credentials: false, config: { default_model: null } }));
        else if (path === "/settings/llm/roles") data = [];
        else if (path === "/workflows/templates") data = [{ workflow_template_id: "standard-story", version: 1, name: "Standard", description: "Guided story workflow.", configuration: config }];
        else if (path === "/workflows/difficulties") data = ["easy", "normal", "difficult", "impossible"].map(id => ({ id, label: id, capabilities: [] }));
        else { unexpected.push(path); return route.fulfill({ status: 500, json: { detail: "Unmapped fixture read" } }); }
        await route.fulfill({ contentType: "application/json", body: JSON.stringify(data) });
    });
    await page.goto(origin, { waitUntil: "networkidle" });
    return { page, context };
}
async function navigate(page, destination) {
    const mobile = page.viewportSize().width <= 950;
    if (mobile) await page.getByRole("button", { name: "Open Studio navigation", exact: true }).click();
    await page.locator(`${mobile ? ".studio-mobile-navigation" : ".studio-sidebar"} [data-destination="${destination}"]`).click();
    if (mobile) await page.getByRole("dialog", { name: "Studio navigation", exact: true }).waitFor({ state: "hidden" });
}
async function shot(page, name) {
    await page.waitForTimeout(100);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, "Document overflow: " + name);
    measurements.push({ name, ...await page.evaluate(() => { const header = document.querySelector(".studio-header").getBoundingClientRect(), sidebar = document.querySelector(".studio-sidebar").getBoundingClientRect(); return { width: innerWidth, height: innerHeight, headerHeight: header.height, sidebarWidth: sidebar.width, scrollWidth: document.documentElement.scrollWidth }; }) });
    await page.screenshot({ path: `${out}/${name}.png` });
}
try {
    // Direct existing signed-out entry and auth redirect; no sign-in completion or provider calls.
    const live = await browser.newPage({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 900 } });
    await live.goto(origin, { waitUntil: "networkidle" });
    await live.getByRole("button", { name: "Sign in through IS", exact: true }).waitFor();
    const auth = await live.request.get(origin + "/api/auth/login", { maxRedirects: 0 });
    assert([302, 307].includes(auth.status())); assert.match(auth.headers().location, /\/oauth2\/authorize\?/);
    await live.screenshot({ path: out + "/signed-out-desktop.png" }); await live.close();

    const { page, context } = await session();
    await page.keyboard.press("Tab");
    assert.equal(await page.locator(".studio-skip-link").evaluate(e => e === document.activeElement), true);
    await page.keyboard.press("Enter");
    assert.equal(await page.evaluate(() => document.activeElement.id), "studio-content");
    await navigate(page, "home"); await shot(page, "after-home-desktop");
    assert.equal(await page.locator(".studio-header").evaluate(e => Math.round(e.getBoundingClientRect().height)), 68);
    assert.equal(await page.locator(".studio-sidebar").evaluate(e => Math.round(e.getBoundingClientRect().width)), 206);
    assert.equal(await page.locator(".studio-sidebar button:disabled").count(), 6);
    for (const id of ["episodes", "templates", "export", "publish", "billing", "help"]) {
        const entry = page.locator(`.studio-sidebar [data-destination="${id}"]`);
        assert.equal(await entry.isDisabled(), true); await entry.getByText("Not available yet").waitFor();
    }
    // Home remains the existing flow, including the import and detailed paths.
    await page.getByRole("button", { name: "Import an existing story", exact: true }).click();
    await page.getByLabel("Existing story text").waitFor();
    await navigate(page, "series"); await page.locator(".story-list-item").first().click();
    await shot(page, "after-workspace-desktop");
    assert.equal(await page.locator(".story-header h1").evaluate(e => e.getBoundingClientRect().top >= 68), true, "Navigation must not leave the story title under the sticky header");
    await navigate(page, "characters"); await page.getByRole("heading", { name: /^Characters/ }).waitFor();
    await navigate(page, "world"); await page.getByRole("heading", { name: /^Canon \(/ }).waitFor();
    await navigate(page, "library"); await page.getByRole("heading", { name: "Assets & references", exact: true }).waitFor();
    await navigate(page, "settings"); await page.getByRole("heading", { name: "Settings", exact: true }).waitFor(); await shot(page, "after-settings-desktop");
    await page.getByRole("button", { name: "AI", exact: true }).click(); await page.getByRole("heading", { name: "AI", exact: true }).waitFor();
    await navigate(page, "workspace");
    const localNav = page.getByRole("navigation", { name: "Story workspace", exact: true });
    await localNav.getByRole("button", { name: /^Scenes/ }).first().click();
    await page.getByRole("button", { name: "Edit scene", exact: true }).click();
    await page.getByLabel("Scene content").fill("Unsaved scene draft survives the navigation drawer.");
    await page.setViewportSize({ width: 390, height: 844 });
    const opener = page.getByRole("button", { name: "Open Studio navigation", exact: true });
    await opener.click(); const dialog = page.getByRole("dialog", { name: "Studio navigation", exact: true }); await dialog.waitFor();
    assert.equal(await page.evaluate(() => document.body.style.overflow), "hidden");
    for (let i = 0; i < 25; i++) { await page.keyboard.press("Tab"); assert.equal(await page.evaluate(() => !!document.activeElement.closest("dialog")), true); }
    await dialog.locator("button:not(:disabled)").first().focus();
    await page.keyboard.press("Shift+Tab");
    assert.equal(await dialog.locator("button:not(:disabled)").last().evaluate(e => e === document.activeElement), true);
    await page.keyboard.press("Escape"); await dialog.waitFor({ state: "hidden" }); assert.equal(await opener.evaluate(e => e === document.activeElement), true);
    assert.equal(await page.getByLabel("Scene content").inputValue(), "Unsaved scene draft survives the navigation drawer.");
    assert.equal(await page.evaluate(() => document.body.style.overflow), "");
    await opener.click(); await page.getByRole("button", { name: "Close Studio navigation", exact: true }).click(); await dialog.waitFor({ state: "hidden" });
    await opener.click(); await page.mouse.click(380, 300); await dialog.waitFor({ state: "hidden" });
    await opener.click(); await page.setViewportSize({ width: 1440, height: 900 }); await dialog.waitFor({ state: "hidden" });
    assert.equal(await page.getByLabel("Scene content").inputValue(), "Unsaved scene draft survives the navigation drawer.");
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    await navigate(page, "home"); await shot(page, "after-home-mobile");
    assert.equal(await page.locator(".studio-header").evaluate(e => Math.round(e.getBoundingClientRect().height)), 61);
    await opener.click(); await shot(page, "after-navigation-mobile"); await page.keyboard.press("Escape");
    await navigate(page, "characters"); await page.getByRole("heading", { name: /^Characters/ }).waitFor(); await shot(page, "after-characters-mobile");
    await navigate(page, "workspace"); await shot(page, "after-workspace-mobile");
    await navigate(page, "settings"); await shot(page, "after-settings-mobile");
    await page.locator(".studio-header").getByLabel("Interface language", { exact: true }).selectOption("id");
    assert.equal(await page.locator("html").getAttribute("lang"), "id"); assert.equal(story.language, "en");
    await shot(page, "after-settings-id-mobile");
    await page.reload({ waitUntil: "networkidle" }); assert.equal(await page.locator("html").getAttribute("lang"), "id");
    await page.locator(".studio-header").getByLabel("Bahasa antarmuka", { exact: true }).selectOption("en");
    for (const width of [320, 390, 768, 950, 951, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, "Shell overflow at " + width);
    }
    await page.getByLabel("Account menu", { exact: true }).click(); await page.keyboard.press("Escape");
    assert.equal(await page.locator(".studio-account").getAttribute("open"), null);
    await page.getByLabel("Account menu", { exact: true }).click(); await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await page.getByRole("button", { name: "Sign in through IS", exact: true }).waitFor();
    await context.close();

    const empty = await session("en-US", undefined, false);
    await empty.page.getByRole("heading", { name: "Create your next story series", exact: true }).waitFor();
    assert.equal(await empty.page.locator(".story-sidebar").isVisible(), false);
    for (const id of ["workspace", "characters", "world", "library"]) {
        const entry = empty.page.locator(`.studio-sidebar [data-destination="${id}"]`);
        assert.equal(await entry.isDisabled(), true);
        await entry.getByText("Select a series first").waitFor();
    }
    await empty.context.close();
    const initial = await session("id-ID");
    assert.equal(await initial.page.locator("html").getAttribute("lang"), "en", "New user must start in English");
    await initial.page.locator(".studio-header").getByLabel("Interface language", { exact: true }).selectOption("auto");
    await initial.page.reload({ waitUntil: "networkidle" }); assert.equal(await initial.page.locator("html").getAttribute("lang"), "id");
    assert.equal(await initial.page.evaluate(() => localStorage.getItem("sandcastle.uiLocale")), "auto");
    await initial.context.close();
    for (const saved of ["en", "id", "auto"]) {
        const existing = await session("id-ID", saved);
        assert.equal(await existing.page.locator("html").getAttribute("lang"), saved === "en" ? "en" : "id");
        await existing.context.close();
    }
    assert.deepEqual(mutations, [{ path: "/auth/logout", method: "POST" }]);
    assert.deepEqual(errors, []); assert.deepEqual(unexpected, []);
    fs.writeFileSync(out + "/measurements.json", JSON.stringify({ measurements, errors, unexpected, mutations }, null, 2));
    console.log("PASS B1: shared navigation, disabled capabilities, 68/61px header, 206px sidebar, modal focus/Escape/backdrop/resize, draft retention, language defaults/preferences, unchanged Story language, IS redirect and sign-out. No AI/domain writes.");
} finally { await browser.close(); }
