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
