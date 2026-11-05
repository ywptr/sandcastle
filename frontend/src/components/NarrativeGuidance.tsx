import { useEffect, useState } from "react";
import {
    getGuidanceProfile, saveGuidanceProfile, suggestNextScene,
    type GuidanceProfileInput, type NextSceneSuggestion,
} from "../api/sandcastle";

export function SuggestionChoices({ suggestions, onSelect, disabled = false }: {
    suggestions: NextSceneSuggestion[]; onSelect: (text: string) => void; disabled?: boolean;
}) {
    return <div className="suggestion-choices" aria-label="Next-scene suggestions">
        {suggestions.map((suggestion) => <article key={suggestion.id}>
            <strong>{suggestion.title}</strong><p>{suggestion.text}</p>
            <button type="button" className="secondary-button" disabled={disabled}
                onClick={() => onSelect(suggestion.text)}>Use this suggestion</button>
        </article>)}
    </div>;
}

export function NarrativeGuidance({ storyId, onSelect, disabled }: {
    storyId: string; onSelect: (text: string) => void; disabled: boolean;
}) {
    const [profile, setProfile] = useState<GuidanceProfileInput | null>(null);
    const [suggestions, setSuggestions] = useState<NextSceneSuggestion[]>([]);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState<string | null>(null);
    const [retry, setRetry] = useState(0);
    useEffect(() => {
        let active = true;
        getGuidanceProfile(storyId).then((value) => {
            if (!active) return;
            const { audience, maturity_rating, tone, genre, guidance_notes, average_rating, rating_count, feedback_tags } = value;
            setProfile({ audience, maturity_rating, tone, genre, guidance_notes, average_rating, rating_count, feedback_tags });
            setError(null);
        }).catch((failure) => { if (active) setError(failure instanceof Error ? failure.message : "Could not load guidance settings."); });
        return () => { active = false; };
    }, [storyId, retry]);

    async function save() {
        if (!profile || busy) return;
        setBusy(true); setError(null); setStatus(null);
        try {
            await saveGuidanceProfile(storyId, profile);
            setSuggestions([]);
            setStatus("Audience settings saved.");
        } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not save settings."); }
        finally { setBusy(false); }
    }

    async function suggest() {
        if (busy) return;
        setBusy(true); setError(null); setStatus(null); setSuggestions([]);
        try {
            const result = await suggestNextScene(storyId);
            setSuggestions(result.suggestions);
        } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not suggest next steps."); }
        finally { setBusy(false); }
    }

    return <div className="narrative-guidance">
        <details>
            <summary>Audience and content settings</summary>
            {profile && <fieldset disabled={disabled || busy}>
                <label>Intended audience
                    <select value={profile.audience} onChange={(event) => setProfile({ ...profile, audience: event.target.value as GuidanceProfileInput["audience"] })}>
                        <option value="child">Child</option><option value="teen">Teen</option><option value="adult">Adult</option>
                    </select>
                </label>
                <label>Content maturity
                    <select value={profile.maturity_rating} onChange={(event) => setProfile({ ...profile, maturity_rating: event.target.value as GuidanceProfileInput["maturity_rating"] })}>
                        <option value="general">General</option><option value="mild">Mild</option>
                        <option value="moderate">Moderate</option><option value="mature">Mature</option>
                    </select>
                </label>
                <p className="muted">Audience describes the reader; maturity sets the content ceiling. Child: general/mild. Teen: up to moderate. Adult does not imply explicit content.</p>
                <button type="button" className="secondary-button" onClick={save}>Save audience settings</button>
            </fieldset>}
            {!profile && !error && <p role="status">Loading guidance settings…</p>}
        </details>
        <p className="muted">Suggestions are advisory planning prompts using saved settings. Choosing one fills the textbox for you to edit; it does not write a scene or change Canon.</p>
        <button type="button" className="secondary-button" disabled={disabled || busy || !profile}
            onClick={suggest}>{busy ? "Working…" : "Suggest what happens next"}</button>
        <SuggestionChoices suggestions={suggestions} disabled={disabled || busy} onSelect={(text) => {
            onSelect(text); setStatus("Suggestion added to the textbox. Edit it before generating when ready.");
        }} />
        {status && <p role="status">{status}</p>}
        {error && <p role="alert" className="error">{error}
            {!profile && <button type="button" className="secondary-button" onClick={() => setRetry((value) => value + 1)}>Retry</button>}
        </p>}
    </div>;
}
