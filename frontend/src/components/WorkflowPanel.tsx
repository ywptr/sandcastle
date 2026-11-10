import { useEffect, useState } from "react";
import { listDifficulties, listWorkflowTemplates, saveStoryWorkflow, workflowStep, reviewCanonCandidate, type CanonCandidateSummary,
    type Difficulty, type StoryWorkflow, type WorkflowConfig, type WorkflowTemplate } from "../api/sandcastle";

export function WorkflowControls({ config, capabilities, definitions, onChange }: {
    config: WorkflowConfig; capabilities: string[]; definitions: StoryWorkflow["step_definitions"];
    onChange: (config: WorkflowConfig) => void;
}) {
    const can = (capability: string) => capabilities.includes(capability);
    const number = (field: "count" | "recent_scene_count", value: string) => onChange({ ...config, guidance: { ...config.guidance, [field]: Number(value) } });
    return <>
        {can("guidance_options") && <fieldset><legend>Next-scene guidance</legend>
            <label>Alternatives (1–5)<input type="number" min={1} max={5} value={config.guidance.count} onChange={(e) => number("count", e.target.value)} /></label>
            <label>Recent Scenes (1–5)<input type="number" min={1} max={5} value={config.guidance.recent_scene_count} onChange={(e) => number("recent_scene_count", e.target.value)} /></label>
        </fieldset>}
        {can("review_preferences") && <fieldset><legend>Canon checkpoint before media planning</legend>
            {([ ["require_before_media", "Require review checkpoint"], ["review_new", "Review new facts"], ["review_conflicts", "Review conflicts"], ["review_uncertain", "Review uncertain facts"] ] as const).map(([key, label]) =>
                <label key={key}><input type="checkbox" checked={config.review[key]} onChange={(e) => onChange({ ...config, review: { ...config.review, [key]: e.target.checked } })} />{label}</label>)}
            <p className="muted">Checkpoints pause planning; they never approve facts automatically.</p>
        </fieldset>}
        {can("media_options") && <fieldset><legend>Media planning</legend>
            <label>Format<select value={config.media.output_format} onChange={(e) => onChange({ ...config, media: { ...config.media, output_format: e.target.value as "image" | "webtoon" } })}><option value="image">Image</option><option value="webtoon">Webtoon</option></select></label>
            <label>Aspect ratio<input value={config.media.aspect_ratio} onChange={(e) => onChange({ ...config, media: { ...config.media, aspect_ratio: e.target.value } })} placeholder="1:1" /></label>
            <p className="muted">Storyboard planning currently uses four panels. No media is generated.</p>
        </fieldset>}
        {can("adaptation_options") && <fieldset><legend>Additional sensitivity hints</legend>
            {["violence", "intimacy", "injury", "horror", "substance_use", "other_sensitive"].map((hint) => <label key={hint}><input type="checkbox" checked={config.adaptation.sensitivity_hints.includes(hint)} onChange={(e) => onChange({ ...config, adaptation: { sensitivity_hints: e.target.checked ? [...config.adaptation.sensitivity_hints, hint] : config.adaptation.sensitivity_hints.filter((s) => s !== hint) } })} />{hint.replaceAll("_", " ")}</label>)}
            <p className="muted">Hints add conservative treatment; they cannot remove detected sensitivities.</p>
        </fieldset>}
        {can("reference_selection") && <fieldset><legend>Reference selections</legend>
            <p className="muted">Optional comma-separated IDs. Blank Character/Place selection uses all available subjects.</p>
            {(["character_ids", "place_ids", "artifact_ids"] as const).map((key) => <label key={key}>{key.replaceAll("_", " ")}<input value={config.references[key]?.join(", ") ?? ""} onChange={(e) => {
                const ids = e.target.value.split(",").map((s) => s.trim()).filter(Boolean);
                onChange({ ...config, references: { ...config.references, [key]: ids.length || key === "artifact_ids" ? ids : null } });
            }} /></label>)}
        </fieldset>}
        {can("step_configuration") && <fieldset><legend>Supported steps</legend><ol>
            {config.order.map((id, index) => {
                const definition = definitions.find((d) => d.step_id === id)!;
                const setting = config.steps.find((s) => s.step_id === id)!;
                function move(offset: number) {
                    const order = [...config.order];
                    [order[index], order[index + offset]] = [order[index + offset], order[index]];
                    onChange({ ...config, order });
                }
                return <li key={id}><label><input type="checkbox" checked={setting.enabled} disabled={definition.required || !definition.available} onChange={(e) => onChange({ ...config, steps: config.steps.map((step) => step.step_id === id ? { ...step, enabled: e.target.checked } : step) })} />{definition.label}{!definition.available ? " (deferred)" : definition.required ? " (required)" : ""}</label>
                    {can("step_ordering") && <><button type="button" className="secondary-button" aria-label={`Move ${definition.label} up`} disabled={index === 0} onClick={() => move(-1)}>↑</button><button type="button" className="secondary-button" aria-label={`Move ${definition.label} down`} disabled={index === config.order.length - 1} onClick={() => move(1)}>↓</button></>}
                </li>;
            })}
        </ol><p className="muted">Save validates dependencies. Step order is a process guide, not automatic execution.</p></fieldset>}
    </>;
}

