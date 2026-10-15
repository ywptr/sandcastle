import { useEffect, useState } from "react";

import {
    listStories,
    type Story,
} from "./api/sandcastle";

import { StorySelector } from "./components/StorySelector";
import { StoryWorkspace } from "./components/StoryWorkspace";


function App() {
    const [stories, setStories] =
        useState<Story[]>([]);
    const [selectedStory, setSelectedStory] =
        useState<Story | null>(null);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState<string | null>(null);


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




    useEffect(() => {
        loadStory();
    }, []);


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