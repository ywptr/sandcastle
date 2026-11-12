import { useEffect, useState } from "react";
import { getCurrentUser, listStories, loginUrl, logout, type AuthUser, type Story } from "./api/sandcastle";
import { GetStarted } from "./components/GetStarted";
import { useI18n } from "./i18n/context";
import { StorySelector } from "./components/StorySelector";
import { SettingsPage } from "./components/SettingsPage";
import { settingsDetail } from "./settings/copy";
import { StudioShell } from "./components/studio/StudioShell";
import type { StudioDestination } from "./components/studio/navigation";
import { StoryWorkspace, type WorkspaceSection, type WorkspaceMobileMode } from "./components/StoryWorkspace";

function App() {
    const {t} = useI18n();
    const [workspaceSection, setWorkspaceSection] = useState<WorkspaceSection>("overview");
    const [workspaceMobileMode, setWorkspaceMobileMode] = useState<WorkspaceMobileMode>("chat");
    const [home, setHome] = useState(false);
    const [difficulty, setDifficulty] = useState("easy");
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [browserOpen, setBrowserOpen] = useState(true);
    const [retry, setRetry] = useState(0);
    const [openedStoryIds, setOpenedStoryIds] = useState<string[]>([]);
    const [stories, setStories] = useState<Story[]>([]);
    const [selectedStoryId, setSelectedStoryId] = useState<string | null>(null);
    const [user, setUser] = useState<AuthUser | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const selectedStory = stories.find((story) => story.story_id === selectedStoryId);

    useEffect(() => {
        let active = true;
        async function load() {
            try {
                const identity = await getCurrentUser();
                if (!active || identity === null) return;
                setUser(identity);
                const result = await listStories();
                if (!active) return;
                setError(null);
                setStories(result);
                setHome(!result.length);
                setBrowserOpen(result.length > 0);
                setSelectedStoryId(result[0]?.story_id ?? null);
                setOpenedStoryIds(result[0] ? [result[0].story_id] : []);
            } catch {
                if (active) {
                    setError("app.error");
                }
            } finally {
                if (active) setLoading(false);
            }
        }
        void load();
        return () => { active = false; };
    }, [retry]);

    async function handleLogout() {
        try {
            await logout();
            setSettingsOpen(false);
            setUser(null);
            setStories([]);
            setOpenedStoryIds([]);
            setSelectedStoryId(null);
        } catch (failure) {
            setError(failure instanceof Error ? failure.message : "Could not sign out.");
        }
    }

    if (loading) return <div className="loading" role="status">{t("app.loading")}</div>;
    if (!user) return <div className="auth-screen"><div className="auth-card">
        <h1>Sandcastle</h1><p>{t("app.welcome")}</p>
        {error && <p className="error" role="alert">{t(error)} <button type="button" onClick={() => setRetry((v) => v + 1)}>{t("common.retry")}</button></p>}
        <button className="primary-button" onClick={() => { window.location.href = loginUrl(); }}>{t("app.signIn")}</button>
    </div></div>;

    function navigate(destination: StudioDestination) {
        window.scrollTo(0, 0);
        setSettingsOpen(destination === "settings");
        if (destination !== "settings") setHome(destination === "home");
        setBrowserOpen(destination === "series");
        if (["workspace", "characters", "world", "library"].includes(destination)) {
            setWorkspaceSection(destination === "characters" ? "characters" : destination === "world" ? "canon" : destination === "library" ? "assets" : "overview");
            setWorkspaceMobileMode(destination === "workspace" ? "chat" : "tools");
        }
    }
    function selectStory(story: Story) {
        setSelectedStoryId(story.story_id);
        setOpenedStoryIds(current => current.includes(story.story_id) ? current : [...current, story.story_id]);
        navigate("workspace");
    }
    function handleCreated(story: Story) {
        setStories(current => [story, ...current]);
        selectStory(story);
    }
    const active: StudioDestination = settingsOpen ? "settings" : home ? "home" : browserOpen ? "series"
        : workspaceSection === "characters" ? "characters" : ["canon", "places", "universe"].includes(workspaceSection) ? "world"
        : workspaceSection === "assets" ? "library" : "workspace";

    return <StudioShell user={user} active={active} hasStory={!!selectedStory} onNavigate={navigate} onLogout={() => { void handleLogout(); }}>
        <div className={`app ${browserOpen ? "browser-open" : "browser-closed"}`}>
        {error && <p className="error" role="alert">{t(error)} <button type="button" onClick={() => setRetry((v) => v + 1)}>{t("common.retry")}</button></p>}
        <div className="app-body">
            <StorySelector stories={stories} selectedStoryId={selectedStoryId}
                onStart={() => navigate("home")} onSelect={selectStory} onCreated={handleCreated} />
            <div className="app-content"><div hidden={settingsOpen || !home}><GetStarted active={home && !settingsOpen} onDetailed={() => {setHome(false);setBrowserOpen(true);}} onCreated={handleCreated} /></div>{settingsOpen && <SettingsPage user={user} initialDetail={settingsDetail(difficulty)} onClose={() => setSettingsOpen(false)} />}
                {stories.filter(item => openedStoryIds.includes(item.story_id)).map(item => <div key={item.story_id} hidden={settingsOpen || home || item.story_id !== selectedStoryId}>
                    <StoryWorkspace active={!settingsOpen && !home && item.story_id === selectedStoryId}
                        story={item} section={workspaceSection} onSectionChange={setWorkspaceSection} mobileMode={workspaceMobileMode} onMobileModeChange={setWorkspaceMobileMode} onDifficultyChanged={setDifficulty}
                        onStoryUpdated={updated => setStories(current => current.map(value => value.story_id === updated.story_id ? updated : value))} />
                </div>)}
            </div>
        </div>
        </div>
    </StudioShell>;
}

export default App;
