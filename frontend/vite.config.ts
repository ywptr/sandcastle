import fs from "node:fs";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig(({ command }) => ({
    plugins: [react()],
    server: {
        host: "192.168.0.99",
        port: 5173,
        strictPort: true,
        // Build does not need access to this machine's local development certificates.
        https: command === "serve" ? {
            key: fs.readFileSync("/home/user/certs/sandcastle/dev-key.pem"),
            cert: fs.readFileSync("/home/user/certs/sandcastle/dev-cert.pem"),
        } : undefined,
        proxy: {
            "/api": {
                target: "http://127.0.0.1:8000",
                changeOrigin: true,
                xfwd: true,
            },
        },
    },
}));
