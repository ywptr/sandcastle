import { useEffect, useState } from "react";
import { listUniverses, listUniverseMembers, listUniverseReferences, listCanonVersions, listArtifacts, listReferenceBindings, type Artifact, type ReferenceBinding } from "../api/sandcastle";

interface UniverseContext { id: string; name: string; description: string; facts: { id: string; object: string; version: string; data: Record<string, unknown> }[] }
export function UniversePanel({ storyId }: { storyId: string }) {
    const [data, setData] = useState<UniverseContext[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [retry, setRetry] = useState(0);
    useEffect(() => {
        let active = true;
        async function load() {
            const universes = await listUniverses();
            const memberships = await Promise.all(universes.map(async (u) => ({ u, members: await listUniverseMembers(u.universe_id) })));
            return Promise.all(memberships.filter(({ members }) => members.some((m) => m.story_id === storyId)).map(async ({ u }) => {
                const refs = await listUniverseReferences(u.universe_id);
                const facts = await Promise.all(refs.map(async (r) => {
                    const versions = await listCanonVersions(r.canon_object_id);
                    return { id: r.reference_id, object: r.canon_object_id, version: r.canon_version_id,
                        data: versions.find((v) => v.canon_version_id === r.canon_version_id)?.data ?? {} };
                }));
                return { id: u.universe_id, name: u.name, description: u.description, facts };
            }));
        }
        load().then((value) => { if (active) { setData(value); setError(null); } }).catch((e) => { if (active) setError(e instanceof Error ? e.message : "Could not load Universe context."); })
            .finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [storyId, retry]);
    return <section className="panel"><span className="eyebrow">Shared story world</span><h2>Universe</h2><p className="muted">Inspect membership and pinned Canon references. Local story edits do not change these shared versions.</p>
        {loading && <p role="status">Loading Universe…</p>}
        {error ? <p className="error" role="alert">{error}<button type="button" onClick={() => setRetry((v) => v + 1)}>Retry</button></p> : !loading && !data.length && <p className="empty-state">This story has no Universe membership.</p>}
        {data.map((u) => <article key={u.id}><h3>{u.name}</h3><p>{u.description}</p>{!u.facts.length && <p>No pinned Canon references.</p>}{u.facts.map((f) => <details key={f.id}><summary>Canon reference · {f.object}</summary><p>Version: {f.version}</p><pre>{JSON.stringify(f.data, null, 2)}</pre></details>)}</article>)}
    </section>;
}
export function AssetsPanel({ storyId, onWorkflow }: { storyId: string; onWorkflow: () => void }) {
    const [assets, setAssets] = useState<Artifact[]>([]);
    const [references, setReferences] = useState<ReferenceBinding[]>([]);
    const [errors, setErrors] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [retry, setRetry] = useState(0);
    useEffect(() => {
        let active = true;
        Promise.allSettled([listArtifacts(storyId), listReferenceBindings(storyId)]).then(([a, r]) => {
            if (!active) return;
            if (a.status === "fulfilled") setAssets(a.value);
            if (r.status === "fulfilled") setReferences(r.value);
            setErrors([a, r].flatMap((v) => v.status === "rejected" ? [String(v.reason)] : [])); setLoading(false);
        });
        return () => { active = false; };
    }, [storyId, retry]);
    return <section className="panel"><h2>Assets & references</h2><p className="muted">Registered media and saved reference bindings for this story. Media execution and upload are outside this workspace milestone.</p>
        <button type="button" className="secondary-button" onClick={onWorkflow}>Configure workflow references</button>
        {loading && <p role="status">Loading assets…</p>}{errors.length > 0 && <div role="alert" className="error">{errors.join("; ")}<button type="button" onClick={() => setRetry((v) => v + 1)}>Retry</button></div>}
        <h3>Registered assets</h3>{!loading && !assets.length && <p>No registered assets.</p>}<ul>{assets.map((a) => <li key={a.artifact_id}><strong>{a.display_name || a.artifact_id}</strong> · {a.source} · {a.media_type}<small>{a.artifact_id}</small></li>)}</ul>
        <h3>Saved references</h3>{!loading && !references.length && <p>No saved reference bindings.</p>}<ul>{references.map((r) => <li key={r.reference_id}>{r.label || r.role} · {r.target_type}<small>{r.artifact_id}</small></li>)}</ul>
    </section>;
}
