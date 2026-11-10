import { useEffect, useState } from "react";
import {
    getStoryWorkflow, type StoryWorkflow, createCanonEntry, listActions, listCanon, listCharacters, listPlaces, listScenes,
    saveCharacter, savePlace, updateCanon, updateStory,
    type CanonEntry, type Character, type Place, type Scene, type Story, type StoryAction,
} from "../api/sandcastle";
import type { EditorField } from "./RecordEditor";
import { StoryMetadataForm } from "./StoryMetadataForm";
import { languages, genreLabel } from "../api/storyMetadata";
import { WorldPanel } from "./WorldPanel";
import { ScenePanel } from "./ScenePanel";
import { WorkflowPanel } from "./WorkflowPanel";
import { AssistantPanel } from "./AssistantPanel";
import { CanonReview } from "./CanonReview";
import { UniversePanel, AssetsPanel } from "./ContextPanels";

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
function upsert<T>(items: T[], item: T, id: (entry: T) => string): T[] {
    return items.some((entry) => id(entry) === id(item))
        ? items.map((entry) => id(entry) === id(item) ? item : entry) : [...items, item];
}


const sections = [
    ["overview", "Overview"], ["scenes", "Scenes"], ["characters", "Characters"], ["places", "Places"],
    ["canon", "Canon"], ["universe", "Universe"], ["assets", "Assets"], ["workflow", "Workflow & Difficulty"], ["activity", "Authority log"],
] as const;
type Section = typeof sections[number][0];

