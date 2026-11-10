import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

let server;
let api;
let resolveApiBase;

before(async () => {
    // Use Vite's actual TS/env transform, without a listener, browser, or new test dependency.
    server = await createServer({
        root: fileURLToPath(new URL("..", import.meta.url)),
        configFile: false,
        server: { middlewareMode: true, hmr: false, watch: null },
        appType: "custom",
    });
    api = await server.ssrLoadModule("/src/api/sandcastle.ts");
    ({ resolveApiBase } = await server.ssrLoadModule("/src/api/baseUrl.ts"));
});

after(async () => { await server?.close(); });

function json(body, status = 200) {
    return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

test("development stays same-origin even with an old absolute API setting", () => {
    assert.equal(resolveApiBase(true, "http://192.168.0.99:8000/api"), "/api");
    assert.equal(api.loginUrl(), "/api/auth/login");
});

test("production keeps its configured API origin and defaults to /api", () => {
    assert.equal(resolveApiBase(false, "https://api.example.test/api/"), "https://api.example.test/api");
    assert.equal(resolveApiBase(false), "/api");
    assert.equal(resolveApiBase(false, ""), "/api");
});

test("auth/me 200 returns the authenticated user using a relative URL and cookies", async (t) => {
    const user = { user_id: "alice", email: "alice@example.test", name: "Alice" };
    t.mock.method(globalThis, "fetch", async (url, options) => {
        assert.equal(url, "/api/auth/me");
        assert.equal(options.credentials, "include");
        return json(user);
    });
    assert.deepEqual(await api.getCurrentUser(), user);
});

test("auth/me 401 is a normal completed signed-out check", async (t) => {
    t.mock.method(globalThis, "fetch", async () => json({ detail: "Not authenticated" }, 401));
    assert.equal(await api.getCurrentUser(), null);
});

test("auth/me network failure remains an error", async (t) => {
    const failure = new TypeError("Failed to fetch");
    t.mock.method(globalThis, "fetch", async () => { throw failure; });
    await assert.rejects(api.getCurrentUser(), (error) => error === failure);
});

test("unexpected auth/me HTTP failures remain errors", async (t) => {
    for (const status of [403, 500, 503]) {
        const mock = t.mock.method(globalThis, "fetch", async () => json({ detail: "Service error" }, status));
        await assert.rejects(api.getCurrentUser(), (error) => error instanceof api.ApiError && error.status === status);
        mock.mock.restore();
    }
});

test("non-auth API requests remain relative and do not suppress authorization errors", async (t) => {
    t.mock.method(globalThis, "fetch", async (url, options) => {
        assert.equal(url, "/api/stories");
        assert.equal(options.credentials, "include");
        return json({ detail: "Session expired" }, 401);
    });
    await assert.rejects(api.listStories(), (error) => error instanceof api.ApiError && error.status === 401);
});

test("guidance requests stay same-origin and do not call Scene generation", async (t) => {
    const calls = [];
    t.mock.method(globalThis, "fetch", async (url, options) => {
        calls.push([url, options.method]);
        assert.equal(options.credentials, "include");
        return json(url.endsWith("narrative_guidance") ? { story_id: "story", suggestions: [] } : { audience: "teen" });
    });
    await api.getGuidanceProfile("story");
    await api.saveGuidanceProfile("story", { audience: "teen", maturity_rating: "mild" });
    await api.suggestNextScene("story");
    assert.deepEqual(calls, [["/api/stories/story/guidance/profile", undefined], ["/api/stories/story/guidance/profile", "PUT"], ["/api/stories/story/workflow/steps/narrative_guidance", "POST"]]);
});

test("choosing a suggestion passes its editable text without fetching or generating", async (t) => {
    const { SuggestionChoices } = await server.ssrLoadModule("/src/components/NarrativeGuidance.tsx");
    const suggestion = { id: "1", title: "A small step", text: "Try a small step toward the goal." };
    let requestText = "Existing request";
    let fetches = 0;
    t.mock.method(globalThis, "fetch", async () => { fetches++; throw Error("Selection must not fetch"); });
    const tree = SuggestionChoices({ suggestions: [suggestion], onSelect: (text) => { requestText = text; } });
    const article = tree.props.children[0];
    const button = article.props.children.find((child) => child?.type === "button");
    button.props.onClick();
    assert.equal(requestText, suggestion.text);
    assert.equal(fetches, 0);
});

test("workflow controls expose only capabilities supplied by the backend", async () => {
    const { WorkflowControls } = await server.ssrLoadModule("/src/components/WorkflowPanel.tsx");
    const { renderToStaticMarkup } = await import("react-dom/server");
    const config = {
        steps: [{ step_id: "scene_creation", enabled: true }, { step_id: "media_execution", enabled: false }],
        order: ["scene_creation", "media_execution"], guidance: { count: 3, recent_scene_count: 4 },
        review: { require_before_media: false, review_new: false, review_conflicts: true, review_uncertain: true },
        media: { output_format: "image", aspect_ratio: "1:1" }, adaptation: { sensitivity_hints: [] },
        references: { character_ids: null, place_ids: null, artifact_ids: [] },
    };
    const definitions = [{ step_id: "scene_creation", label: "Scene Creation", required: true, available: true },
        { step_id: "media_execution", label: "Media Execution", required: false, available: false }];
    const html = (capabilities) => renderToStaticMarkup(WorkflowControls({ config, capabilities, definitions, onChange() {} }));
    assert.equal(html([]), "");
    assert.match(html(["guidance_options"]), /Alternatives/);
    assert.doesNotMatch(html(["guidance_options"]), /Supported steps/);
    assert.match(html(["step_configuration", "step_ordering"]), /Supported steps/);
    assert.match(html(["step_configuration"]), /deferred/);
    assert.doesNotMatch(html(["step_configuration"]), /Reference selections/);
    assert.match(html(["reference_selection"]), /Reference selections/);
});

test("workflow choices use authenticated endpoints without running domain actions", async (t) => {
    const calls = [];
    t.mock.method(globalThis, "fetch", async (url, options) => { calls.push([url, options.method]); return json({}); });
    await api.getStoryWorkflow("story");
    await api.listWorkflowTemplates();
    await api.listDifficulties();
    await api.saveStoryWorkflow("story", { difficulty: "normal", workflow_template_id: "webtoon", template_version: 1 });
    assert.deepEqual(calls, [["/api/stories/story/workflow", undefined], ["/api/workflows/templates", undefined], ["/api/workflows/difficulties", undefined], ["/api/stories/story/workflow", "PUT"]]);
});

test("M13 Story metadata preserves explicit nulls and empty secondary genres", async (t) => {
    const input = { title: "A new beginning", premise: null, objective: null, language: null, primary_genre: null, secondary_genres: [] };
    const calls = [];
    t.mock.method(globalThis, "fetch", async (url, options) => {
        calls.push([url, options.method]);
        assert.equal(options.credentials, "include");
        assert.deepEqual(JSON.parse(options.body), input);
        return json({ story_id: "story", ...input });
    });
    assert.equal((await api.createStory(input)).language, null);
    assert.deepEqual((await api.updateStory("story", input)).secondary_genres, []);
    assert.deepEqual(calls, [["/api/stories", "POST"], ["/api/stories/story", "PATCH"]]);
});

test("metadata controls exactly mirror the M13 bounded backend taxonomy", async () => {
    const { readFile } = await import("node:fs/promises");
    const source = await readFile(new URL("../../backend/app/stories/metadata.py", import.meta.url), "utf8");
    const { languages, genres } = await server.ssrLoadModule("/src/api/storyMetadata.ts");
    const literal = (name) => source.match(new RegExp(name + " = (?:Annotated\\[)?Literal\\[([^\\]]+)\\]"))[1].match(/"([^"]+)"/g).map((s) => JSON.parse(s));
    assert.deepEqual(Object.keys(languages), literal("Language"));
    assert.deepEqual(genres, literal("Genre"));
});

