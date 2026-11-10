import { useState, type FormEvent } from "react";
import type { Story, StoryCreateInput } from "../api/sandcastle";

import { useI18n } from "../i18n/context";
import { languages, genres } from "../api/storyMetadata";

export function StoryMetadataForm({ story, onSave, onCancel }: {
    story?: Story; onSave: (input: StoryCreateInput) => Promise<void>; onCancel: () => void;
}) {
    const {t} = useI18n();
    const [title, setTitle] = useState(story?.title ?? "");
    const [premise, setPremise] = useState(story?.premise ?? "");
    const [objective, setObjective] = useState(story?.objective ?? "");
    const [language, setLanguage] = useState(story?.language ?? "");
    const [primary, setPrimary] = useState(story?.primary_genre ?? "");
    const [secondary, setSecondary] = useState(story?.secondary_genres ?? []);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    async function submit(event: FormEvent) {
        event.preventDefault();
        if (busy || !title.trim()) return;
        setBusy(true); setError(null);
        try { await onSave({ title: title.trim(), premise: premise.trim() || null, objective: objective.trim() || null,
            language: language || null, primary_genre: primary || null, secondary_genres: secondary }); }
        catch { setError(t("common.error")); }
        finally { setBusy(false); }
    }
    return <form className="record-editor" onSubmit={submit}><fieldset disabled={busy}>
        <label>{t("metadata.title")}<input required maxLength={255} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
        <label>{t("metadata.premise")}<textarea rows={3} value={premise} onChange={(e) => setPremise(e.target.value)} placeholder={t("create.placeholder")} /></label>
        <label>{t("metadata.language")}<select value={language} onChange={(e) => setLanguage(e.target.value)}><option value="">{t("common.notSet")}</option>{Object.entries(languages).map(([id]) => <option key={id} value={id}>{t(`language.${id}`)}</option>)}</select></label>
        <p className="muted">{t("metadata.languageHelp")}</p>
        <label>{t("field.genre")}<select value={primary} onChange={(e) => { setPrimary(e.target.value); setSecondary((current) => current.filter((g) => g !== e.target.value)); }}><option value="">{t("common.notSet")}</option>{genres.map((g) => <option key={g} value={g}>{t(`genre.${g}`)}</option>)}</select></label>
        <details open={story ? true : undefined}><summary>{t("metadata.advanced")}</summary>
            <label>{t("metadata.objective")}<textarea rows={3} value={objective} onChange={(e) => setObjective(e.target.value)} /></label>
            <fieldset><legend>{t("field.secondary")}</legend><div className="genre-options">{genres.filter((g) => g !== primary).map((g) => <label key={g}><input type="checkbox" checked={secondary.includes(g)} disabled={!secondary.includes(g) && secondary.length >= 3} onChange={(e) => setSecondary((current) => e.target.checked ? [...current, g] : current.filter((v) => v !== g))} />{t(`genre.${g}`)}</label>)}</div></fieldset>
        </details>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="editor-actions"><button type="button" className="secondary-button" onClick={onCancel}>{t("common.cancel")}</button><button type="submit" className="primary-button">{t(busy ? "common.saving" : story ? "metadata.save" : "metadata.create")}</button></div>
    </fieldset></form>;
}
