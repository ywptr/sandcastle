// Optional HTTPS browser acceptance using isolated API fixtures; never generates media.
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || "playwright");
import assert from "node:assert/strict";
import { createHash, randomUUID } from "node:crypto";
import fs from "node:fs";
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const origin = process.env.WORKSPACE_ORIGIN || "https://192.168.0.99:5182";
const out = process.env.WORKSPACE_SCREENSHOTS || "/tmp/sc0001-visuals";
fs.mkdirSync(out, { recursive: true });
const page = await browser.newPage({ ignoreHTTPSErrors: true, viewport: { width: 1600, height: 1100 } });
const now = "2026-11-10T10:00:00Z";
const source = "Mara enters the abandoned station. An old radio lights up. Elias's voice comes through. Mara answers, but the transmission cuts out.";
const story = { story_id: "s1", user_id: "fixture", title: "The Last Signal", premise: "A deserted station receives a familiar voice.", objective: "Discover the signal's source.", language: "en", primary_genre: "mystery", secondary_genres: ["drama"], status: "draft", created_at: now, updated_at: now };
const scene = { scene_id: "sc1", story_id: "s1", source_action_id: null, sequence_number: 1, title: "The radio", content: source, status: "draft", created_at: now, updated_at: now };
const characters = [{ character_id: "c1", story_id: "s1", name: "Mara", description: "An apprentice cartographer.", appearance: "Dark curls.", outfit: "A blue coat.", personality: "Curious.", created_at: now, updated_at: now }];
const places = [{ place_id: "p1", story_id: "s1", name: "Abandoned station", description: "A disused radio station.", appearance: "Dusty windows and an old radio.", atmosphere: "Quiet.", created_at: now, updated_at: now }];
const canon = [{ canon_entry_id: "f1", story_id: "s1", type: "world", key: "station.state", value: "The station is abandoned.", status: "approved", subject_id: null, fact_type: null, created_at: now, updated_at: now }];
const config = { steps: ["scene_creation", "narrative_guidance", "canon_extraction", "canon_review", "continuity_check", "media_adaptation"].map((step_id) => ({ step_id, enabled: true })), order: [], guidance: { count: 3, recent_scene_count: 3 }, review: { require_before_media: true, review_new: true, review_conflicts: true, review_uncertain: true }, media: { aspect_ratio: "1:1", output_format: "webtoon" }, adaptation: { sensitivity_hints: [] }, references: { character_ids: null, place_ids: null, artifact_ids: [] } };
const workflow = { story_id: "s1", difficulty: "easy", workflow_template_id: "standard-story", template_version: 1, template_name: "Standard", configuration: config, capabilities: [], step_definitions: [] };
const hash = () => createHash("sha256").update(JSON.stringify({ content: scene.content, title: scene.title })).digest("hex");
const plans = [], approvals = [], requests = [], errors = [];
let failTranslation = false;
page.on("pageerror", (error) => errors.push(error.message));
page.on("request", (request) => { assert(!/api\.openai|api\.anthropic|generativelanguage|\/v2\/media/.test(request.url()), "Unexpected provider/media request"); });
function beats(plan) { return plan.production.panels || plan.production.shots || plan.production.beats; }
function compile(plan) {
    const value = structuredClone(plan);
    value.compiled_instructions = beats(value).map((beat, i) => ({ beat_number: i + 1, compiled: `Moment: ${beat.source_excerpt}\nVisual: ${beat.visual_description}\nCanon: The station is abandoned.`, override: value.overrides.find((o) => o.beat_number === i + 1)?.instruction || null }));
    value.compiled_instructions.forEach((b) => { b.effective = b.override ? b.override + "\nCanon: The station is abandoned." : b.compiled; });
    const manifest = { media_plan_id: value.plan_id, story_id: "s1", created_at: now, requests: value.compiled_instructions.map((item) => ({ media_request_id: randomUUID(), media_type: value.target_format === "webtoon" ? "image" : "video", purpose: value.target_format === "webtoon" ? "comic_panel" : "video_scene", prompt: item.effective, context: { production_format: value.target_format }, references: [], aspect_ratio: "9:16", created_at: now })) };
    return { plan: value, manifest };
}
function draft(format) {
    const shared = { narrative_purpose: "Reveal the signal", source_excerpt: "An old radio lights up.", visual_description: "Mara notices the radio lighting up.", character_ids: ["c1"], place_ids: ["p1"], artifact_ids: [], continuity_notes: ["Keep the speaker's identity unresolved."] };
    let production;
    if (format === "webtoon") production = { target_format: format, reading_order: "top_to_bottom", layout_hint: "A vertical reveal.", panels: [{ ...shared, panel_number: 1, dialogue: "", caption: "", framing: "wide" }, { ...shared, panel_number: 2, dialogue: "Elias?", caption: "", framing: "close_up" }] };
    if (format === "short_drama") production = { target_format: format, target_duration_seconds: 8, audio_direction: "A radio crackle breaks the silence.", shots: [3, 5].map((duration, i) => ({ ...shared, shot_number: i + 1, estimated_duration: duration, shot_scale: i ? "close_up" : "wide", camera_direction: "Hold on the reveal.", performance_direction: "Restrained surprise.", dialogue: i ? "Elias?" : "", voiceover: "", audio_or_ambience: "Static, then silence." })) };
    if (format === "story_reel") production = { target_format: format, target_duration_seconds: 6, narration_text_strategy: "Short readable phrases.", visual_strategy: "Place, signal, reaction.", beats: [1, 2].map((number) => ({ ...shared, beat_number: number, duration: 3, on_screen_text: number === 1 ? "One last signal." : "Then silence.", voiceover: number === 1 ? "Elias…" : "", transition_hint: "Cut, then hold." })) };
    return compile({ plan_id: randomUUID(), story_id: "s1", scene_id: "sc1", target_format: format, source_digest: hash(), context_digest: "c".repeat(64), production, summary: "A familiar voice interrupts the station's silence.", continuity_notes: [], warnings: [{ code: "continuity_uncertainty", message: "Elias is heard but not seen. Preserve that uncertainty." }], continuity_context: { story, characters, places, canon, references: [], guidance: { audience: "adult", maturity_rating: "general" }, workflow_configuration: config }, instruction: null, overrides: [], compiler_version: "production-v1", created_at: now }).plan;
}
await page.route("**/api/**", async (route) => {
    if (new URL(route.request().url()).pathname.endsWith("/creative-direction")) return route.fulfill({contentType:"application/json",body:"null"});
    const request = route.request(), path = new URL(request.url()).pathname;
    if (!path.startsWith("/api/")) return route.continue();
    const body = request.postDataJSON(); requests.push([path, request.method()]); let data;
    if (path === "/api/auth/me") data = { user_id: "fixture", email: "writer@example.test", name: "Production preview" };
    else if (path === "/api/stories") data = [story];
    else if (path.endsWith("/adaptations/compile")) data = compile(body.plan);
    else if (path.endsWith("/adaptations/approve")) {
        const compiled = compile(body.plan);
        data = { adaptation_id: randomUUID(), revision: approvals.filter((a) => a.plan.target_format === body.plan.target_format).length + 1, ...compiled, source_changed: false, context_changed: false, approved_at: now };
        approvals.unshift(data);
    } else if (path.endsWith("/adaptations")) {
        if (request.method() === "POST") {
            await new Promise((resolve) => setTimeout(resolve, 350));
            if (failTranslation) return route.fulfill({ status: 502, contentType: "application/json", body: JSON.stringify({ detail: "Translation failed. No plan saved." }) });
            data = draft(body.target_format); plans.push(data);
        } else data = approvals.map((a) => ({ ...a, source_changed: a.plan.source_digest !== hash() }));
    } else if (path.endsWith("/characters")) data = characters;
    else if (path.endsWith("/places")) data = places;
    else if (path.endsWith("/canon")) data = canon;
    else if (path.endsWith("/scenes/sc1")) { Object.assign(scene, body, { updated_at: new Date().toISOString() }); data = scene; }
    else if (path.endsWith("/scenes")) data = [scene];
    else if (path.endsWith("/actions")) data = [];
    else if (path.endsWith("/workflow")) data = workflow;
    else if (path.endsWith("/guidance/profile")) data = { audience: "adult", maturity_rating: "general", tone: null, genre: null, guidance_notes: null, average_rating: null, rating_count: 0, feedback_tags: [] };
    else throw Error("Unexpected fixture endpoint: " + path);
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(data) });
});
async function openScene() {
    await page.goto(origin, { waitUntil: "networkidle" });
    await page.locator(".story-list-item").click();
    await page.getByRole("navigation", { name: "Story workspace", exact: true }).getByRole("button", { name: /^Scenes/ }).first().click();
    await page.getByRole("button", { name: "Production · Webtoon / Short Drama / Story Reel", exact: true }).click();
    await page.getByText("No approved production plans for this Scene yet.").or(page.locator(".history-item").first()).waitFor();
}
try {
    await openScene();
    await page.getByRole("button", { name: "Prepare production plan", exact: true }).click();
    await page.getByText("Interpreting the narrative and preparing the complete plan…", { exact: true }).waitFor();
    await page.getByText("Scene prepared for Webtoon.", { exact: false }).waitFor();
    assert.equal(await page.getByLabel("Plan summary", { exact: true }).count(), 0, "Easy should start with a summary");
    await page.getByRole("button", { name: "Review plan", exact: true }).click();
    await page.getByLabel(/^Visual description/).first().fill("Wide view of Mara beside the radio.");
    const nav = page.getByRole("navigation", { name: "Story workspace", exact: true });
    await nav.getByRole("button", { name: "Characters", exact: true }).click();
    await nav.getByRole("button", { name: /^Scenes/ }).first().click();
    assert.equal(await page.getByLabel(/^Visual description/).first().inputValue(), "Wide view of Mara beside the radio.");
    const productionToggle = page.getByRole("button", { name: "Production · Webtoon / Short Drama / Story Reel", exact: true });
    await productionToggle.click(); await productionToggle.click();
    assert.equal(await page.getByLabel(/^Visual description/).first().inputValue(), "Wide view of Mara beside the radio.");
    await page.getByRole("button", { name: "Move panel 1 down", exact: true }).click();
    assert.equal(await page.getByLabel(/^Visual description/).nth(1).inputValue(), "Wide view of Mara beside the radio.");
    await page.getByRole("button", { name: "Generation instructions", exact: true }).click();
    await page.getByRole("heading", { name: "Provider-neutral generation instructions", exact: true }).waitFor();
    assert.equal(await page.getByText("Explicit presentation overrides", { exact: true }).count(), 0);
    await page.screenshot({ path: out + "/webtoon-review.png", fullPage: true });
    await page.getByRole("button", { name: "Approve production plan", exact: true }).click();
    await page.getByText("Approved revision 1 saved. No media was generated.", { exact: true }).waitFor();
    assert.equal(approvals[0].plan.production.panels[1].visual_description, "Wide view of Mara beside the radio.");
    await page.reload({ waitUntil: "networkidle" });
    await page.locator(".story-list-item").click();
    await page.getByRole("navigation", { name: "Story workspace", exact: true }).getByRole("button", { name: /^Scenes/ }).first().click();
    await page.getByRole("button", { name: "Production · Webtoon / Short Drama / Story Reel", exact: true }).click();
    await page.locator(".history-item").first().click();
    await page.getByText("Approved revision 1 · immutable snapshot", { exact: true }).waitFor();
    await page.getByRole("button", { name: "Edit scene", exact: true }).click();
    await page.getByLabel(/^Scene content/).fill(source + " The room darkens.");
    await page.getByRole("button", { name: "Save scene", exact: true }).click();
    await page.getByText("Scene has changed since this production plan was created or approved.", { exact: false }).waitFor();
    await page.getByRole("button", { name: "Generation instructions", exact: true }).click();
    await page.getByRole("heading", { name: "Provider-neutral generation instructions", exact: true }).waitFor();
    await page.screenshot({ path: out + "/stale-history.png", fullPage: true });
    for (const [format, label] of [["short_drama", "Short Drama"], ["story_reel", "Story Reel"]]) {
        await page.getByRole("button", { name: label, exact: true }).click();
        await page.getByRole("button", { name: "Create new adaptation", exact: true }).click();
        await page.getByText(`Scene prepared for ${label}.`, { exact: false }).waitFor();
        await page.getByRole("button", { name: "Review plan", exact: true }).click();
        const duration = page.getByLabel(format === "short_drama" ? "Estimated duration (seconds)" : "Beat duration (seconds)", { exact: true });
        await duration.first().fill("4");
        await page.getByText(`Estimated total: ${format === "short_drama" ? 9 : 7} seconds`, { exact: false }).waitFor();
        if (format === "story_reel") await page.getByLabel(/^On-screen text/).first().fill("A familiar voice.");
        await page.screenshot({ path: out + "/" + format + ".png", fullPage: true });
        await page.getByRole("button", { name: "Approve production plan", exact: true }).click();
        await page.getByText("Approved revision 1 saved. No media was generated.", { exact: true }).waitFor();
    }
    workflow.difficulty = "difficult";
    await openScene();
    await page.getByRole("button", { name: "Prepare production plan", exact: true }).click();
    await page.getByText("Scene prepared for Webtoon.", { exact: false }).waitFor();
    await page.getByText("Explicit presentation overrides", { exact: true }).click();
    await page.getByLabel(/^Beat 1 presentation override/).fill("Use a low viewpoint; keep the same event.");
    await page.getByRole("button", { name: "Generation instructions", exact: true }).click();
    await page.getByText("Explicit override (stored separately)", { exact: true }).waitFor();
    await page.getByRole("button", { name: "Approve production plan", exact: true }).click();
    await page.getByText("Approved revision 2 saved. No media was generated.", { exact: true }).waitFor();
    assert.equal(approvals[0].plan.overrides.length, 1);
    workflow.difficulty = "impossible";
    await openScene();
    await page.locator(".history-item").first().click();
    await page.getByText("Full structured plan", { exact: true }).click();
    await page.getByText("Provider-neutral generation manifest", { exact: true }).click();
    for (const width of [390, 320]) {
        await page.setViewportSize({ width, height: 900 });
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, "overflow at " + width);
        if (width === 390) await page.screenshot({ path: out + "/mobile-production.png", fullPage: true });
    }
    failTranslation = true;
    const count = approvals.length;
    await page.getByRole("button", { name: "Create new adaptation", exact: true }).click();
    await page.getByText("Production planning could not complete.", { exact: false }).waitFor();
    assert.equal(approvals.length, count);
    assert.equal(await page.locator("img,video,audio").count(), 0);
    assert.deepEqual(errors, []);
    console.log("PASS: format selection, loading/error, all format editors, reorder/edit/totals, instruction inspection, Easy/Difficult/Impossible disclosure, overrides, approval/reload/history, stale Scene warning, mobile layout, normal Scene save. No media/provider execution. Fixture API calls: " + requests.length);
} catch (error) { await page.screenshot({ path: out + "/browser-error.png", fullPage: true }); throw error; } finally { await browser.close(); }
