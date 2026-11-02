import { useEffect, useState } from "react";
import {
    createCanonEntry, listActions, listCanon, listCharacters, listPlaces, listScenes,
    saveCharacter, savePlace, updateCanon, updateStory,
    type CanonEntry, type Character, type Place, type Scene, type Story, type StoryAction,
} from "../api/sandcastle";
import { RecordEditor, type EditorField } from "./RecordEditor";
import { WorldPanel } from "./WorldPanel";
import { ScenePanel } from "./ScenePanel";

const characterFields: EditorField[] = [
    { name: "name", label: "Name", required: true, maxLength: 255 },
    ...["description", "appearance", "outfit", "personality"].map((name) => ({
        name, label: name[0].toUpperCase() + name.slice(1), multiline: true,
    })),
];
const placeFields: EditorField[] = [
    characterFields[0],
    ...["description", "appearance", "atmosphere"].map((name) => ({
        name, label: name[0].toUpperCase() + name.slice(1), multiline: true,
    })),
];
const canonFields: EditorField[] = [
    { name: "type", label: "Type (e.g. character, location, rule)", required: true, maxLength: 50 },
    { name: "key", label: "Key (e.g. character.mara.eye_color)", required: true, maxLength: 255 },
    { name: "value", label: "Authoritative fact", required: true, multiline: true },
    { name: "status", label: "Status", options: ["approved", "superseded"] },
];
const storyFields: EditorField[] = [
    { name: "title", label: "Title", required: true, maxLength: 255 },
    { name: "premise", label: "Premise", multiline: true },
    { name: "objective", label: "Objective", multiline: true },
];

function upsert<T>(items: T[], item: T, id: (entry: T) => string): T[] {
    return items.some((entry) => id(entry) === id(item))
        ? items.map((entry) => id(entry) === id(item) ? item : entry) : [...items, item];
}

interface Props {
    story: Story;
    onStoryUpdated: (story: Story) => void;
}

export function StoryWorkspace({ story, onStoryUpdated }: Props) {
    const [characters, setCharacters] = useState<Character[]>([]);
    const [places, setPlaces] = useState<Place[]>([]);
    const [canon, setCanon] = useState<CanonEntry[]>([]);
    const [scenes, setScenes] = useState<Scene[]>([]);
    const [actions, setActions] = useState<StoryAction[]>([]);
    const [editingStory, setEditingStory] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [reload, setReload] = useState(0);
    const storyId = story.story_id;

    useEffect(() => {
        let active = true;
        Promise.all([listCharacters(storyId), listPlaces(storyId), listCanon(storyId), listScenes(storyId), listActions(storyId)])
            .then(([nextCharacters, nextPlaces, nextCanon, nextScenes, nextActions]) => {
                if (!active) return;
                setCharacters(nextCharacters);
                setPlaces(nextPlaces);
                setCanon(nextCanon);
                setScenes(nextScenes);
                setActions(nextActions);
                setError(null);
            }).catch((failure) => {
                if (active) setError(failure instanceof Error ? failure.message : "Could not load story world.");
            }).finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [storyId, reload]);

    if (loading) return <main className="workspace" role="status">Loading story world…</main>;
    if (error) return <main className="workspace"><p className="error" role="alert">{error}</p>
        <button className="secondary-button" onClick={() => { setLoading(true); setReload((value) => value + 1); }}>Retry</button></main>;

    return (
        <main className="workspace">
            <header className="story-header">
                <div className="panel-heading"><h1>{story.title}</h1>
                    <button className="secondary-button" disabled={editingStory} onClick={() => setEditingStory(true)}>Edit story</button></div>
                <p>{story.premise || "Add a premise to shape your story."}</p>
                {story.objective && <p><strong>Objective:</strong> {story.objective}</p>}
                {editingStory && <RecordEditor fields={storyFields}
                    initial={{ title: story.title, premise: story.premise ?? "", objective: story.objective ?? "" }}
                    onCancel={() => setEditingStory(false)} onSave={async (values) => {
                        const updated = await updateStory(storyId, { title: values.title, premise: values.premise, objective: values.objective });
                        onStoryUpdated(updated);
                        setEditingStory(false);
                    }} />}
            </header>
            <nav className="workspace-nav" aria-label="Story workspace">
                <a href="#characters">Characters</a><a href="#places">Places</a><a href="#canon">Canon</a><a href="#scenes">Scenes</a>
            </nav>
            <div className="workspace-grid">
                <WorldPanel title="Characters" singular="character" fields={characterFields}
                    records={characters.map((item) => ({ id: item.character_id, title: item.name,
                        values: { name: item.name, description: item.description, appearance: item.appearance, outfit: item.outfit, personality: item.personality } }))}
                    onSave={async (id, values) => {
                        const item = await saveCharacter(storyId, id, { name: values.name, description: values.description,
                            appearance: values.appearance, outfit: values.outfit, personality: values.personality });
                        setCharacters((current) => upsert(current, item, (entry) => entry.character_id));
                    }} />
                <WorldPanel title="Places" singular="place" fields={placeFields}
                    records={places.map((item) => ({ id: item.place_id, title: item.name,
                        values: { name: item.name, description: item.description, appearance: item.appearance, atmosphere: item.atmosphere } }))}
                    onSave={async (id, values) => {
                        const item = await savePlace(storyId, id, { name: values.name, description: values.description,
                            appearance: values.appearance, atmosphere: values.atmosphere });
                        setPlaces((current) => upsert(current, item, (entry) => entry.place_id));
                    }} />
            </div>
            <div className="workspace-section">
                <p className="muted">Canon records authoritative continuity. Character, Place, and Scene edits do not silently change these facts.</p>
                <WorldPanel title="Canon" singular="canon fact" fields={canonFields}
                    createFields={canonFields.filter((field) => field.name !== "status")}
                    records={canon.map((item) => ({ id: item.canon_entry_id, title: item.key,
                        values: { type: item.type, key: item.key, value: item.value, status: item.status } }))}
                    onSave={async (id, values) => {
                        const input = { type: values.type, key: values.key, value: values.value };
                        const item = id ? await updateCanon(storyId, id, { ...input, status: values.status === "superseded" ? "superseded" : "approved" })
                            : await createCanonEntry(storyId, input.type, input.key, input.value);
                        setCanon((current) => upsert(current, item, (entry) => entry.canon_entry_id));
                    }} />
            </div>
            <ScenePanel storyId={storyId} scenes={scenes} onSaved={(scene) => {
                setScenes((current) => upsert(current, scene, (entry) => entry.scene_id).sort((a, b) => a.sequence_number - b.sequence_number));
            }} onGenerated={async () => setActions(await listActions(storyId))} />
            <details className="panel actions-panel">
                <summary>Authority log ({actions.length})</summary>
                {actions.map((action) => <article className="action-entry" key={action.action_id}>
                    <p><strong>{action.action_type}</strong> · {action.status} · {action.decision?.outcome ?? "Pending"}</p>
                    <p>{action.request}</p><p className="muted">{action.decision?.reason}</p>
                </article>)}
            </details>
        </main>
    );
}
