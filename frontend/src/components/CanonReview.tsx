import { useEffect, useState } from "react";
import { listCanonCandidates, reviewCanonCandidate, workflowStep, type CanonCandidateSummary, type StoryWorkflow } from "../api/sandcastle";
import { CanonReviewItem } from "./WorkflowPanel";

export function CanonReview({ storyId, workflow, sceneId, onChanged }: {
    storyId: string; workflow: StoryWorkflow | null; sceneId?: string; onChanged: () => void;
}) {
    const [rows, setRows] = useState<CanonCandidateSummary[]>([]);
    const [busy, setBusy] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [retry, setRetry] = useState(0);
    const [filter, setFilter] = useState("pending");
    const [status, setStatus] = useState<string | null>(null);
    useEffect(() => {
        let active = true;
        listCanonCandidates(storyId).then((data) => { if (active) { setRows(data); setError(null); } })
            .catch((e) => { if (active) setError(e instanceof Error ? e.message : "Could not load candidates."); })
            .finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [storyId, retry]);
    async function review(candidate: CanonCandidateSummary, approve: boolean, replace: boolean, uncertain: boolean) {
        setBusy(true); setError(null);
        try {
            await reviewCanonCandidate(storyId, candidate.canon_candidate_id, approve, replace, uncertain);
            setRetry((value) => value + 1); onChanged(); setStatus(approve ? "Canon approved explicitly." : "Proposal rejected; Canon unchanged.");
        } catch (e) { setError(e instanceof Error ? e.message : "Could not review proposal."); }
        finally { setBusy(false); }
    }
    async function act(id: string) {
        setBusy(true); setError(null);
        try { await workflowStep(storyId, id, id === "canon_extraction" ? sceneId : undefined); setRetry((value) => value + 1); setStatus("Continuity proposals refreshed. Review each fact before approval."); }
        catch (e) { setError(e instanceof Error ? e.message : "Could not run Canon action."); }
        finally { setBusy(false); }
    }
    const shown = rows.filter((c) => filter === "all" || c.status === filter);
    return <section className="panel"><h2>Canon candidates</h2><p className="muted">Proposed facts need your explicit approval. Evidence and uncertainty stay visible.</p>
        <div className="button-row">{[["canon_extraction", "Find facts in selected scene"], ["continuity_check", "Review continuity"]].map(([id, label]) =>
            <button type="button" className="secondary-button" key={id} disabled={busy || (id === "canon_extraction" && !sceneId) || !workflow?.configuration.steps.some((s) => s.step_id === id && s.enabled)} onClick={() => act(id)}>{label}</button>)}</div>
        <label>Candidate status<select value={filter} onChange={(e) => setFilter(e.target.value)}>{["pending", "approved", "rejected", "all"].map((s) => <option key={s}>{s}</option>)}</select></label>
        {loading && <p role="status">Loading candidates…</p>}
        {!loading && !error && !shown.length && <p className="empty-state">No {filter === "all" ? "" : filter} candidates. Extract facts from a scene when you’re ready.</p>}
        <ol className="candidate-list">{shown.map((c) => c.status === "pending" ? <CanonReviewItem key={c.canon_candidate_id} candidate={c} disabled={busy} onReview={(a, r, u) => review(c, a, r, u)} />
            : <li key={c.canon_candidate_id}><strong>{c.key}: {c.value}</strong><blockquote>{c.evidence}</blockquote><p>{c.status} · {c.classification} · {c.reasoning}</p></li>)}</ol>
        {status && <p role="status">{status}</p>}{error && <p className="error" role="alert">{error}<button type="button" disabled={busy} onClick={() => setRetry((v) => v + 1)}>Retry loading candidates</button></p>}
    </section>;
}
