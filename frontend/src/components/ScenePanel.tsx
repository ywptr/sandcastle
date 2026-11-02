import { useState } from "react";
import { createScene, generateScene, updateScene, type Scene } from "../api/sandcastle";
import { RecordEditor, type EditorField } from "./RecordEditor";

const fields: EditorField[] = [
    { name: "title", label: "Scene title", maxLength: 255 },
    { name: "content", label: "Scene content", required: true, multiline: true },
];

interface Props {
    storyId: string;
    scenes: Scene[];
    onSaved: (scene: Scene) => void;
    onGenerated: () => Promise<void>;
}

export function ScenePanel({ storyId, scenes, onSaved, onGenerated }: Props) {
    const [editing, setEditing] = useState<string | null>(null);
    const [request, setRequest] = useState("");
    const [generating, setGenerating] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const selected = scenes.find((scene) => scene.scene_id === editing);

    async function generate() {
        if (!request.trim() || generating) return;
        setGenerating(true);
        setMessage(null);
        try {
            const result = await generateScene(storyId, request.trim());
            if (result.scene) {
                onSaved(result.scene);
                setRequest("");
                setMessage("Draft scene created. Review it before making any explicit Canon changes.");
            } else {
                setMessage(result.action.decision?.reason ?? "This request requires approval.");
            }
            await onGenerated();
        } catch (failure) {
            setMessage(failure instanceof Error ? failure.message : "Generation failed. You can create a scene manually.");
        } finally {
            setGenerating(false);
        }
    }

    return (
        <section className="panel scenes-panel" id="scenes">
            <div className="panel-heading">
                <h2>Scenes <small>({scenes.length})</small></h2>
                <button className="secondary-button" disabled={editing !== null || generating}
                    onClick={() => setEditing("new")}>Write a scene</button>
            </div>
            <p className="muted">Scenes are narrative drafts. Saving or generating prose never changes Canon automatically.</p>
            {editing !== null && (
                <RecordEditor key={editing} fields={fields}
                    initial={{ title: selected?.title ?? "", content: selected?.content ?? "" }}
                    submitLabel={editing === "new" ? "Create scene" : "Save scene"}
                    onCancel={() => setEditing(null)} onSave={async (values) => {
                        const scene = editing === "new"
                            ? await createScene(storyId, values.title || null, values.content)
                            : await updateScene(storyId, editing, values.title || null, values.content);
                        onSaved(scene);
                        setEditing(null);
                    }} />
            )}
            {scenes.length === 0 && <p>No scenes yet. Write the first scene to begin.</p>}
            <div className="scene-list">
                {scenes.map((scene) => (
                    <article className="scene" key={scene.scene_id}>
                        <div className="panel-heading">
                            <h3>{scene.sequence_number}. {scene.title || "Untitled scene"}</h3>
                            <button className="secondary-button" disabled={editing !== null || generating}
                                onClick={() => setEditing(scene.scene_id)}>Edit scene</button>
                        </div>
                        <div className="scene-content">{scene.content}</div>
                    </article>
                ))}
            </div>
            <details className="generation-options">
                <summary>Optional: generate the next scene</summary>
                <p className="muted">Uses your saved Story, Characters, Places, approved Canon, and edited previous Scenes. Available when AI writing is enabled.</p>
                <label className="generation-request">What should happen next?
                    <textarea value={request} disabled={generating} onChange={(event) => setRequest(event.target.value)} rows={3} />
                </label>
                <button className="primary-button" disabled={generating || editing !== null || !request.trim()}
                    onClick={generate}>{generating ? "Writing scene…" : "Generate scene"}</button>
                {message && <p role="status">{message}</p>}
            </details>
        </section>
    );
}
