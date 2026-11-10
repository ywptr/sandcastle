import { useEffect, useState } from "react";
import { ApiError, type Scene } from "../api/sandcastle";
import { approveProduction, compileProduction, listProductions, translateProduction,
    type ApprovedProduction, type ProductionBeat, type ProductionManifest, type ProductionPlan, type TargetFormat } from "../api/production";
import { formatNames, moveBeat, productionBeats, replaceBeats, sceneDigest } from "../api/productionEditing";

const framing = ["wide", "full", "medium", "close_up", "detail", "overhead"];
function errorMessage(error: unknown): string {
    if (error instanceof ApiError && error.status === 503) return "Production translation is unavailable. Configure an AI provider, or retry if the service is temporarily unavailable.";
    if (error instanceof ApiError && error.status === 409) return error.message;
    if (error instanceof ApiError && error.status === 422) return error.message;
    return "Production planning could not complete. Your Scene and previously approved plans are unchanged.";
}

function BeatEditor({ beat, index, plan, disabled, advanced, onChange, onMove, onRemove }: {
    beat: ProductionBeat; index: number; plan: ProductionPlan; disabled: boolean; advanced: boolean;
    onChange: (value: ProductionBeat) => void; onMove: (offset: number) => void; onRemove: () => void;
}) {
    const label = plan.target_format === "webtoon" ? "Panel" : plan.target_format === "short_drama" ? "Shot" : "Beat";
    function text(field: string, title: string, maxLength = 1000, required = false) {
        const value = (beat as unknown as Record<string, unknown>)[field];
        return <label key={field}>{title}<textarea rows={2} maxLength={maxLength} required={required} value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange({ ...beat, [field]: e.target.value })} /></label>;
    }
    const context = plan.continuity_context;
    return <article className="production-beat"><fieldset disabled={disabled}><legend>{label} {index + 1}</legend>
        <div className="button-row"><button type="button" className="secondary-button" aria-label={`Move ${label.toLowerCase()} ${index + 1} up`} disabled={index === 0} onClick={() => onMove(-1)}>↑</button><button type="button" className="secondary-button" aria-label={`Move ${label.toLowerCase()} ${index + 1} down`} disabled={index === productionBeats(plan.production).length - 1} onClick={() => onMove(1)}>↓</button><button type="button" className="secondary-button" disabled={productionBeats(plan.production).length === 1} onClick={onRemove}>Remove {label.toLowerCase()} {index + 1}</button></div>
        {text("narrative_purpose", "Narrative purpose", 2000, true)}
        {text("visual_description", "Visual description", 2000, true)}
        {"framing" in beat && <label>Framing<select value={beat.framing} onChange={(e) => onChange({ ...beat, framing: e.target.value as typeof beat.framing })}>{framing.map((s) => <option key={s}>{s}</option>)}</select></label>}
        {"shot_scale" in beat && <><label>Shot scale<select value={beat.shot_scale} onChange={(e) => onChange({ ...beat, shot_scale: e.target.value as typeof beat.shot_scale })}>{framing.map((s) => <option key={s}>{s}</option>)}</select></label>
            <label>Estimated duration (seconds)<input type="number" required min={1} max={30} step={1} value={beat.estimated_duration} onChange={(e) => onChange({ ...beat, estimated_duration: Number(e.target.value) })} /></label></>}
        {"duration" in beat && <label>Beat duration (seconds)<input type="number" required min={1} max={15} step={1} value={beat.duration} onChange={(e) => onChange({ ...beat, duration: Number(e.target.value) })} /></label>}
        {"dialogue" in beat && text("dialogue", "Dialogue")}{"caption" in beat && text("caption", "Caption")}
        {"on_screen_text" in beat && text("on_screen_text", "On-screen text")}{"voiceover" in beat && text("voiceover", "Voiceover")}
        {"transition_hint" in beat && text("transition_hint", "Transition")}
        <details open={advanced || undefined}><summary>Identity, source & production details</summary>
            {text("source_excerpt", "Exact source excerpt", 1000, true)}
            <fieldset><legend>Characters</legend>{context.characters.length ? context.characters.map((c) => <label className="checkbox-label" key={c.character_id}><input type="checkbox" checked={beat.character_ids.includes(c.character_id)} onChange={(e) => onChange({ ...beat, character_ids: e.target.checked ? [...beat.character_ids, c.character_id] : beat.character_ids.filter((id) => id !== c.character_id) })} />{c.name}</label>) : <p>No selected Character records.</p>}</fieldset>
            <fieldset><legend>Places</legend>{context.places.length ? context.places.map((p) => <label className="checkbox-label" key={p.place_id}><input type="checkbox" checked={beat.place_ids.includes(p.place_id)} onChange={(e) => onChange({ ...beat, place_ids: e.target.checked ? [...beat.place_ids, p.place_id] : beat.place_ids.filter((id) => id !== p.place_id) })} />{p.name}</label>) : <p>No selected Place records.</p>}</fieldset>
            {"camera_direction" in beat && <>{text("camera_direction", "Camera direction")}{text("performance_direction", "Performance direction")}{text("audio_or_ambience", "Audio / ambience")}</>}
            <label>Continuity notes (one per line)<textarea rows={2} maxLength={10000} value={beat.continuity_notes.join("\n")} onChange={(e) => onChange({ ...beat, continuity_notes: e.target.value.split("\n").filter(Boolean) })} /></label>
            {advanced && <fieldset><legend>Artifact references (metadata only)</legend>{context.references.filter((r, i, rows) => r.kind.includes("artifact") && rows.findIndex((v) => v.reference_id === r.reference_id) === i).map((r) => <label className="checkbox-label" key={r.reference_id}><input type="checkbox" checked={beat.artifact_ids.includes(r.reference_id)} onChange={(e) => onChange({ ...beat, artifact_ids: e.target.checked ? [...beat.artifact_ids, r.reference_id] : beat.artifact_ids.filter((id) => id !== r.reference_id) })} />{r.role || "Reference"} · {r.reference_id}</label>)}<p className="muted">No media is fetched or copied.</p></fieldset>}
        </details>
    </fieldset></article>;
}

