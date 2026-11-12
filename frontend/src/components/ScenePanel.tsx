import { useState } from "react";
import { createScene, updateScene, type Scene } from "../api/sandcastle";
import { ProductionWorkspace } from "./ProductionWorkspace";
import { RecordEditor, type EditorField } from "./RecordEditor";
const fields: EditorField[] = [
    { name: "title", label: "Scene title", maxLength: 255 },
    { name: "content", label: "Scene content", required: true, multiline: true },
];
export function ScenePanel({ storyId, scenes, onSaved, selectedId, onSelect, difficulty }: {
    storyId: string; scenes: Scene[]; onSaved: (scene: Scene) => void; selectedId: string | null; onSelect: (id: string) => void; difficulty?: string;
}) {
    const [productionOpen, setProductionOpen] = useState(false);
    const [productionSceneIds, setProductionSceneIds] = useState<string[]>([]);
    const [editing, setEditing] = useState<string | null>(null);
    const [editorIds, setEditorIds] = useState<string[]>([]);
    const selected = scenes.find((s) => s.scene_id === selectedId) ?? scenes[0];
    const [previousSelectedId, setPreviousSelectedId] = useState(selected?.scene_id);
    if (previousSelectedId !== selected?.scene_id) {
        setPreviousSelectedId(selected?.scene_id);
        setEditing(null);
        setProductionOpen(false);
    }
    function openEditor(id: string) {
        setEditorIds(ids => ids.includes(id) ? ids : [...ids, id]);
        setEditing(id);
    }
    function closeEditor(id: string) {
        setEditorIds(ids => ids.filter(value => value !== id));
        setEditing(current => current === id ? null : current);
    }
    return <section className="panel scenes-panel">
        <div className="panel-heading"><div><span className="eyebrow">Your narrative</span><h2>Scenes <small>{scenes.length}</small></h2></div>
            <button type="button" className="secondary-button" onClick={() => openEditor("new")}>+ Write a scene</button></div>
        <p className="muted">Ordered story scenes form your narrative. Episodes are a future output grouping. Saving prose never changes Canon.</p>
        <nav className="scene-picker" aria-label="Ordered scenes">{scenes.map((scene) => <button type="button" key={scene.scene_id}
            aria-current={selected?.scene_id === scene.scene_id ? "true" : undefined} onClick={() => { onSelect(scene.scene_id); setEditing(null); }}>
            <small>{String(scene.sequence_number).padStart(2, "0")}</small> {scene.title || "Untitled scene"}</button>)}</nav>
        {editorIds.map(id => {
            const scene = scenes.find(value => value.scene_id === id);
            return <div key={id} hidden={editing !== id}><RecordEditor fields={fields} initial={{ title: scene?.title ?? "", content: scene?.content ?? "" }}
                submitLabel={id === "new" ? "Create scene" : "Save scene"} onCancel={() => closeEditor(id)} onSave={async values => {
                    const saved = id === "new" ? await createScene(storyId, values.title || null, values.content)
                        : await updateScene(storyId, id, values.title || null, values.content);
                    onSaved(saved); onSelect(saved.scene_id); closeEditor(id);
                }} /></div>;
        })}
        {!editing && (selected ? <article className="scene"><div className="panel-heading"><h3>{selected.sequence_number}. {selected.title || "Untitled scene"}</h3>
                <button type="button" className="secondary-button" onClick={() => openEditor(selected.scene_id)}>Edit scene</button></div>
                <p className="eyebrow">{selected.status}</p><div className="scene-content">{selected.content}</div></article>
            : <div className="empty-state"><h3>A world waiting to unfold</h3><p>Write your opening scene, or describe it to the assistant.</p></div>)}
        {selected && <div className="scene-production"><button type="button" className="secondary-button" aria-expanded={productionOpen} onClick={() => {
            setProductionOpen(value => !value);
            setProductionSceneIds(ids => ids.includes(selected.scene_id) ? ids : [...ids, selected.scene_id]);
        }}>Production · Webtoon / Short Drama / Story Reel</button>
            {scenes.filter(scene => productionSceneIds.includes(scene.scene_id)).map(scene => <div key={scene.scene_id} hidden={!productionOpen || scene.scene_id !== selected.scene_id}>
                <ProductionWorkspace storyId={storyId} scene={scene} difficulty={difficulty} />
            </div>)}
        </div>}
    </section>;
}
