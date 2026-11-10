import { useState, type FormEvent } from "react";
import type { Story, StoryCreateInput } from "../api/sandcastle";

import { languages, genres, genreLabel } from "../api/storyMetadata";

export function StoryMetadataForm({ story, onSave, onCancel }: {
    story?: Story; onSave: (input: StoryCreateInput) => Promise<void>; onCancel: () => void;
}) {
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
        catch (failure) { setError(failure instanceof Error ? failure.message : "Could not save. Please retry."); }
        finally { setBusy(false); }
    }
    return <form className="record-editor" onSubmit={submit}><fieldset disabled={busy}>
        <label>Title / idea *<input required maxLength={255} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
        <label>Premise<textarea rows={3} value={premise} onChange={(e) => setPremise(e.target.value)} placeholder="A person, a world, a possibility…" /></label>
        <label>Story language<select value={language} onChange={(e) => setLanguage(e.target.value)}><option value="">Not set</option>{Object.entries(languages).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
        <p className="muted">Saved per series. Guides generated prose and suggestions.</p>
        <label>Primary genre<select value={primary} onChange={(e) => { setPrimary(e.target.value); setSecondary((current) => current.filter((g) => g !== e.target.value)); }}><option value="">Not set</option>{genres.map((g) => <option key={g} value={g}>{genreLabel(g)}</option>)}</select></label>
        <details open={story ? true : undefined}><summary>Objective & secondary genres</summary>
            <label>Objective<textarea rows={3} value={objective} onChange={(e) => setObjective(e.target.value)} /></label>
            <fieldset><legend>Secondary genres (up to 3)</legend><div className="genre-options">{genres.filter((g) => g !== primary).map((g) => <label key={g}><input type="checkbox" checked={secondary.includes(g)} disabled={!secondary.includes(g) && secondary.length >= 3} onChange={(e) => setSecondary((current) => e.target.checked ? [...current, g] : current.filter((v) => v !== g))} />{genreLabel(g)}</label>)}</div></fieldset>
        </details>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="editor-actions"><button type="button" className="secondary-button" onClick={onCancel}>Cancel</button><button type="submit" className="primary-button">{busy ? "Saving…" : story ? "Save story details" : "Create series"}</button></div>
    </fieldset></form>;
}
