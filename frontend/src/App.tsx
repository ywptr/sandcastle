import { useEffect, useState } from "react";
import { ApiError, getCurrentUser, listStories, loginUrl, logout, type AuthUser, type Story } from "./api/sandcastle";
import { StorySelector } from "./components/StorySelector";
import { StoryWorkspace } from "./components/StoryWorkspace";

function App() {
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
                const result = await listStories();
                if (!active) return;
                setUser(identity);
                setStories(result);
                setSelectedStoryId(result[0]?.story_id ?? null);
            } catch (failure) {
                if (active && !(failure instanceof ApiError && failure.status === 401)) {
                    setError(failure instanceof Error ? failure.message : "Could not load Sandcastle.");
                }
            } finally {
                if (active) setLoading(false);
            }
        }
        void load();
        return () => { active = false; };
    }, []);

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
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary-button" onClick={() => { window.location.href = loginUrl(); }}>Sign in through IS</button>
    </div></div>;

    return <div className="app">
        <header className="app-header"><div className="brand"><strong>Sandcastle</strong><span>Story & Canon</span>
            <div className="user-menu"><div><strong>{user.name ?? user.email}</strong><span>{user.email}</span></div>
                <button className="secondary-button" onClick={handleLogout}>Sign out</button></div>
        </div></header>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="app-body">
            <StorySelector stories={stories} selectedStoryId={selectedStoryId}
                onSelect={(story) => setSelectedStoryId(story.story_id)} onCreated={(story) => {
                    setStories((current) => [story, ...current]);
                    setSelectedStoryId(story.story_id);
                }} />
            <div className="app-content">{selectedStory ? <StoryWorkspace key={selectedStory.story_id}
                story={selectedStory} onStoryUpdated={(updated) => setStories((current) => current.map((story) =>
                    story.story_id === updated.story_id ? updated : story))} />
                : <div className="empty-state"><h1>Create your first story</h1><p>Start with a title and premise in the Stories panel.</p></div>}
            </div>
        </div>
    </div>;
}

export default App;
