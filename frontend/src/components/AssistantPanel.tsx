import { useI18n } from "../i18n/context";
import { useState } from "react";
import { generateScene, type Scene, type StoryWorkflow } from "../api/sandcastle";
import { NarrativeGuidance } from "./NarrativeGuidance";

export function AssistantPanel({ storyId, workflow, onSaved, onGenerated, onOpenScenes }: {
    storyId: string; workflow: StoryWorkflow | null; onSaved: (scene: Scene) => void;
    onGenerated: () => Promise<void>; onOpenScenes: () => void;
}) {
    const {t} = useI18n();
    const [request, setRequest] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState<string | null>(null);
    async function generate() {
        if (!request.trim() || busy) return;
        setBusy(true); setError(null); setStatus(null);
        try {
            const result = await generateScene(storyId, request.trim());
            if (result.scene) { onSaved(result.scene); onOpenScenes(); setRequest(""); setStatus("assistant.saved"); }
            else setStatus(result.action.decision?.reason ?? "assistant.approval");
            try { await onGenerated(); }
            catch { setError("assistant.logError"); }
        } catch { setError("assistant.failed"); }
        finally { setBusy(false); }
    }
    const enabled = !!workflow?.configuration.steps.some((s) => s.step_id === "scene_creation" && s.enabled);
    return <aside className="assistant-panel" aria-label={t("assistant.label")}>
        <div className="assistant-heading"><span className="assistant-mark" aria-hidden="true">✦</span><div><span className="eyebrow">{t("assistant.eyebrow")}</span><h2>{t("assistant.title")}</h2></div></div>
        <p>{t("assistant.intro")}</p>
        <div className="assistant-note">{t("assistant.context")}</div>
        <button type="button" className="prompt-chip" onClick={() => setRequest("Continue the story from the last scene, respecting established continuity.")}>{t("assistant.continue")}</button>
        <NarrativeGuidance storyId={storyId} capabilities={workflow?.capabilities ?? []} disabled={busy}
            suggestionsEnabled={!!workflow?.configuration.steps.some((s) => s.step_id === "narrative_guidance" && s.enabled)} onSelect={setRequest} />
        <form onSubmit={(e) => { e.preventDefault(); void generate(); }}>
            <label>{t("assistant.next")}<textarea rows={5} value={request} disabled={busy} onChange={(e) => setRequest(e.target.value)} placeholder={t("assistant.placeholder")} /></label>
            <button type="submit" className="primary-button" disabled={busy || !enabled || !request.trim()}>{t(busy ? "assistant.writing" : "assistant.generate")}</button>
        </form>
        {!enabled && <p className="muted">{t("assistant.unavailable")}</p>}
        {status && <p role="status">{t(status)}</p>}{error && <p className="error" role="alert">{t(error)}</p>}
        <small className="muted">{t("assistant.scope")}</small>
    </aside>;
}
