import { en, id } from "./resources";
export type Locale = "en" | "id";
export type LocalePreference = Locale | "auto";
export const preferenceKey = "sandcastle.uiLocale";
export function normalizeLocale(value: string): Locale | null {
    const code = value.toLowerCase().split(/[-_]/)[0];
    return code === "en" || code === "id" ? code : null;
}
export function browserLocale(languages: readonly string[]): Locale { return normalizeLocale(languages[0] ?? "") ?? "en"; }
export function resolveLocale(preference: LocalePreference, languages: readonly string[]): Locale { return preference === "auto" ? browserLocale(languages) : preference; }
export function readPreference(): LocalePreference { try { const value = localStorage.getItem(preferenceKey); return value === "en" || value === "id" || value === "auto" ? value : "en"; } catch { return "en"; } }
export function translate(locale: Locale, key: string, values: Record<string, string | number> = {}) {
    const text = (locale === "id" ? id[key] : en[key]) ?? en[key] ?? key;
    return text.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? `{${name}}`));
}
