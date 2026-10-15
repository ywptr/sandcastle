import { useState } from "react";

import {
    createStory,
    type Story,
} from "../api/sandcastle";


interface StorySelectorProps {
    stories: Story[];
    selectedStoryId: string | null;
    onSelect: (story: Story) => void;
    onCreated: (story: Story) => void;
}


export function StorySelector({
    stories,
    selectedStoryId,
    onSelect,
    onCreated,
}: StorySelectorProps) {
    const [creating, setCreating] =
        useState(false);

    const [title, setTitle] =
        useState("");

    const [premise, setPremise] =
        useState("");

    const [objective, setObjective] =
        useState("");

    const [error, setError] =
        useState<string | null>(null);


    function resetForm() {
        setTitle("");
        setPremise("");
        setObjective("");
        setError(null);
    }


    function cancelCreate() {
        resetForm();
        setCreating(false);
    }


    async function handleCreate() {
        const cleanTitle = title.trim();

        if (!cleanTitle) {
            setError("Title is required.");
            return;
        }

        try {
            setError(null);

            const story = await createStory({
                title: cleanTitle,
                premise:
                    premise.trim()
                    || undefined,
                objective:
                    objective.trim()
                    || undefined,
            });

            onCreated(story);

            resetForm();
            setCreating(false);

        } catch (error) {
            setError(
                error instanceof Error
                    ? error.message
                    : "Failed to create story"
            );
        }
    }


    return (
        <aside className="story-sidebar">

            <div className="story-sidebar-heading">
                <h2>Stories</h2>

                <button
                    className="secondary-button"
                    onClick={() =>
                        setCreating(true)
                    }
                >
                    New
                </button>
            </div>


            <div className="story-list">
                {stories.map((story) => (
                    <button
                        key={story.story_id}
                        className={
                            story.story_id
                            === selectedStoryId
                                ? "story-list-item active"
                                : "story-list-item"
                        }
                        onClick={() =>
                            onSelect(story)
                        }
                    >
                        <strong>
                            {story.title}
                        </strong>

                        {story.premise && (
                            <span>
                                {story.premise}
                            </span>
                        )}
                    </button>
                ))}
            </div>


            {creating && (
                <div className="story-create-form">

                    <h3>New story</h3>

                    <label>
                        <span>Title</span>

                        <input
                            value={title}
                            onChange={(event) =>
                                setTitle(
                                    event.target.value
                                )
                            }
                        />
                    </label>

                    <label>
                        <span>Premise</span>

                        <textarea
                            value={premise}
                            onChange={(event) =>
                                setPremise(
                                    event.target.value
                                )
                            }
                        />
                    </label>

                    <label>
                        <span>Objective</span>

                        <textarea
                            value={objective}
                            onChange={(event) =>
                                setObjective(
                                    event.target.value
                                )
                            }
                        />
                    </label>

                    {error && (
                        <div className="error">
                            {error}
                        </div>
                    )}

                    <div className="story-create-actions">
                        <button
                            className="secondary-button"
                            onClick={cancelCreate}
                        >
                            Cancel
                        </button>

                        <button
                            className="primary-button"
                            onClick={handleCreate}
                        >
                            Create
                        </button>
                    </div>

                </div>
            )}

        </aside>
    );
}