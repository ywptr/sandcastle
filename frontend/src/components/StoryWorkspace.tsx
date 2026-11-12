import { StorySetup } from "./studio/StorySetup";
import { RetainedPanel } from "./studio/RetainedPanel";
import { workspaceCopy } from "./studio/workspaceCopy";
import "../styles/studio-workspace.css";
import { useI18n } from "../i18n/context";
import { useEffect, useState } from "react";
import {
    getStoryWorkflow, type StoryWorkflow, createCanonEntry, listActions, listCanon, listCharacters, listPlaces, listScenes,
    saveCharacter, savePlace, updateCanon, updateStory,
    type CanonEntry, type Character, type Place, type Scene, type Story, type StoryAction,
} from "../api/sandcastle";
import type { EditorField } from "./RecordEditor";
import { StoryMetadataForm } from "./StoryMetadataForm";
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
export type WorkspaceSection = typeof sections[number][0];
export type WorkspaceMobileMode = "chat" | "tools" | "story";

export function StoryWorkspace({ story, onStoryUpdated, onDifficultyChanged, section, onSectionChange, mobileMode, onMobileModeChange, active = true }: {
    active?: boolean;
    story: Story; onStoryUpdated: (story: Story) => void; onDifficultyChanged?: (difficulty: string) => void;
    section: WorkspaceSection; onSectionChange: (section: WorkspaceSection) => void;
    mobileMode: WorkspaceMobileMode; onMobileModeChange: (mode: WorkspaceMobileMode) => void;
}) {
    const {t, locale} = useI18n();
    const copy = workspaceCopy[locale];
    const [advancedTools, setAdvancedTools] = useState(false);
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
    const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);
    const [view, setView] = useState<"chat" | "split" | "focus">("chat");
    const assistantOpen = view !== "focus";
    const [setupOpen, setSetupOpen] = useState(() => window.matchMedia("(min-width: 951px)").matches);
    useEffect(() => {
        const media = window.matchMedia("(min-width: 951px)");
        const resize = () => setSetupOpen(media.matches);
        media.addEventListener("change", resize);
        return () => media.removeEventListener("change", resize);
    }, []);
    const [viewSection, setViewSection] = useState(section);
    if (active && section !== viewSection) {
        setViewSection(section);
        if (section !== "overview") setView("split");
    }
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
    useEffect(() => {
        if (active && workflow) onDifficultyChanged?.(workflow.difficulty);
    }, [active, workflow, onDifficultyChanged]);
    function saveScene(scene: Scene) {
        setScenes((current) => upsert(current, scene, (entry) => entry.scene_id).sort((a, b) => a.sequence_number - b.sequence_number));
        setSelectedSceneId(scene.scene_id);
    }
    function navigate(next: WorkspaceSection) { setView("split"); onSectionChange(next); onMobileModeChange("tools"); setToolsOpen(false); }
    const easy = !workflow || workflow.difficulty === "easy";
    return <main className={`workspace studio-workspace workspace-view-${view} ${assistantOpen ? "" : "assistant-collapsed"}`}>
        <header className="story-header"><div><span className="eyebrow">{t("workspace.identity")} · {t(`series.status.${story.status}`)}</span><h1>{story.title}</h1>
            <p>{story.language ? t(`language.${story.language}`) : t("common.notSet")} · {story.primary_genre ? t(`genre.${story.primary_genre}`) : t("common.notSet")} · {workflow ? t(`difficulty.${workflow.difficulty}`) : t("common.loading")}</p></div>
            <div className="workspace-view-switch" role="group" aria-label={copy.layout}>
                <button type="button" aria-pressed={view === "chat"} onClick={() => setView("chat")}>{copy.chat}</button>
                <button type="button" aria-pressed={view === "split"} onClick={() => setView("split")}>{copy.split}</button>
                <button type="button" aria-pressed={view === "focus"} onClick={() => { setView("focus"); onMobileModeChange("tools"); }}>{t("workspace.focus")}</button>
            </div></header>
        <nav className="mobile-modes" aria-label={t("workspace.mode")}>
            <button type="button" aria-pressed={mobileMode === "story"} onClick={() => { onMobileModeChange("story"); setToolsOpen(true); }}>{copy.story}</button>
            <button type="button" aria-pressed={mobileMode === "chat"} onClick={() => { onMobileModeChange("chat"); setView("chat"); setToolsOpen(false); }}>{t("workspace.assistant")}</button>
            <button type="button" aria-pressed={mobileMode === "tools"} onClick={() => { onMobileModeChange("tools"); setView("split"); setToolsOpen(false); }}>{copy.preview}</button>
        </nav>
        <button type="button" className="mobile-tool-toggle secondary-button" aria-expanded={toolsOpen} aria-controls={`story-tools-${storyId}`} onClick={() => { setToolsOpen((v) => !v); onMobileModeChange(toolsOpen ? "tools" : "story"); }}>{t("workspace.mobileTools")} · {t(`workspace.${section}`)} {toolsOpen ? "−" : "+"}</button>
        <div className="workspace-load-state">
                {loading && <p role="status">{t("workspace.loading")}</p>}
                {errors.length > 0 && <div className="error" role="alert"><strong>{t("workspace.partialError")}</strong><ul>{errors.map((e) => <li key={e}>{e}</li>)}</ul><button type="button" className="secondary-button" onClick={() => setReload((v) => v + 1)}>{t("workspace.retryReads")}</button></div>}
        </div>
        <div className="workspace-layout">
            <nav id={`story-tools-${storyId}`} className={`workspace-nav ${toolsOpen || mobileMode === "story" ? "tools-open" : ""}`} aria-label={t("workspace.nav")}><span className="eyebrow">{t("workspace.yourStory")}</span>{sections.filter(([id]) => !easy || ["overview","scenes","characters"].includes(id)).map(([id]) => <button type="button" key={id} aria-current={section === id ? "page" : undefined} onClick={() => navigate(id)}>{t(`workspace.${id}`)}{id === "scenes" && <small>{scenes.length}</small>}</button>)}
                <button type="button" onClick={() => navigate("scenes")}>{t("workspace.production")}</button>
                {easy && <><button type="button" aria-expanded={advancedTools} onClick={() => setAdvancedTools((v) => !v)}>{t("workspace.tools")}</button>{advancedTools && sections.filter(([id]) => !["overview","scenes","characters"].includes(id)).map(([id]) => <button type="button" key={id} aria-current={section === id ? "page" : undefined} onClick={() => navigate(id)}>{t(`workspace.${id}`)}</button>)}</>}
                {scenes.length > 0 && <details open><summary>{t("workspace.sceneOutline")}</summary>{scenes.map((s) => <button type="button" key={s.scene_id} aria-current={section === "scenes" && selectedScene?.scene_id === s.scene_id ? "true" : undefined} onClick={() => { setSelectedSceneId(s.scene_id); navigate("scenes"); }}>{s.sequence_number}. {s.title || t("workspace.untitled")}</button>)}</details>}
            </nav>
            <div className={`assistant-region ${mobileMode === "chat" ? "mobile-active" : ""}`} hidden={!assistantOpen}>
                <AssistantPanel storyId={storyId} storyLanguage={story.language} workflow={workflow} onSaved={saveScene} onOpenScenes={() => navigate("scenes")} onGenerated={async () => setActions(await listActions(storyId))} />
                <button type="button" className="secondary-button" onClick={() => navigate("scenes")}>{t("workspace.openEditor")}</button>
            </div>
            <div className={`editor-region ${mobileMode === "tools" ? "mobile-active" : ""}`} role="region" aria-label={copy.preview} tabIndex={0}><div className="workspace-preview-heading"><span className="eyebrow">{copy.scenePreview}</span><p>{copy.savedPreview}</p></div>
                <RetainedPanel active={active && section === "overview"}><section className="panel overview-panel"><span className="eyebrow">{t("workspace.heart")}</span><div className="panel-heading"><h2>{t("workspace.details")}</h2></div>
                    {editingStory ? <StoryMetadataForm story={story} onCancel={() => setEditingStory(false)} onSave={async (input) => { const updated = await updateStory(storyId, input); onStoryUpdated(updated); setEditingStory(false); }} /> : <><h3>{t("metadata.premise")}</h3><p className="story-premise">{story.premise || t("workspace.premiseEmpty")}</p><h3>{t("metadata.objective")}</h3><p>{story.objective || t("workspace.objectiveEmpty")}</p><p>{t("metadata.language")}: {story.language ? t(`language.${story.language}`) : t("common.notSet")}</p><p>{t("field.genre")}: {[story.primary_genre, ...story.secondary_genres ?? []].filter(Boolean).map((g) => t(`genre.${g}`)).join(", ") || t("common.notSet")}</p></>}
                    <div className="overview-stats"><button type="button" onClick={() => navigate("scenes")}><strong>{scenes.length}</strong>{t("workspace.scenes")}</button><button type="button" onClick={() => navigate("characters")}><strong>{characters.length}</strong>{t("workspace.characters")}</button>{!easy && <button type="button" onClick={() => navigate("canon")}><strong>{canon.filter((c) => c.status === "approved").length}</strong>{t("workspace.canonFacts")}</button>}</div>
                    {!easy && <button type="button" className="secondary-button" onClick={() => navigate("workflow")}>Workflow: {workflow?.template_name ?? "Loading…"} · Difficulty: {workflow?.difficulty ?? "…"} →</button>}
                </section></RetainedPanel>
                <RetainedPanel active={active && section === "characters"}><WorldPanel title="Characters" singular="character" fields={characterFields}
                    records={characters.map((item) => ({ id: item.character_id, title: item.name,
                        values: { name: item.name, description: item.description, appearance: item.appearance, outfit: item.outfit, personality: item.personality } }))}
                    onSave={async (id, values) => {
                        const item = await saveCharacter(storyId, id, { name: values.name, description: values.description,
                            appearance: values.appearance, outfit: values.outfit, personality: values.personality });
                        setCharacters((current) => upsert(current, item, (entry) => entry.character_id));
                        return item.character_id;
                    }} /></RetainedPanel>
                <RetainedPanel active={active && section === "places"}><WorldPanel title="Places" singular="place" fields={placeFields}
                    records={places.map((item) => ({ id: item.place_id, title: item.name,
                        values: { name: item.name, description: item.description, appearance: item.appearance, atmosphere: item.atmosphere } }))}
                    onSave={async (id, values) => {
                        const item = await savePlace(storyId, id, { name: values.name, description: values.description,
                            appearance: values.appearance, atmosphere: values.atmosphere });
                        setPlaces((current) => upsert(current, item, (entry) => entry.place_id));
                        return item.place_id;
                    }} /></RetainedPanel>
                <RetainedPanel active={active && section === "canon"}><><p className="context-note">Canon is authoritative structured continuity. Editing Characters, Places, or Scenes never silently changes these facts.</p><WorldPanel title="Canon" singular="canon fact" fields={canonFields}
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
                    <CanonReview storyId={storyId} workflow={workflow} sceneId={selectedScene?.scene_id} onChanged={() => setReload((v) => v + 1)} /></></RetainedPanel>
                <RetainedPanel active={active && section === "scenes"}><ScenePanel difficulty={workflow?.difficulty} storyId={storyId} scenes={scenes} selectedId={selectedScene?.scene_id ?? null} onSelect={setSelectedSceneId} onSaved={saveScene} /></RetainedPanel>
                <RetainedPanel active={active && section === "workflow"}>{workflow ? <WorkflowPanel key={storyId} workflow={workflow} onSaved={setWorkflow} sceneId={selectedScene?.scene_id} onDomainChanged={() => setReload((v) => v + 1)} /> : <p>Workflow is unavailable. Retry loading above.</p>}</RetainedPanel>
                <RetainedPanel active={active && section === "universe"}><UniversePanel storyId={storyId} /></RetainedPanel>
                <RetainedPanel active={active && section === "assets"}><AssetsPanel storyId={storyId} onWorkflow={() => navigate("workflow")} /></RetainedPanel>
                <RetainedPanel active={active && section === "activity"}><section className="panel"><h2>Authority log</h2><p className="muted">Decisions associated with requested story actions.</p>{!actions.length && <p>No recorded actions yet.</p>}{actions.map((a) => <article className="action-entry" key={a.action_id}><h3>{a.action_type} · {a.status}</h3><p>{a.request}</p><p>{a.decision?.outcome ?? "Pending"} · {a.decision?.reason}</p></article>)}</section></RetainedPanel>
            </div>
            <aside className="workspace-setup-region">
                <button type="button" className="workspace-setup-toggle" aria-expanded={setupOpen} aria-controls={`story-setup-${storyId}`} onClick={() => setSetupOpen(value => !value)}><span>{copy.setup}</span><span aria-hidden="true">{setupOpen ? "−" : "+"}</span></button>
                <div id={`story-setup-${storyId}`} hidden={!setupOpen}>
                    <StorySetup story={story} onEdit={() => { navigate("overview"); setEditingStory(true); }} onOpenScenes={() => navigate("scenes")} />
                </div>
            </aside>
        </div>
    </main>;
}
