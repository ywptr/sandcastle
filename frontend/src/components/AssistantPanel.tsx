import { useI18n } from "../i18n/context";
import { useState } from "react";
import { generateScene, type Scene, type StoryWorkflow } from "../api/sandcastle";
import { workspaceCopy } from "./studio/workspaceCopy";
import { NarrativeGuidance } from "./NarrativeGuidance";

export function AssistantPanel({ storyId, storyLanguage, workflow, onSaved, onGenerated, onOpenScenes }: {
    storyId: string; storyLanguage?: string | null; workflow: StoryWorkflow | null; onSaved: (scene: Scene) => void;
    onGenerated: () => Promise<void>; onOpenScenes: () => void;
}) {
    const {t, locale} = useI18n();
    const copy = workspaceCopy[locale];
    const [receipt, setReceipt] = useState<{prompt:string;scene?:Scene;reason?:string} | null>(null);
    const [request, setRequest] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState<string | null>(null);
    async function generate() {
        if (!request.trim() || busy) return;
        setBusy(true); setError(null); setStatus(null);
        try {
            const result = await generateScene(storyId, request.trim());
            setReceipt({prompt:request.trim(),scene:result.scene ?? undefined,reason:result.action.decision?.reason});
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
        <div className="assistant-guidance-log" role="region" aria-label={copy.scope} tabIndex={0}><div className="assistant-introduction"><span className="eyebrow">{copy.scope}</span><p>{t("assistant.intro")}</p></div>
        <div className="assistant-note"><strong>{copy.context}</strong><p>{t("assistant.context")}</p></div>
        <button type="button" className="prompt-chip" disabled={busy} onClick={() => setRequest("Continue the story from the last scene, respecting established continuity.")}>{t("assistant.continue")}</button>
        <NarrativeGuidance storyId={storyId} capabilities={workflow?.capabilities ?? []} disabled={busy}
            suggestionsEnabled={!!workflow?.configuration.steps.some((s) => s.step_id === "narrative_guidance" && s.enabled)} onSelect={setRequest} />
        {receipt && <section className="assistant-receipt" aria-label={copy.session}>
            <div className="assistant-user-bubble"><strong>{copy.submitted}</strong><p>{receipt.prompt}</p></div>
            <div className="assistant-result-bubble"><strong>{receipt.scene ? copy.result : copy.decision}</strong><p>{receipt.scene?.title || receipt.reason || t("assistant.approval")}</p>{receipt.scene && <><p>{receipt.scene.content}</p><button type="button" className="secondary-button" onClick={onOpenScenes}>{t("workspace.openEditor")}</button></>}</div>
            <p className="muted">{copy.session}</p>
        </section>}
        <small className="muted">{t("assistant.scope")}</small></div>
        <form onSubmit={(e) => { e.preventDefault(); void generate(); }}>
            <span className="eyebrow">{copy.prompt}</span><label>{t("assistant.next")}<textarea aria-label={t("assistant.next")} rows={5} value={request} disabled={busy} onChange={(e) => setRequest(e.target.value)} placeholder={t("assistant.placeholder")} /></label>
            <p className="assistant-language"><strong>{copy.language}:</strong> {storyLanguage ? t(`language.${storyLanguage}`) : t("common.notSet")}</p>
            <button type="submit" className="primary-button" disabled={busy || !enabled || !request.trim()}>{t(busy ? "assistant.writing" : "assistant.generate")}</button>
        </form>
        {!enabled && <p className="muted">{t("assistant.unavailable")}</p>}
        {status && <p role="status">{t(status)}</p>}{error && <p className="error" role="alert">{t(error)}</p>}
    </aside>;
}