test("candidate, Universe, and artifact inspection use existing authenticated read endpoints", async (t) => {
    const calls = [];
    t.mock.method(globalThis, "fetch", async (url, options) => { calls.push(url); assert.equal(options.credentials, "include"); assert.equal(options.method, undefined); return json([]); });
    await api.listCanonCandidates("story");
    await api.listUniverses();
    await api.listUniverseMembers("world");
    await api.listUniverseReferences("world");
    await api.listCanonVersions("object");
    await api.listArtifacts("story");
    await api.listReferenceBindings("story");
    assert.deepEqual(calls, ["/api/stories/story/canon/candidates", "/api/universes", "/api/universes/world/stories", "/api/universes/world/canon/references", "/api/canon/library/object/versions", "/api/artifacts?story_id=story", "/api/stories/story/references"]);
});

test("candidate review sends explicit conflict and uncertainty acceptance only when chosen", async (t) => {
    const calls = [];
    t.mock.method(globalThis, "fetch", async (url, options) => { calls.push([url, JSON.parse(options.body)]); return json({}); });
    await api.reviewCanonCandidate("story", "proposal", true, true, true);
    await api.reviewCanonCandidate("story", "proposal", false, false, false);
    assert.deepEqual(calls, [["/api/stories/story/canon/candidates/proposal/approve", { replace_conflicts: true, accept_uncertain: true }], ["/api/stories/story/canon/candidates/proposal/reject", {}]]);
});