export function CanonReviewItem({ candidate, disabled, onReview }: { candidate: CanonCandidateSummary; disabled: boolean; onReview: (approved: boolean, replace: boolean, uncertain: boolean) => void }) {
    const [replace, setReplace] = useState(false);
    const [uncertain, setUncertain] = useState(false);
    return <li><strong>{candidate.subject_name ?? candidate.subject_id ?? "Story"} · {candidate.key}: {candidate.value}</strong><blockquote>{candidate.evidence}</blockquote><p>{candidate.classification} · {candidate.reasoning}</p>
        {(candidate.classification === "conflict" || candidate.classification === "uncertain") && <label><input type="checkbox" checked={replace} disabled={disabled} onChange={(e) => setReplace(e.target.checked)} />Explicitly replace relevant current Canon if needed</label>}
        {candidate.classification === "uncertain" && <label><input type="checkbox" checked={uncertain} disabled={disabled} onChange={(e) => setUncertain(e.target.checked)} />Accept this uncertain proposal</label>}
        <button type="button" className="secondary-button" disabled={disabled || (candidate.classification === "conflict" && !replace) || (candidate.classification === "uncertain" && !uncertain)} onClick={() => onReview(true, replace, uncertain)}>Approve fact</button>
        <button type="button" className="secondary-button" disabled={disabled} onClick={() => onReview(false, false, false)}>Reject proposal</button>
    </li>;
}

