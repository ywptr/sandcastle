import { useEffect, useState, type ReactNode } from "react";
import { normalizeLocale, preferenceKey, readPreference, resolveLocale, translate, type LocalePreference } from "./core";
import { I18nContext } from "./context";
export function I18nProvider({children}: {children: ReactNode}) {
    const [preference, updatePreference] = useState(readPreference);
    const [languages, setLanguages] = useState(() => typeof navigator === "undefined" ? ["en"] : [...(navigator.languages?.length ? navigator.languages : [navigator.language])]);
    const locale = resolveLocale(preference,languages);
    useEffect(() => { document.documentElement.lang = locale; },[locale]);
    useEffect(() => { const change = () => setLanguages([...navigator.languages]); window.addEventListener("languagechange",change); return () => window.removeEventListener("languagechange",change); },[]);
    function setPreference(value: LocalePreference) { updatePreference(value); try { if (value === "auto") localStorage.removeItem(preferenceKey); else localStorage.setItem(preferenceKey,value); } catch { /* Device storage may be unavailable; current view still updates. */ } }
    return <I18nContext value={{locale,preference,unsupported:preference === "auto" && !normalizeLocale(languages[0] ?? ""),setPreference,t:(key,values) => translate(locale,key,values)}}>{children}</I18nContext>;
}