test("AI settings requests preserve omitted credentials and use account-scoped routes", async (t) => {
    const calls = [];
    t.mock.method(globalThis, "fetch", async (url, options) => {
        calls.push([url, options.method, options.body ? JSON.parse(options.body) : null]);
        assert.equal(options.credentials, "include");
        return json({});
    });
    await api.listLLMProviders();
    await api.saveLLMProvider("anthropic", { enabled: false, config: { default_model: "claude-test" } });
    await api.removeLLMCredentials("anthropic");
    await api.listLLMRoles();
    await api.saveLLMRole("creative_writer", null);
    assert.deepEqual(calls, [
        ["/api/settings/llm/providers", undefined, null],
        ["/api/settings/llm/providers/anthropic", "PUT", { enabled: false, config: { default_model: "claude-test" } }],
        ["/api/settings/llm/providers/anthropic/credentials", "DELETE", null],
        ["/api/settings/llm/roles", undefined, null],
        ["/api/settings/llm/roles/creative_writer", "PUT", { provider: null }],
    ]);
});

test("production endpoints keep translation, review, approval, and history separate", async (t) => {
    const production = await server.ssrLoadModule("/src/api/production.ts");
    const calls = [];
    t.mock.method(globalThis, "fetch", async (url, options) => {
        calls.push([url, options.method, options.body ? JSON.parse(options.body) : null]);
        assert.equal(options.credentials, "include");
        return json({});
    });
    const plan = { plan_id: "draft" };
    await production.translateProduction("story", "scene", "story_reel", "Keep the reveal quiet.");
    await production.compileProduction("story", "scene", plan);
    await production.approveProduction("story", "scene", plan);
    await production.listProductions("story", "scene");
    assert.deepEqual(calls, [
        ["/api/stories/story/scenes/scene/adaptations", "POST", { target_format: "story_reel", instruction: "Keep the reveal quiet." }],
        ["/api/stories/story/scenes/scene/adaptations/compile", "POST", { plan }],
        ["/api/stories/story/scenes/scene/adaptations/approve", "POST", { approved: true, plan }],
        ["/api/stories/story/scenes/scene/adaptations", undefined, null],
    ]);
});

test("production reorder renumbers beats and keeps explicit overrides with their beat", async () => {
    const { moveBeat, productionBeats } = await server.ssrLoadModule("/src/api/productionEditing.ts");
    const plan = { production: { target_format: "webtoon", panels: [{ panel_number: 1, visual_description: "First" }, { panel_number: 2, visual_description: "Second" }] }, overrides: [{ beat_number: 1, instruction: "Low viewpoint" }], compiled_instructions: [{ compiled: "Old" }] };
    const moved = moveBeat(plan, 0, 1);
    assert.equal(productionBeats(moved.production)[0].visual_description, "Second");
    assert.deepEqual(moved.production.panels.map((p) => p.panel_number), [1, 2]);
    assert.deepEqual(moved.overrides, [{ beat_number: 2, instruction: "Low viewpoint" }]);
    assert.deepEqual(moved.compiled_instructions, []);
    assert.equal(plan.production.panels[0].visual_description, "First");
});