export function ProductionWorkspace({ storyId, scene, difficulty = "easy" }: { storyId: string; scene: Scene; difficulty?: string }) {
    const [format, setFormat] = useState<TargetFormat>("webtoon");
    const [instruction, setInstruction] = useState("");
    const [plan, setPlan] = useState<ProductionPlan | null>(null);
    const [manifest, setManifest] = useState<ProductionManifest | null>(null);
    const [history, setHistory] = useState<ApprovedProduction[]>([]);
    const [historyLoading, setHistoryLoading] = useState(true);
    const [historyError, setHistoryError] = useState(false);
    const [reload, setReload] = useState(0);
    const [busy, setBusy] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState<string | null>(null);
    const [reviewOpen, setReviewOpen] = useState(difficulty !== "easy");
    const [inspecting, setInspecting] = useState(false);
    const [viewing, setViewing] = useState<ApprovedProduction | null>(null);
    const [currentDigest, setCurrentDigest] = useState<string | null>(null);
    const [contextStale, setContextStale] = useState(false);
    const [dirty, setDirty] = useState(false);
    const advanced = difficulty === "difficult" || difficulty === "impossible";
    useEffect(() => {
        let active = true;
        listProductions(storyId, scene.scene_id).then((rows) => { if (active) { setHistory(rows); setHistoryError(false); } })
            .catch(() => { if (active) setHistoryError(true); }).finally(() => { if (active) setHistoryLoading(false); });
        return () => { active = false; };
    }, [storyId, scene.scene_id, scene.updated_at, reload]);
    useEffect(() => {
        let active = true;
        sceneDigest({ content: scene.content, title: scene.title }).then((digest) => { if (active) setCurrentDigest(digest); }).catch(() => { if (active) setCurrentDigest(null); });
        return () => { active = false; };
    }, [scene.content, scene.title]);
    const selectedHistory = history.find((row) => row.adaptation_id === viewing?.adaptation_id);
    const sourceStale = !!plan && ((!!currentDigest && currentDigest !== plan.source_digest) || !!selectedHistory?.source_changed);
    const stale = sourceStale || contextStale || !!selectedHistory?.context_changed;
    function changed(next: ProductionPlan) { setPlan({ ...next, compiled_instructions: [] }); setManifest(null); setDirty(true); setStatus(null); }
    async function translate() {
        if (busy) return; setBusy("translate"); setError(null); setStatus(null);
        try {
            const next = await translateProduction(storyId, scene.scene_id, format, instruction.trim() || null);
            setPlan(next); setManifest(null); setViewing(null); setContextStale(false); setDirty(false); setInspecting(false); setReviewOpen(difficulty !== "easy");
            setStatus(`Scene prepared for ${formatNames[next.target_format]}. Review before approval.`);
        } catch (failure) { setError(errorMessage(failure)); } finally { setBusy(null); }
    }
    async function inspect() {
        if (!plan || busy) return;
        setBusy("compile"); setError(null);
        try { const compiled = await compileProduction(storyId, scene.scene_id, plan); setPlan(compiled.plan); setManifest(compiled.manifest); setDirty(false); setInspecting(true); }
        catch (failure) { setError(errorMessage(failure)); if (failure instanceof ApiError && failure.status === 409) setContextStale(true); }
        finally { setBusy(null); }
    }
    async function approve() {
        if (!plan || busy || stale || viewing) return;
        setBusy("approve"); setError(null); setStatus(null);
        try {
            const saved = await approveProduction(storyId, scene.scene_id, plan);
            setPlan(saved.plan); setManifest(saved.manifest); setViewing(saved); setDirty(false); setReload((v) => v + 1);
            setStatus(`Approved revision ${saved.revision} saved. No media was generated.`);
        } catch (failure) { setError(errorMessage(failure)); if (failure instanceof ApiError && failure.status === 409) setContextStale(true); }
        finally { setBusy(null); }
    }
    return <section className="production-workspace" aria-label="Scene production">
        <h3>Turn this Scene into</h3><div className="format-choices" aria-label="Production format">{(Object.keys(formatNames) as TargetFormat[]).map((f) => <button type="button" key={f} className="secondary-button" aria-pressed={format === f} disabled={!!busy} onClick={() => setFormat(f)}>{formatNames[f]}</button>)}</div>
        <label>Optional production direction<textarea rows={2} maxLength={1000} value={instruction} disabled={!!busy} onChange={(e) => setInstruction(e.target.value)} /></label>
        <button type="button" className="primary-button" disabled={!!busy} onClick={translate}>{busy === "translate" ? "Translating narrative…" : plan ? "Create new adaptation" : "Prepare production plan"}</button>
        <p className="muted">One text-model interpretation. Review and approve an editable plan; images and video are not generated here.</p>
        {busy && <p role="status">{busy === "translate" ? "Interpreting the narrative and preparing the complete plan…" : "Working…"}</p>}
        {error && <p className="error" role="alert">{error}</p>}{status && <p role="status">{status}</p>}
        {plan && <form onSubmit={(e) => { e.preventDefault(); void approve(); }}>
            <div className="context-note"><h3>{formatNames[plan.target_format]} · {productionBeats(plan.production).length} {plan.target_format === "webtoon" ? "panels" : plan.target_format === "short_drama" ? "shots" : "beats"}</h3>
                <p>{plan.summary}</p><p>Characters: {new Set(productionBeats(plan.production).flatMap((b) => b.character_ids)).size} · Places: {plan.continuity_context.places.map((p) => p.name).join(", ") || "Unspecified"}</p>
                {plan.production.target_format !== "webtoon" && <p>Estimated total: {plan.production.target_duration_seconds} seconds · planning estimate</p>}
                <p>Continuity: {plan.warnings.length ? `${plan.warnings.length} ${plan.warnings.length === 1 ? "thing" : "things"} to review` : "Context attached; human review required"}</p>
                {viewing && <p><strong>Approved revision {viewing.revision} · immutable snapshot</strong></p>}
            </div>
            {stale && <p className="error" role="alert">{sourceStale ? "Scene has changed since this production plan was created or approved." : "Story, Canon, references, guidance, or workflow context changed."} Create a new adaptation. Historical approval remains unchanged.</p>}
            {plan.warnings.length > 0 && <aside aria-label="Production warnings"><h4>{plan.warnings.length} {plan.warnings.length === 1 ? "thing" : "things"} to review</h4><ul>{plan.warnings.map((w, i) => <li key={`${w.code}:${i}`}>{w.message}</li>)}</ul></aside>}
            <button type="button" className="secondary-button" aria-expanded={reviewOpen} onClick={() => setReviewOpen((v) => !v)}>Review plan</button>
            {reviewOpen && <fieldset disabled={!!busy || !!viewing} className="production-review"><legend>Structured production plan</legend>
                <label>Plan summary<textarea required rows={2} maxLength={2000} value={plan.summary} onChange={(e) => changed({ ...plan, summary: e.target.value })} /></label>
                {plan.production.target_format === "webtoon" && <><label>Reading order<select value={plan.production.reading_order} onChange={(e) => { if (plan.production.target_format === "webtoon") changed({ ...plan, production: { ...plan.production, reading_order: e.target.value as typeof plan.production.reading_order } }); }}><option value="top_to_bottom">Top to bottom</option><option value="left_to_right">Left to right</option><option value="right_to_left">Right to left</option></select></label><label>Layout hint<textarea maxLength={1000} value={plan.production.layout_hint} onChange={(e) => { if (plan.production.target_format === "webtoon") changed({ ...plan, production: { ...plan.production, layout_hint: e.target.value } }); }} /></label></>}
                {plan.production.target_format === "short_drama" && <label>Overall audio direction<textarea maxLength={1000} value={plan.production.audio_direction} onChange={(e) => { if (plan.production.target_format === "short_drama") changed({ ...plan, production: { ...plan.production, audio_direction: e.target.value } }); }} /></label>}
                {plan.production.target_format === "story_reel" && <>{(["narration_text_strategy", "visual_strategy"] as const).map((field) => <label key={field}>{field.replaceAll("_", " ")}<textarea required maxLength={2000} value={plan.production.target_format === "story_reel" ? plan.production[field] : ""} onChange={(e) => { if (plan.production.target_format === "story_reel") changed({ ...plan, production: { ...plan.production, [field]: e.target.value } }); }} /></label>)}</>}
                {productionBeats(plan.production).map((beat, index, beats) => <BeatEditor key={index} beat={beat} index={index} plan={plan} disabled={!!busy || !!viewing} advanced={advanced}
                    onChange={(value) => changed(replaceBeats(plan, beats.map((b, i) => i === index ? value : b)))} onMove={(offset) => changed(moveBeat(plan, index, offset))}
                    onRemove={() => changed(replaceBeats({ ...plan, overrides: plan.overrides.filter((o) => o.beat_number !== index + 1).map((o) => ({ ...o, beat_number: o.beat_number > index + 1 ? o.beat_number - 1 : o.beat_number })) }, beats.filter((_, i) => i !== index)))} />)}
                <button type="button" className="secondary-button" disabled={productionBeats(plan.production).length >= (plan.target_format === "webtoon" ? 12 : plan.target_format === "short_drama" ? 24 : 20)} onClick={() => { const beats = productionBeats(plan.production); changed(replaceBeats(plan, [...beats, structuredClone(beats.at(-1)!)])); }}>Add {plan.target_format === "webtoon" ? "panel" : plan.target_format === "short_drama" ? "shot" : "beat"} viewpoint</button>
            </fieldset>}
            <div className="button-row"><button type="button" className="secondary-button" disabled={!!busy || (stale && !viewing)} onClick={() => { if (viewing) setInspecting((v) => !v); else void inspect(); }}>Generation instructions</button>
                {!viewing && <button type="submit" className="primary-button" disabled={!!busy || stale}>Approve production plan</button>}
                {viewing && <button type="button" className="secondary-button" disabled={stale || !!busy} onClick={() => { setViewing(null); setStatus("Editing a copy. Approval will create a new revision."); setReviewOpen(true); }}>Edit as new revision</button>}</div>
            {dirty && <p className="muted">Plan edited. Compile instructions again to inspect the current output; approval also recompiles on the server.</p>}
            {inspecting && !dirty && <section aria-label="Generation instructions"><h4>Provider-neutral generation instructions</h4>{plan.compiled_instructions.map((item) => <details key={item.beat_number} open><summary>Beat {item.beat_number}{item.override ? " · explicit override" : " · compiled"}</summary><pre>{item.compiled}</pre>{item.override && <><strong>Explicit override (stored separately)</strong><pre>{item.override}</pre><details><summary>Effective instruction with authoritative context</summary><pre>{item.effective}</pre></details></>}</details>)}</section>}
            {advanced && <details className="override-editor"><summary>Explicit presentation overrides</summary><p className="muted">Overrides are separate from compiler output. Canon, identity, and audience constraints remain attached.</p><fieldset disabled={!!busy || !!viewing}>{productionBeats(plan.production).map((_, i) => <label key={i}>Beat {i + 1} presentation override<textarea rows={2} maxLength={2000} value={plan.overrides.find((o) => o.beat_number === i + 1)?.instruction ?? ""} onChange={(e) => changed({ ...plan, overrides: [...plan.overrides.filter((o) => o.beat_number !== i + 1), ...(e.target.value.trim() ? [{ beat_number: i + 1, instruction: e.target.value }] : [])] })} /></label>)}</fieldset></details>}
            {difficulty === "impossible" && <><details><summary>Full structured plan</summary><pre>{JSON.stringify(plan, null, 2)}</pre></details><details><summary>Provider-neutral generation manifest</summary>{manifest ? <pre>{JSON.stringify(manifest, null, 2)}</pre> : <p>Use Generation instructions to compile the current manifest.</p>}</details></>}
        </form>}
        <section className="production-history"><div className="panel-heading"><h4>Approved production history</h4><button type="button" className="secondary-button" onClick={() => setReload((v) => v + 1)}>Refresh history</button></div>
            {historyLoading && <p role="status">Loading approved plans…</p>}{historyError && <p role="alert" className="error">Could not load production history. Use Refresh history to retry.</p>}{!historyLoading && !historyError && !history.length && <p>No approved production plans for this Scene yet.</p>}
            {history.map((row) => <button type="button" className="history-item secondary-button" disabled={!!busy} key={row.adaptation_id} onClick={() => { setPlan(structuredClone(row.plan)); setManifest(row.manifest); setViewing(row); setFormat(row.plan.target_format); setContextStale(row.context_changed); setDirty(false); setInspecting(false); setReviewOpen(difficulty !== "easy"); setStatus(null); setError(null); }}>{formatNames[row.plan.target_format]} · revision {row.revision} · {new Date(row.approved_at).toLocaleString()}{row.source_changed ? " · Scene changed" : row.context_changed ? " · Context changed" : ""}</button>)}
        </section>
    </section>;
}
