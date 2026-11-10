import { useEffect, useRef, useState } from "react";
import type { StorytellingStyle } from "../api/creativeDirection";
import { useI18n } from "../i18n/context";
export function StyleLibrary({styles,selected,onChoose,onClose}: {styles:StorytellingStyle[];selected:string;onChoose:(style:StorytellingStyle)=>void;onClose:()=>void}) {
    const {t,locale} = useI18n(); const dialog = useRef<HTMLDialogElement>(null);
    const [query,setQuery] = useState(""); const [region,setRegion] = useState(""); const [detail,setDetail] = useState(selected);
    useEffect(() => { const previous = document.activeElement as HTMLElement | null; const element = dialog.current; element?.showModal(); return () => { element?.close(); previous?.focus(); }; },[]);
    const aliases:Record<string,string> = {mena:"middle east arab timur tengah",europe:"european period eropa",south_asia:"india bollywood",southeast_asia:"thailand thai lakorn asia tenggara",east_asia:"korea japan china anime asia timur",north_america:"american hollywood amerika"};
    const results = styles.filter((s) => (!region || s.region === region) && `${s.name.en} ${s.name.id} ${s.summary[locale]} ${t(`region.${s.region}`)} ${aliases[s.region]}`.toLowerCase().includes(query.toLowerCase()));
    const style = styles.find((s) => s.id === detail); const localized = locale === "id" ? style?.localized_guidance?.id : undefined;
    return <dialog ref={dialog} className="style-drawer" onCancel={onClose} aria-labelledby="style-library-title"><div className="panel-heading"><h2 id="style-library-title">{t("styles.choose")}</h2><button type="button" onClick={onClose}>{t("common.close")}</button></div>
        <label>{t("styles.search")}<input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} /></label><label>{t("styles.region")}<select value={region} onChange={(e) => setRegion(e.target.value)}><option value="">{t("styles.all")}</option>{[...new Set(styles.map((s) => s.region))].map((r) => <option key={r} value={r}>{t(`region.${r}`)}</option>)}</select></label>
        {!results.length && <p role="status">{t("styles.empty")}</p>}<div className="style-results">{results.map((s) => <button type="button" aria-pressed={detail === s.id} key={s.id} onClick={() => setDetail(s.id)}><strong>{s.name[locale]}</strong><span>{s.summary[locale]}</span>{s.id === selected && <small>{t("common.selected")}</small>}</button>)}</div>
        {style && <section className="style-detail"><h3>{style.name[locale]}</h3><p>{style.summary[locale]}</p><p className="muted">{t("styles.preview")}</p><h4>{t("styles.narrative")}</h4><p>{localized?.narrative ?? style.narrative_guidance} {localized?.dialogue ?? style.dialogue_guidance}</p><h4>{t("styles.image")}</h4><p>{localized?.image ?? style.image_guidance}</p><h4>{t("styles.video")}</h4><p>{localized?.video ?? style.video_guidance}</p><p>{t("field.independent")}</p><button type="button" className="primary-button" onClick={() => {onChoose(style);onClose();}}>{t("common.use")}</button></section>}
    </dialog>;
}
