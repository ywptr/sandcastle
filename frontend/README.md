# Local HTTPS development

Run the FastAPI backend on HTTP port 8012 and Vite with `npm run dev`.
From `backend/`, start the API with:

```sh
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8012 --reload
```

The browser opens `https://5480-deb13.lan.com:5182`; Vite uses the existing mkcert
certificate/key in `/home/user/certs/sandcastle/`.

The hostname must resolve to `192.168.0.99` through your LAN DNS or client hosts
file, and the browser must trust this host's existing mkcert development CA.
Renew the certificate on the development host with:

```sh
mkcert -cert-file /home/user/certs/sandcastle/dev-cert.pem -key-file /home/user/certs/sandcastle/dev-key.pem 5480-deb13.lan.com localhost 192.168.0.99 127.0.0.1
```

Restart Vite after certificate renewal. Keep the private key and CA private key
off Git; only the CA certificate is needed for trust on another client.

Development API and login URLs are always relative to `/api`, even if an old
`VITE_API_BASE_URL` points at an HTTP backend. Vite proxies `/api/*` to
`http://127.0.0.1:8012/api/*` without rewriting the path or query string. Methods,
request cookies, and response Set-Cookie headers pass through; forwarded headers
preserve the browser-facing scheme. FastAPI owns `/api/auth/callback`.

Use these **local** settings (do not change production configuration):

```dotenv
# frontend/.env.local (optional in development)
VITE_API_BASE_URL=/api

# backend/.env
SANDCASTLE_AUTH_CALLBACK_URL=https://5480-deb13.lan.com:5182/api/auth/callback
SANDCASTLE_WEB_URL=https://5480-deb13.lan.com:5182
SANDCASTLE_COOKIE_SECURE=true
```

Restart/reload the backend after changing its environment. IS must permit the
exact callback URI above for the configured client; this repository does not
register or modify IS redirect URIs. Keep existing IS credentials private.

Session cookies remain HttpOnly, SameSite=Lax, and host-only. Secure is enabled
for this local HTTPS flow. No backend TLS or extra CORS allowance is needed.
`/api/auth/me` returning 401 is normal signed-out state; other HTTP failures and
network failures remain visible errors. Cookie credentials stay included.

Production builds still honor a nonempty `VITE_API_BASE_URL` when a separate API
origin is required, otherwise they default to `/api`. The existing production
Vercel rewrite is unchanged. Production builds do not read local TLS files.

```sh
npm test
npm run lint
npm run build
```

Tests use Node's built-in runner and Vite's TS/env transform; no new test
framework or browser dependency is required.

---

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
