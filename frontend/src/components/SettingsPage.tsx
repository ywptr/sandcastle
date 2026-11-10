import { useState } from "react";
import type { AuthUser } from "../api/sandcastle";
import { detailLevels, type SettingsDetail } from "../settings/copy";
import { useI18n } from "../i18n/context";
import type { LocalePreference } from "../i18n/core";
import { AIProviderSettings } from "./AIProviderSettings";
export function SettingsPage({ user, initialDetail, onClose }: {user: AuthUser; initialDetail: SettingsDetail; onClose: () => void;}) {
    const {t,preference,setPreference,unsupported} = useI18n();
    const [page,setPage]=useState("general"); const [detail,setDetail]=useState(initialDetail);
    return <main className="settings-page"><header className="panel-heading"><div><span className="eyebrow">{t("settings.scope")}</span><h1>{t("nav.settings")}</h1></div><button type="button" className="secondary-button" onClick={onClose}>{t("nav.backStudio")}</button></header><nav className="settings-nav" aria-label={t("nav.settings")}>{["general","ai","account"].map((item)=><button type="button" key={item} aria-current={page===item?"page":undefined} onClick={()=>setPage(item)}>{t(`nav.${item}`)}</button>)}</nav>
        {page==="general"&&<section className="panel"><h2>{t("nav.general")}</h2><label>{t("settings.language")}<select value={preference} onChange={(e)=>setPreference(e.target.value as LocalePreference)}><option value="auto">{t("settings.automatic")}</option><option value="en">English</option><option value="id">Bahasa Indonesia</option></select></label><p>{t("settings.languageHelp")}</p>{unsupported&&<p role="status">{t("settings.unsupported")}</p>}<label>{t("settings.detail")}<select value={detail} onChange={(e)=>setDetail(e.target.value as SettingsDetail)}>{detailLevels.map((v)=><option key={v} value={v}>{t(`difficulty.${v}`)}</option>)}</select></label><p>{t("settings.detailHint")}</p><p>{t("settings.levels")}</p><button type="button" className="primary-button" onClick={()=>setPage("ai")}>{t("settings.manage")}</button></section>}
        {page==="ai"&&<AIProviderSettings detail={detail}/>}{page==="account"&&<section className="panel"><h2>{t("nav.account")}</h2><p>{user.name??user.email}</p><p>{user.email}</p><p>{t("settings.identity")}</p><h3>{t("settings.workspace")}</h3><p>{t("settings.workspaceHelp")}</p></section>}
    </main>;
}
