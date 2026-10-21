import { useEffect, useState } from "react";

import {
    getCurrentUser,
    logout,
    type AuthUser,
    listStories,
    type Story,
} from "./api/sandcastle";

import { StorySelector } from "./components/StorySelector";
import { StoryWorkspace } from "./components/StoryWorkspace";


function App() {
    const [stories, setStories] = useState<Story[]>([]);
    const [selectedStory, setSelectedStory] = useState<Story | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [user, setUser] = useState<AuthUser | null>(null);
    const [authLoading, setAuthLoading] = useState(true);

    async function loadUser() {
    try {
        const result =
            await getCurrentUser();

        setUser(result);

    } catch {
        setUser(null);

    } finally {
        setAuthLoading(false);
    }
}

    async function loadStory() {
        try {
            const result =
                await listStories();

            setStories(result);

            setSelectedStory(
              result.length > 0
              ? result[0]
              : null
            );

        } catch (error) {
            setError(
                error instanceof Error
                    ? error.message
                    : "Failed to load Sandcastle"
            );

        } finally {
            setLoading(false);
        }
    }

    function handleStoryCreated(
      story: Story, 
    ) {
      setStories((current) => [
        story,
        ...current,
      ]);

      setSelectedStory(story);
    }

    function handleLogin() {
        window.location.href =
            `${import.meta.env.VITE_API_BASE_URL}/auth/login`;
    }


    async function handleLogout() {
        try {
            await logout();
        } finally {
            setUser(null);
            setStories([]);
            setSelectedStory(null);
        }
    }


    useEffect(() => {
        loadUser();
    }, []);

    useEffect(() => {
        if (user) {
            loadStory();
        }
    }, [user]);


    if (authLoading) {
        return (
            <div className="loading">
                Checking session…
            </div>
        );
    }


    if (!user) {
        return (
            <div className="auth-screen">
                <div className="auth-card">
                    <h1>Sandcastle</h1>

                    <p>
                        Sign in to continue to your stories and canon.
                    </p>

                    <button
                        className="primary-button"
                        onClick={handleLogin}
                    >
                        Sign in
                    </button>
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="loading">
                Loading Sandcastle…
            </div>
        );
    }

    if (error) {
        return (
            <div className="loading">
                {error}
            </div>
        );
    }

    return (
        <div className="app">
            <header className="app-header">
                <div className="brand">
                    <strong>
                        Sandcastle
                    </strong>

                    <span>
                        Story & Canon
                    </span>
                </div>
            </header>

          <div className="app-body">
          
              <StorySelector
                  stories={stories}
                  selectedStoryId={
                      selectedStory?.story_id
                      ?? null
                  }
                  onSelect={setSelectedStory}
                  onCreated={handleStoryCreated}
              />
          
              <div className="app-content">
                  {selectedStory ? (
                      <StoryWorkspace
                          story={selectedStory}
                      />
                  ) : (
                      <div className="empty-state">
                          <h1>Create your first story</h1>
          
                          <p>
                              Start by creating a story
                              from the Stories panel.
                          </p>
                      </div>
                  )}
              </div>
          
          </div>
        </div>
    );
}

export default App;