test("duration edits update the format-specific total and source digest tracks exact text", async () => {
    const { replaceBeats, sceneDigest } = await server.ssrLoadModule("/src/api/productionEditing.ts");
    for (const format of ["short_drama", "story_reel"]) {
        const plan = { production: { target_format: format, target_duration_seconds: 1 }, overrides: [], compiled_instructions: [] };
        const beats = format === "short_drama" ? [{ estimated_duration: 3 }, { estimated_duration: 4 }] : [{ duration: 3 }, { duration: 4 }];
        const edited = replaceBeats(plan, beats);
        assert.equal(edited.production.target_duration_seconds, 7);
    }
    const { createHash } = await import("node:crypto");
    const source = { content: "Mara hears a signal.\n信号", title: "The radio" };
    assert.equal(await sceneDigest(source), createHash("sha256").update(JSON.stringify(source)).digest("hex"));
    assert.notEqual(await sceneDigest(source), await sceneDigest({ ...source, content: source.content + " " }));
});

test("AI settings partial toggle and explicit model routing stay account scoped", async (t) => {
    const calls = [];
    t.mock.method(globalThis, "fetch", async (url, options) => {
        calls.push([url, JSON.parse(options.body)]);
        return json({});
    });
    await api.saveLLMProvider("openai", { enabled: false });
    await api.saveLLMRole("narrative_media_translator", "google", "gemini-test");
    assert.deepEqual(calls, [
        ["/api/settings/llm/providers/openai", { enabled: false }],
        ["/api/settings/llm/roles/narrative_media_translator", { provider: "google", model: "gemini-test" }],
    ]);
});

test("Settings disclosure and error copy do not expose provider payloads", async () => {
    const copy = await server.ssrLoadModule("/src/settings/copy.ts");
    assert.equal(copy.canRoute("easy"), false);
    assert.equal(copy.canRoute("normal"), false);
    assert.equal(copy.canRoute("difficult"), true);
    assert.equal(copy.canRoute("impossible"), true);
    assert.equal(copy.settingsDetail("unknown"), "easy");
    assert.equal(copy.roleNames.narrative_media_translator, "Production planning");
    for (const status of [401, 422, 503, 500]) {
        assert.equal(copy.settingsError(new api.ApiError(status, "private-upstream-secret")).includes("private-upstream-secret"), false);
    }
});

test("UI locale resolves explicit preference before normalized browser language with English fallback", async () => {
    const core = await server.ssrLoadModule("/src/i18n/core.ts");
    assert.equal(core.browserLocale(["id-ID"]), "id");
    assert.equal(core.browserLocale(["en-GB"]), "en");
    assert.equal(core.browserLocale(["fr-FR"]), "en");
    assert.equal(core.resolveLocale("en", ["id-ID"]), "en");
    assert.equal(core.resolveLocale("auto", ["id-ID"]), "id");
    assert.equal(core.translate("id", "create.title"), "Cerita apa yang ingin kamu buat?");
    assert.equal(core.translate("id", "direction.revision", {revision:2}), "Revisi 2");
    const resources = await server.ssrLoadModule("/src/i18n/resources.ts");
    assert.deepEqual(Object.keys(resources.en).sort(), Object.keys(resources.id).sort());
    resources.en["test.fallback"] = "English fallback";
    assert.equal(core.translate("id", "test.fallback"), "English fallback");
    delete resources.en["test.fallback"];
});

test("Get Started approval is atomic and read-only historical language is omitted on revision", async (t) => {
    const creative = await server.ssrLoadModule("/src/api/creativeDirection.ts");
    const calls=[];
    t.mock.method(globalThis,"fetch",async(url,options)=>{calls.push([url,options.body?JSON.parse(options.body):null]);return json({});});
    await creative.recommendDirection("An idea", "webtoon");
    await creative.startSeries({title:"One Story",language:"id"},creative.initialDirection());
    await creative.saveDirection("s",{...creative.initialDirection(),expected_revision:1,language_at_approval:"en"});
    assert.equal(calls[0][0],"/api/styles/recommend");assert.equal("locale" in calls[0][1],false);
    assert.equal(calls[1][0],"/api/stories/start");assert.equal(calls[1][1].story.language,"id");
    assert.equal("language_at_approval" in calls[2][1],false);
});
