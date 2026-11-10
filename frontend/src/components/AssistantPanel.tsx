import { useState } from "react";
import { generateScene, type Scene, type StoryWorkflow } from "../api/sandcastle";
import { NarrativeGuidance } from "./NarrativeGuidance";

export function AssistantPanel({ storyId, workflow, onSaved, onGenerated, onOpenScenes }: {
    storyId: string; workflow: StoryWorkflow | null; onSaved: (scene: Scene) => void;
    onGenerated: () => Promise<void>; onOpenScenes: () => void;
}) {
    const [request, setRequest] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState<string | null>(null);
    async function generate() {
        if (!request.trim() || busy) return;
        setBusy(true); setError(null); setStatus(null);
        try {
            const result = await generateScene(storyId, request.trim());
            if (result.scene) { onSaved(result.scene); onOpenScenes(); setRequest(""); setStatus("Scene drafted. Review and edit it in Scenes. Canon remains unchanged."); }
            else setStatus(result.action.decision?.reason ?? "This request requires approval.");
            try { await onGenerated(); }
            catch { setError("The writing result is saved, but the Authority log could not refresh. Reopen the story to retry the log read."); }
        } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not generate. Your prompt is ready to retry."); }
        finally { setBusy(false); }
    }
    const enabled = !!workflow?.configuration.steps.some((s) => s.step_id === "scene_creation" && s.enabled);
    return <aside className="assistant-panel" aria-label="Creative assistant">
        <div className="assistant-heading"><span className="assistant-mark" aria-hidden="true">✦</span><div><span className="eyebrow">Creative companion</span><h2>Let’s shape your story</h2></div></div>
        <p>Start with a direction. We’ll turn it into a scene you can make your own.</p>
        <div className="assistant-note">Writing uses your saved story details, Characters, Places, approved Canon, and previous Scenes.</div>
        <button type="button" className="prompt-chip" onClick={() => setRequest("Continue the story from the last scene, respecting established continuity.")}>Continue the story ↗</button>
        <NarrativeGuidance storyId={storyId} capabilities={workflow?.capabilities ?? []} disabled={busy}
            suggestionsEnabled={!!workflow?.configuration.steps.some((s) => s.step_id === "narrative_guidance" && s.enabled)} onSelect={setRequest} />
        <form onSubmit={(e) => { e.preventDefault(); void generate(); }}>
            <label>What should happen next?<textarea rows={5} value={request} disabled={busy} onChange={(e) => setRequest(e.target.value)} placeholder="Describe the next moment in your story…" /></label>
            <button type="submit" className="primary-button" disabled={busy || !enabled || !request.trim()}>{busy ? "Writing scene…" : "Generate scene →"}</button>
        </form>
        {!enabled && <p className="muted">Load a workflow with Scene creation enabled to generate. Manual editing remains available in Scenes.</p>}
        {status && <p role="status">{status}</p>}{error && <p className="error" role="alert">{error}</p>}
        <small className="muted">Focused writing tools. General chat is a future capability; this area is separate from your saved story data.</small>
    </aside>;
}
