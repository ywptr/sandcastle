export function resolveApiBase(isDevelopment: boolean, configuredBase?: string): string {
    // The dev browser always uses Vite's HTTPS origin, including with an old .env.local.
    if (isDevelopment) return "/api";
    return configuredBase?.trim().replace(/\/+$/, "") || "/api";
}