export function WorkflowPanel({ workflow, onSaved, sceneId, onDomainChanged }: { workflow: StoryWorkflow; onSaved: (workflow: StoryWorkflow) => void; sceneId?: string; onDomainChanged: () => void }) {
    const [draft, setDraft] = useState(workflow);
    const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
    const [levels, setLevels] = useState<Difficulty[]>([]);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState<string | null>(null);
    const [candidates, setCandidates] = useState<CanonCandidateSummary[]>([]);
    const [retry, setRetry] = useState(0);
    const [preview, setPreview] = useState<string[]>([]);
    useEffect(() => {
        let active = true;
        Promise.all([listDifficulties(), listWorkflowTemplates()]).then(([nextLevels, nextTemplates]) => {
            if (active) { setLevels(nextLevels); setTemplates(nextTemplates); }
        }).catch((e) => { if (active) setError(e instanceof Error ? e.message : "Could not load workflow choices."); });
        return () => { active = false; };
    }, [retry]);
    const caps = levels.find((level) => level.id === draft.difficulty)?.capabilities ?? workflow.capabilities;
    const can = (cap: string) => caps.includes(cap);
    function choose(difficulty: string, template: WorkflowTemplate) {
        setDraft({ ...draft, difficulty, workflow_template_id: template.workflow_template_id, template_version: template.version, configuration: structuredClone(template.configuration) });
    }
    async function save() {
        setBusy(true); setError(null); setStatus(null);
        try {
            const saved = await saveStoryWorkflow(workflow.story_id, { difficulty: draft.difficulty, workflow_template_id: draft.workflow_template_id, template_version: draft.template_version, configuration: draft.configuration });
            setDraft(saved); onSaved(saved); setStatus("Workflow saved. No Story or media action was run.");
        } catch (e) { setError(e instanceof Error ? e.message : "Could not save workflow."); }
        finally { setBusy(false); }
    }
    async function act(id: string) {
        setBusy(true); setError(null); setPreview([]); setStatus(null);
        try {
            const result = await workflowStep<CanonCandidateSummary[] | { counts?: Record<string, number>; shots?: { visual_instruction: string }[]; requests?: { prompt: string }[] }>(workflow.story_id, id, ["canon_review", "continuity_check"].includes(id) ? undefined : sceneId);
            if (Array.isArray(result)) { const pending = result.filter((row) => row.status === "pending"); setCandidates(pending); setStatus(`${pending.length} pending Canon proposals. Review is explicit.`); }
            else if (result.counts) setPreview(Object.entries(result.counts).map(([kind, count]) => `${count} ${kind}`));
            else if (result.shots) setPreview(result.shots.map((shot) => shot.visual_instruction));
            else if (result.requests) setPreview(result.requests.map((request) => request.prompt));
        } catch (e) { setError(e instanceof Error ? e.message : "Could not preview workflow step."); }
        finally { setBusy(false); }
    }
    async function review(candidate: CanonCandidateSummary, approved: boolean, replace: boolean, uncertain: boolean) {
        setBusy(true); setError(null);
        try {
            await reviewCanonCandidate(workflow.story_id, candidate.canon_candidate_id, approved, replace, uncertain);
            setCandidates((rows) => rows.filter((row) => row.canon_candidate_id !== candidate.canon_candidate_id));
            setStatus(approved ? "Canon fact approved explicitly." : "Proposal rejected; Canon unchanged.");
            onDomainChanged();
        } catch (e) { setError(e instanceof Error ? e.message : "Could not review proposal."); }
        finally { setBusy(false); }
    }
    return <section className="panel workflow-panel"><h2>Story workflow</h2>
        <p><strong>{workflow.template_name} · v{workflow.template_version}</strong>. Difficulty controls complexity, not subscription access.</p>
        <fieldset disabled={busy || !levels.length}><legend>Workflow settings</legend>
            <label>Difficulty<select value={draft.difficulty} onChange={(e) => {
                const level = e.target.value;
                const selected = templates.find((t) => t.workflow_template_id === draft.workflow_template_id && t.version === draft.template_version)!;
                const allowed = levels.findIndex((l) => l.id === selected.difficulty_minimum) <= levels.findIndex((l) => l.id === level);
                choose(level, allowed ? selected : templates.find((t) => t.workflow_template_id === "standard-story" && t.version === 1)!);
            }}>{levels.map((level) => <option key={level.id} value={level.id}>{level.label}</option>)}</select></label>
            <p className="muted">{templates.find((t) => t.workflow_template_id === draft.workflow_template_id && t.version === draft.template_version)?.description}</p>
            <details><summary>Available capabilities</summary><ul>{caps.map((cap) => <li key={cap}>{cap.replaceAll("_", " ")}</li>)}</ul></details>
            <p className="muted">Changing difficulty or template resets draft settings to that template's defaults. Save to apply.</p>
            {can("template_selection") && <label>Template<select value={`${draft.workflow_template_id}:${draft.template_version}`} onChange={(e) => choose(draft.difficulty, templates.find((t) => `${t.workflow_template_id}:${t.version}` === e.target.value)!)}>
                {templates.filter((t) => levels.findIndex((l) => l.id === t.difficulty_minimum) <= levels.findIndex((l) => l.id === draft.difficulty)).map((t) => <option key={`${t.workflow_template_id}:${t.version}`} value={`${t.workflow_template_id}:${t.version}`}>{t.name} · v{t.version}</option>)}
            </select></label>}
            {!can("step_configuration") && <p>Choose a direction, write or generate a Scene, then review continuity. Media planning is optional and always requested separately.</p>}
            <WorkflowControls config={draft.configuration} capabilities={caps} definitions={workflow.step_definitions} onChange={(configuration) => setDraft({ ...draft, configuration })} />
            <button type="button" className="primary-button" onClick={save}>Save workflow</button>
        </fieldset>
        <p className="muted">Preview actions below use the saved workflow. Canon review and extraction remain explicit Story actions.</p>
        {([ ["canon_extraction", "Find facts in latest Scene"], ["canon_review", "Review pending facts"], ["continuity_check", "Check continuity"], ["media_adaptation", "Preview visual treatment"], ["storyboard_planning", "Preview four-panel plan"] ] as const).filter(([id]) => workflow.configuration.steps.some((s) => s.step_id === id && s.enabled) && (id === "continuity_check" || id === "canon_review" || id === "canon_extraction" || workflow.capabilities.includes("media_options"))).map(([id, label]) =>
            <button key={id} type="button" className="secondary-button" disabled={busy || (!["continuity_check", "canon_review"].includes(id) && !sceneId)} onClick={() => act(id)}>{label}</button>)}
        {candidates.length > 0 && <ol aria-label="Pending Canon review">{candidates.map((candidate) => <CanonReviewItem key={candidate.canon_candidate_id} candidate={candidate} disabled={busy} onReview={(approved, replace, uncertain) => review(candidate, approved, replace, uncertain)} />)}</ol>}
        {preview.length > 0 && <ol aria-label="Workflow preview">{preview.map((text, index) => <li key={index}>{text}</li>)}</ol>}
        {status && <p role="status">{status}</p>}{error && <p className="error" role="alert">{error}{!levels.length && <button type="button" onClick={() => setRetry((value) => value + 1)}>Retry choices</button>}</p>}
    </section>;
}
