import { useState } from "react";
import { ratings, visuals, type DirectionInput, type StorytellingStyle } from "../api/creativeDirection";
import { genres, languages } from "../api/storyMetadata";
import { useI18n } from "../i18n/context";
import { StyleLibrary } from "./StyleLibrary";
export function CreativeOptions({direction,onChange,styles,metadata,onMetadata}: {direction:DirectionInput;onChange:(value:DirectionInput)=>void;styles:StorytellingStyle[];metadata?:{language:string;primary:string;secondary:string[]};onMetadata?:(value:{language:string;primary:string;secondary:string[]})=>void}) {
    const {t,locale} = useI18n(); const [library,setLibrary] = useState(false); const style=styles.find((s)=>s.id===direction.storytelling_style_id);
    const change = (fields:Partial<DirectionInput>) => onChange({...direction,...fields});
    return <section className="creative-options"><div className="panel-heading"><div><span>{t("field.style")}</span><h3>{style?.name[locale] ?? t("common.loading")}</h3></div><button type="button" onClick={()=>setLibrary(true)} disabled={!styles.length}>{t("styles.change")}</button></div><p>{t("field.independent")}</p>
        {metadata && onMetadata && <><label>{t("field.genre")}<select value={metadata.primary} onChange={(e)=>onMetadata({...metadata,primary:e.target.value,secondary:metadata.secondary.filter((g)=>g!==e.target.value)})}>{genres.map((g)=><option key={g} value={g}>{t(`genre.${g}`)}</option>)}</select></label><label>{t("field.language")}<select value={metadata.language} onChange={(e)=>onMetadata({...metadata,language:e.target.value})}>{Object.keys(languages).map((l)=><option key={l} value={l}>{t(`language.${l}`)}</option>)}</select></label></>}
        <label>{t("field.rating")}<select value={direction.audience_rating} onChange={(e)=>change({audience_rating:e.target.value})}>{ratings.map((r)=><option key={r} value={r}>{t(`rating.${r}`)}</option>)}</select></label>
        <details><summary>{t("field.advanced")}</summary>
            {metadata && onMetadata && <fieldset><legend>{t("field.secondary")}</legend>{genres.filter((g)=>g!==metadata.primary).map((g)=><label className="checkbox-label" key={g}><input type="checkbox" checked={metadata.secondary.includes(g)} disabled={!metadata.secondary.includes(g)&&metadata.secondary.length>=3} onChange={(e)=>onMetadata({...metadata,secondary:e.target.checked?[...metadata.secondary,g]:metadata.secondary.filter((v)=>v!==g)})}/>{t(`genre.${g}`)}</label>)}</fieldset>}
            <label>{t("field.visual")}<select value={direction.visual_style} onChange={(e)=>change({visual_style:e.target.value})}>{visuals.map((v)=><option key={v} value={v}>{t(`visual.${v}`)}</option>)}</select></label>
            <label>{t("field.culture")}<input maxLength={200} placeholder={t("common.notSet")} value={direction.cultural_setting??""} onChange={(e)=>change({cultural_setting:e.target.value||null})}/></label>
            <label>{t("field.era")}<input maxLength={200} placeholder={t("common.notSet")} value={direction.historical_era??""} onChange={(e)=>change({historical_era:e.target.value||null})}/></label>{direction.storytelling_style_id==="european_period_drama"&&!direction.historical_era&&<p>{t("field.periodHint")}</p>}
            <label>{t("field.tone")}<input maxLength={200} value={direction.tone??""} onChange={(e)=>change({tone:e.target.value||null})}/></label>
            <label>{t("field.tropes")}<input maxLength={1400} value={direction.tropes.join(",")} onChange={(e)=>change({tropes:e.target.value.split(",").slice(0,12)})} onBlur={()=>change({tropes:direction.tropes.map((v)=>v.trim()).filter(Boolean)})}/></label>
        </details><p className="muted">{t("rating.note")}</p>
        {library&&<StyleLibrary styles={styles} selected={direction.storytelling_style_id} onClose={()=>setLibrary(false)} onChoose={(s)=>change({storytelling_style_id:s.id,style_version:s.version})}/>}
    </section>;
}
