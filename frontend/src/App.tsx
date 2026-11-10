import { useEffect, useState } from "react";
import { getCurrentUser, listStories, loginUrl, logout, type AuthUser, type Story } from "./api/sandcastle";
import { StorySelector } from "./components/StorySelector";
import { StoryWorkspace } from "./components/StoryWorkspace";

function App() {
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
            setUser(null);
            setStories([]);
            setSelectedStoryId(null);
        } catch (failure) {
            setError(failure instanceof Error ? failure.message : "Could not sign out.");
        }
    }

    if (loading) return <div className="loading" role="status">Loading Sandcastle…</div>;
    if (!user) return <div className="auth-screen"><div className="auth-card">
        <h1>Sandcastle</h1><p>Sign in to create and continue your stories.</p>
        {error && <p className="error" role="alert">{error} <button type="button" onClick={() => setRetry((v) => v + 1)}>Retry connection</button></p>}
        <button className="primary-button" onClick={() => { window.location.href = loginUrl(); }}>Sign in through IS</button>
    </div></div>;

    return <div className={`app ${browserOpen ? "browser-open" : "browser-closed"}`}>
        <header className="app-header"><div className="brand"><strong>Sandcastle<span className="brand-dot">✦</span></strong><span>Your story studio</span>
            <button type="button" className="secondary-button" aria-expanded={browserOpen} onClick={() => setBrowserOpen((v) => !v)}>{browserOpen ? "Close series" : "Browse series"}</button>
            <div className="user-menu"><div><strong>{user.name ?? user.email}</strong><span>{user.email}</span></div>
                <button className="secondary-button" onClick={handleLogout}>Sign out</button></div>
        </div></header>
        {error && <p className="error" role="alert">{error} <button type="button" onClick={() => setRetry((v) => v + 1)}>Retry</button></p>}
        <div className="app-body">
            <StorySelector stories={stories} selectedStoryId={selectedStoryId}
                onSelect={(story) => { setSelectedStoryId(story.story_id); setBrowserOpen(false); }} onCreated={(story) => {
                    setStories((current) => [story, ...current]);
                    setSelectedStoryId(story.story_id);
                    setBrowserOpen(false);
                }} />
            <div className="app-content">{selectedStory ? <StoryWorkspace key={selectedStory.story_id}
                story={selectedStory} onStoryUpdated={(updated) => setStories((current) => current.map((story) =>
                    story.story_id === updated.story_id ? updated : story))} />
                : <div className="empty-state"><h1>Create your first story</h1><p>Start with an idea in the Series browser.</p></div>}
            </div>
        </div>
    </div>;
}

export default App;
