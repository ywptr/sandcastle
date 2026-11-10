import { createContext, useContext } from "react";
import { translate, type Locale, type LocalePreference } from "./core";
export const I18nContext = createContext({ locale: "en" as Locale, preference: "auto" as LocalePreference, unsupported: false, setPreference: (_value: LocalePreference) => {}, t: (key: string, values?: Record<string, string | number>) => translate("en",key,values) });
export function useI18n() { return useContext(I18nContext); }