export function StoryWorkspace({ story, onStoryUpdated }: { story: Story; onStoryUpdated: (story: Story) => void }) {
    const [workflow, setWorkflow] = useState<StoryWorkflow | null>(null);
    const [characters, setCharacters] = useState<Character[]>([]);
    const [places, setPlaces] = useState<Place[]>([]);
    const [canon, setCanon] = useState<CanonEntry[]>([]);
    const [scenes, setScenes] = useState<Scene[]>([]);
    const [actions, setActions] = useState<StoryAction[]>([]);
    const [editingStory, setEditingStory] = useState(false);
    const [loading, setLoading] = useState(true);
    const [errors, setErrors] = useState<string[]>([]);
    const [reload, setReload] = useState(0);
    const [toolsOpen, setToolsOpen] = useState(false);
    const [section, setSection] = useState<Section>("overview");
    const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);
    const [assistantOpen, setAssistantOpen] = useState(true);
    const [mobileMode, setMobileMode] = useState("chat");
    const storyId = story.story_id;
    const selectedScene = scenes.find((s) => s.scene_id === selectedSceneId) ?? scenes.at(-1);
    useEffect(() => {
        let active = true;
        Promise.allSettled([listCharacters(storyId), listPlaces(storyId), listCanon(storyId), listScenes(storyId), listActions(storyId), getStoryWorkflow(storyId)])
            .then(([c, p, f, s, a, w]) => {
                if (!active) return;
                if (c.status === "fulfilled") setCharacters(c.value);
                if (p.status === "fulfilled") setPlaces(p.value);
                if (f.status === "fulfilled") setCanon(f.value);
                if (s.status === "fulfilled") setScenes(s.value.toSorted((a, b) => a.sequence_number - b.sequence_number));
                if (a.status === "fulfilled") setActions(a.value);
                if (w.status === "fulfilled") setWorkflow(w.value);
                const names = ["Characters", "Places", "Canon", "Scenes", "Authority log", "Workflow"];
                setErrors([c, p, f, s, a, w].flatMap((v, i) => v.status === "rejected" ? [`${names[i]}: ${v.reason instanceof Error ? v.reason.message : "Could not load"}`] : []));
                setLoading(false);
            });
        return () => { active = false; };
    }, [storyId, reload]);
    function saveScene(scene: Scene) {
        setScenes((current) => upsert(current, scene, (entry) => entry.scene_id).sort((a, b) => a.sequence_number - b.sequence_number));
        setSelectedSceneId(scene.scene_id);
    }
    function navigate(next: Section) { setSection(next); setMobileMode("tools"); setToolsOpen(false); }
    return <main className={`workspace ${assistantOpen ? "" : "assistant-collapsed"}`}>
        <header className="story-header"><div><span className="eyebrow">Series workspace · {story.status}</span><h1>{story.title}</h1>
            <p>{story.language ? languages[story.language as keyof typeof languages] : "Language not set"} · {story.primary_genre ? genreLabel(story.primary_genre) : "Genre not set"} · {workflow?.difficulty ?? "Loading difficulty…"}</p></div>
            <button type="button" className="secondary-button assistant-toggle" aria-expanded={assistantOpen} onClick={() => setAssistantOpen((v) => !v)}>{assistantOpen ? "Focus editor" : "Show assistant"}</button></header>
        <nav className="mobile-modes" aria-label="Story mode"><button type="button" aria-pressed={mobileMode === "chat"} onClick={() => { setMobileMode("chat"); setAssistantOpen(true); }}>Assistant</button><button type="button" aria-pressed={mobileMode === "tools" && section === "overview"} onClick={() => navigate("overview")}>Outline</button><button type="button" aria-pressed={mobileMode === "tools" && section === "scenes"} onClick={() => navigate("scenes")}>Scenes</button></nav>
        <button type="button" className="mobile-tool-toggle secondary-button" aria-expanded={toolsOpen} aria-controls="story-tools" onClick={() => setToolsOpen((v) => !v)}>Story tools · {sections.find(([id]) => id === section)?.[1]} {toolsOpen ? "−" : "+"}</button>
        <div className="workspace-layout">
            <nav id="story-tools" className={`workspace-nav ${toolsOpen ? "tools-open" : ""}`} aria-label="Story workspace"><span className="eyebrow">Your story</span>{sections.map(([id, label]) => <button type="button" key={id} aria-current={section === id ? "page" : undefined} onClick={() => navigate(id)}>{label}{id === "scenes" && <small>{scenes.length}</small>}</button>)}
                {scenes.length > 0 && <details open><summary>Scene outline</summary>{scenes.map((s) => <button type="button" key={s.scene_id} onClick={() => { setSelectedSceneId(s.scene_id); navigate("scenes"); }}>{s.sequence_number}. {s.title || "Untitled scene"}</button>)}</details>}
            </nav>
            <div className={`assistant-region ${mobileMode === "chat" ? "mobile-active" : ""}`} hidden={!assistantOpen}>
                <AssistantPanel storyId={storyId} workflow={workflow} onSaved={saveScene} onOpenScenes={() => setSection("scenes")} onGenerated={async () => setActions(await listActions(storyId))} />
                <button type="button" className="secondary-button" onClick={() => navigate("scenes")}>Open scene editor →</button>
            </div>
            <div className={`editor-region ${mobileMode === "tools" ? "mobile-active" : ""}`}>
                {loading && <p role="status">Loading your story…</p>}
                {errors.length > 0 && <div className="error" role="alert"><strong>Some story data could not load.</strong><ul>{errors.map((e) => <li key={e}>{e}</li>)}</ul><button type="button" className="secondary-button" onClick={() => setReload((v) => v + 1)}>Retry failed reads</button></div>}
                {section === "overview" && <section className="panel overview-panel"><span className="eyebrow">The heart of your series</span><div className="panel-heading"><h2>Story details</h2><button type="button" className="secondary-button" onClick={() => setEditingStory(true)}>Edit details</button></div>
                    {editingStory ? <StoryMetadataForm story={story} onCancel={() => setEditingStory(false)} onSave={async (input) => { const updated = await updateStory(storyId, input); onStoryUpdated(updated); setEditingStory(false); }} /> : <><h3>Premise</h3><p className="story-premise">{story.premise || "What if…? Add a premise to begin shaping this world."}</p><h3>Objective</h3><p>{story.objective || "Where do you want this story to go?"}</p><p>Language: {story.language || "Not set"}</p><p>Genre: {[story.primary_genre, ...story.secondary_genres ?? []].filter(Boolean).map((g) => genreLabel(g!)).join(", ") || "Not set"}</p></>}
                    <div className="overview-stats"><button type="button" onClick={() => navigate("scenes")}><strong>{scenes.length}</strong>Scenes</button><button type="button" onClick={() => navigate("characters")}><strong>{characters.length}</strong>Characters</button><button type="button" onClick={() => navigate("canon")}><strong>{canon.filter((c) => c.status === "approved").length}</strong>Canon facts</button></div>
                    <button type="button" className="secondary-button" onClick={() => navigate("workflow")}>Workflow: {workflow?.template_name ?? "Loading…"} · Difficulty: {workflow?.difficulty ?? "…"} →</button>
                </section>}
                {section === "characters" && <WorldPanel title="Characters" singular="character" fields={characterFields}
                    records={characters.map((item) => ({ id: item.character_id, title: item.name,
                        values: { name: item.name, description: item.description, appearance: item.appearance, outfit: item.outfit, personality: item.personality } }))}
                    onSave={async (id, values) => {
                        const item = await saveCharacter(storyId, id, { name: values.name, description: values.description,
                            appearance: values.appearance, outfit: values.outfit, personality: values.personality });
                        setCharacters((current) => upsert(current, item, (entry) => entry.character_id));
                        return item.character_id;
                    }} />}
                {section === "places" && <WorldPanel title="Places" singular="place" fields={placeFields}
                    records={places.map((item) => ({ id: item.place_id, title: item.name,
                        values: { name: item.name, description: item.description, appearance: item.appearance, atmosphere: item.atmosphere } }))}
                    onSave={async (id, values) => {
                        const item = await savePlace(storyId, id, { name: values.name, description: values.description,
                            appearance: values.appearance, atmosphere: values.atmosphere });
                        setPlaces((current) => upsert(current, item, (entry) => entry.place_id));
                        return item.place_id;
                    }} />}
                {section === "canon" && <><p className="context-note">Canon is authoritative structured continuity. Editing Characters, Places, or Scenes never silently changes these facts.</p><WorldPanel title="Canon" singular="canon fact" fields={canonFields}
                    createFields={canonFields.filter((field) => field.name !== "status")}
                    records={canon.map((item) => ({ id: item.canon_entry_id, title: item.key,
                        values: { type: item.type, key: item.key, value: item.value, status: item.status } }))}
                    onSave={async (id, values) => {
                        const input = { type: values.type, key: values.key, value: values.value };
                        const item = id ? await updateCanon(storyId, id, { ...input, status: values.status === "superseded" ? "superseded" : "approved" })
                            : await createCanonEntry(storyId, input.type, input.key, input.value);
                        setCanon((current) => upsert(current, item, (entry) => entry.canon_entry_id));
                        return item.canon_entry_id;
                    }} />
                    <CanonReview storyId={storyId} workflow={workflow} sceneId={selectedScene?.scene_id} onChanged={() => setReload((v) => v + 1)} /></>}
                {section === "scenes" && <ScenePanel storyId={storyId} scenes={scenes} selectedId={selectedScene?.scene_id ?? null} onSelect={setSelectedSceneId} onSaved={saveScene} />}
                {section === "workflow" && (workflow ? <WorkflowPanel key={storyId} workflow={workflow} onSaved={setWorkflow} sceneId={selectedScene?.scene_id} onDomainChanged={() => setReload((v) => v + 1)} /> : <p>Workflow is unavailable. Retry loading above.</p>)}
                {section === "universe" && <UniversePanel storyId={storyId} />}
                {section === "assets" && <AssetsPanel storyId={storyId} onWorkflow={() => navigate("workflow")} />}
                {section === "activity" && <section className="panel"><h2>Authority log</h2><p className="muted">Decisions associated with requested story actions.</p>{!actions.length && <p>No recorded actions yet.</p>}{actions.map((a) => <article className="action-entry" key={a.action_id}><h3>{a.action_type} · {a.status}</h3><p>{a.request}</p><p>{a.decision?.outcome ?? "Pending"} · {a.decision?.reason}</p></article>)}</section>}
            </div>
        </div>
    </main>;
}
