import { useState } from "react";
import { createScene, updateScene, type Scene } from "../api/sandcastle";
import { RecordEditor, type EditorField } from "./RecordEditor";
const fields: EditorField[] = [
    { name: "title", label: "Scene title", maxLength: 255 },
    { name: "content", label: "Scene content", required: true, multiline: true },
];
export function ScenePanel({ storyId, scenes, onSaved, selectedId, onSelect }: {
    storyId: string; scenes: Scene[]; onSaved: (scene: Scene) => void; selectedId: string | null; onSelect: (id: string) => void;
}) {
    const [editing, setEditing] = useState<string | null>(null);
    const selected = scenes.find((s) => s.scene_id === selectedId) ?? scenes[0];
    const editingScene = scenes.find((s) => s.scene_id === editing);
    return <section className="panel scenes-panel">
        <div className="panel-heading"><div><span className="eyebrow">Your narrative</span><h2>Scenes <small>{scenes.length}</small></h2></div>
            <button type="button" className="secondary-button" onClick={() => setEditing("new")}>+ Write a scene</button></div>
        <p className="muted">Ordered story scenes form your narrative. Episodes are a future output grouping. Saving prose never changes Canon.</p>
        <nav className="scene-picker" aria-label="Ordered scenes">{scenes.map((scene) => <button type="button" key={scene.scene_id}
            aria-current={selected?.scene_id === scene.scene_id ? "true" : undefined} onClick={() => { onSelect(scene.scene_id); setEditing(null); }}>
            <small>{String(scene.sequence_number).padStart(2, "0")}</small> {scene.title || "Untitled scene"}</button>)}</nav>
        {editing ? <RecordEditor key={editing} fields={fields} initial={{ title: editingScene?.title ?? "", content: editingScene?.content ?? "" }}
            submitLabel={editing === "new" ? "Create scene" : "Save scene"} onCancel={() => setEditing(null)} onSave={async (values) => {
                const saved = editing === "new" ? await createScene(storyId, values.title || null, values.content)
                    : await updateScene(storyId, editing, values.title || null, values.content);
                onSaved(saved); onSelect(saved.scene_id); setEditing(null);
            }} /> : selected ? <article className="scene"><div className="panel-heading"><h3>{selected.sequence_number}. {selected.title || "Untitled scene"}</h3>
                <button type="button" className="secondary-button" onClick={() => setEditing(selected.scene_id)}>Edit scene</button></div>
                <p className="eyebrow">{selected.status}</p><div className="scene-content">{selected.content}</div></article>
            : <div className="empty-state"><h3>A world waiting to unfold</h3><p>Write your opening scene, or describe it to the assistant.</p></div>}
    </section>;
}
