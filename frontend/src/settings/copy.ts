import { ApiError, type LLMProviderConfig, type LLMRoleBinding } from "../api/sandcastle";

// Settings copy is grouped for future SC#0004 translation keys; no i18n runtime yet.
export const providerNames = { openai: "OpenAI", anthropic: "Anthropic", google: "Google Gemini" };
export const roleNames = { creative_writer: "Creative writing", story_importer: "Story import", narrative_media_translator: "Production planning" };
export const detailLevels = ["easy", "normal", "difficult", "impossible"] as const;
export type SettingsDetail = typeof detailLevels[number];
export function settingsDetail(value: string): SettingsDetail { return detailLevels.includes(value as SettingsDetail) ? value as SettingsDetail : "easy"; }
export function canRoute(detail: SettingsDetail) { return detail === "difficult" || detail === "impossible"; }
export const aiCopy = {
    title: "AI", personalTitle: "My AI Providers", modeTitle: "AI mode", routingTitle: "Advanced routing",
    defaultTitle: "Sandcastle Default", defaultUnavailable: "Coming when workspace AI configuration is available. No workspace or platform AI is connected today.",
    personalMode: "Use my own providers", personalHelp: "Connect your own OpenAI, Anthropic, or Google account. Personal providers remain available when workspace AI arrives.",
    automatic: "Automatic chooses OpenAI, then Anthropic, then Google from your enabled personal providers with a saved key and model. It selects before a request; it does not try another provider after a failure.",
    unverified: "A saved key means connected, not verified by a live call. Saving or opening Settings makes no provider generation request.",
    saved: "Personal provider saved. Key input cleared.", removed: "Credential removed. Personal provider disabled.",
    removal: "Removing the saved credential disables this provider. It does not revoke the original key at the provider.",
    roleSaved: "Routing preference saved.", loadError: "Provider settings are unavailable. Retry to load your personal settings.",
    statuses: "Supported means Sandcastle has an adapter. Connected means a key is saved. Enabled means it may be used. Selected means your current routing chooses it for a task.",
    unavailableRole: "This task is unavailable. Enable and configure the selected personal provider, or choose Automatic.",
    workspaceFuture: "Future Workspace Settings → AI will hold shared workspace configuration. Your personal keys stay separate; workspace configuration is unavailable until trusted workspace identity exists.",
};
export function settingsError(failure: unknown): string {
    if (failure instanceof ApiError) {
        if (failure.status === 401) return "Sign in again to manage your personal AI settings.";
        if (failure.status === 422) return "Invalid configuration. Check the model ID and enable a connected provider before choosing it for a task.";
        if (failure.status === 503) return "Provider settings are unavailable. Retry, or ask the operator to check backend encryption configuration.";
    }
    return "Settings could not be saved. Please retry. If replacing a key, enter it again.";
}
export function providerTasks(provider: LLMProviderConfig, roles: LLMRoleBinding[]): string[] {
    return roles.filter((r) => r.available && r.selected_provider === provider.provider).map((r) => roleNames[r.role]);
}
