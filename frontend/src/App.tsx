import { useEffect, useState } from "react";
import { getCurrentUser, listStories, loginUrl, logout, type AuthUser, type Story } from "./api/sandcastle";
import { GetStarted } from "./components/GetStarted";
import { useI18n } from "./i18n/context";
import { StorySelector } from "./components/StorySelector";
import { SettingsPage } from "./components/SettingsPage";
import { settingsDetail } from "./settings/copy";
import { StoryWorkspace } from "./components/StoryWorkspace";

function App() {
    const {t} = useI18n();
    const [home, setHome] = useState(false);
    const [difficulty, setDifficulty] = useState("easy");
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [browserOpen, setBrowserOpen] = useState(true);
    const [retry, setRetry] = useState(0);
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
                setSelectedStoryId(result[0]?.story_id ?? null);
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

    return <div className={`app ${browserOpen ? "browser-open" : "browser-closed"}`}>
        <header className="app-header"><div className="brand"><strong>Sandcastle<span className="brand-dot">✦</span></strong><span>{t("nav.studio")}</span>
            <button type="button" className="secondary-button" aria-expanded={browserOpen} onClick={() => { setSettingsOpen(false); setBrowserOpen((v) => !v); }}>{t(browserOpen ? "nav.closeSeries" : "nav.browse")}</button>
            <button type="button" className="secondary-button" onClick={() => {setHome(true);setSettingsOpen(false);setBrowserOpen(false);}}>{t("nav.home")}</button>
            <button type="button" className="secondary-button" aria-pressed={settingsOpen} onClick={() => { setBrowserOpen(false); setSettingsOpen((v) => !v); }}>{t("nav.settings")}</button>
            <div className="user-menu"><div><strong>{user.name ?? user.email}</strong><span>{user.email}</span></div>
                <button className="secondary-button" onClick={handleLogout}>{t("nav.signOut")}</button></div>
        </div></header>
        {error && <p className="error" role="alert">{t(error)} <button type="button" onClick={() => setRetry((v) => v + 1)}>{t("common.retry")}</button></p>}
        <div className="app-body">
            <StorySelector stories={stories} selectedStoryId={selectedStoryId}
                onStart={() => {setHome(true);setSettingsOpen(false);setBrowserOpen(false);}} onSelect={(story) => { setHome(false);setSelectedStoryId(story.story_id); setBrowserOpen(false); }} onCreated={(story) => {
                    setHome(false);setStories((current) => [story, ...current]);
                    setSelectedStoryId(story.story_id);
                    setBrowserOpen(false);
                }} />
            <div className="app-content">{settingsOpen ? <SettingsPage user={user} initialDetail={settingsDetail(difficulty)} onClose={() => setSettingsOpen(false)} /> : home ? <GetStarted onDetailed={() => {setHome(false);setBrowserOpen(true);}} onCreated={(story) => {setStories((current) => [story,...current]);setSelectedStoryId(story.story_id);setHome(false);setBrowserOpen(false);}} /> : selectedStory ? <StoryWorkspace key={selectedStory.story_id}
                story={selectedStory} onDifficultyChanged={setDifficulty} onStoryUpdated={(updated) => setStories((current) => current.map((story) =>
                    story.story_id === updated.story_id ? updated : story))} />
                : <GetStarted onDetailed={() => setBrowserOpen(true)} onCreated={(story) => {setStories((current) => [story,...current]);setSelectedStoryId(story.story_id);setBrowserOpen(false);}} />}
            </div>
        </div>
    </div>;
}

export default App;
