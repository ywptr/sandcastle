import { useEffect, useState } from "react";

import {
    createCanonEntry,
    generateScene,
    listActions,
    listCanon,
    listScenes,
    type CanonEntry,
    type Scene,
    type Story,
    type StoryAction,
} from "../api/sandcastle";

import { CanonForm } from "./CanonForm";

interface StoryWorkspaceProps {
    story: Story;
}

export function StoryWorkspace({
    story,
}: StoryWorkspaceProps) {
    const [canon, setCanon] =
        useState<CanonEntry[]>([]);

    const [actions, setActions] =
        useState<StoryAction[]>([]);

    const [actionRequest, setActionRequest] =
        useState("");

    const [scenes, setScenes] =
        useState<Scene[]>([]);

    const [submitting, setSubmitting] =
        useState(false);

    const [error, setError] =
        useState<string | null>(null);


    async function handleCreateCanon(
        type: string,
        key: string,
        value: string,
    ) {
        const entry = await createCanonEntry(
            story.story_id,
            type,
            key,
            value,
        );

        setCanon((current) => [
            ...current,
            entry,
        ]);

        return entry;
    }

    async function loadCanon() {
        const result = await listCanon(
            story.story_id
        );

        setCanon(result);
    }

    async function loadScenes() {
        const result = await listScenes(
            story.story_id
        );

        setScenes(result);
    }


    async function loadActions() {
        const result = await listActions(
            story.story_id
        );

        setActions(result);
    }


    async function loadWorkspace() {
        try {
            setError(null);

            await Promise.all([
                loadCanon(),
                loadActions(),
                loadScenes(),
            ]);
        } catch (error) {
            setError(
                error instanceof Error
                    ? error.message
                    : "Failed to load story"
            );
        }
    }


    async function handleSubmitAction() {
        const request =
            actionRequest.trim();

        if (!request || submitting) {
            return;
        }

        try {
            setSubmitting(true);
            setError(null);

            await generateScene(
                story.story_id,
                request,
            );

            setActionRequest("");

            await Promise.all([
                loadActions(),
                loadScenes(),
            ]);
        } catch (error) {
            setError(
                error instanceof Error
                    ? error.message
                    : "Failed to submit action"
            );
        } finally {
            setSubmitting(false);
        }
    }


    useEffect(() => {
        loadWorkspace();
    }, [story.story_id]);


    return (
        <main className="workspace">

            <section className="story-header">
                <div>
                    <span className="eyebrow">
                        Story
                    </span>

                    <h1>{story.title}</h1>

                    {story.premise && (
                        <p>{story.premise}</p>
                    )}
                </div>
            </section>


            {error && (
                <div className="error">
                    {error}
                </div>
            )}


            <div className="workspace-grid">

                <section className="panel">
                    <div className="panel-heading">
                        <h2>Canon</h2>
                        <span>
                            {canon.length} entries
                        </span>
                    </div>

                    <CanonForm
                        onCreate={handleCreateCanon}
                    />                    

                    <div className="canon-list">
                        {canon.map((entry) => (
                            <article
                                key={
                                    entry.canon_entry_id
                                }
                                className="canon-entry"
                            >
                                <div className="canon-meta">
                                    <span>
                                        {entry.type}
                                    </span>

                                    <code>
                                        {entry.key}
                                    </code>
                                </div>

                                <p>
                                    {entry.value}
                                </p>
                            </article>
                        ))}
                    </div>
                </section>


                <section className="panel">
                    <div className="panel-heading">
                        <h2>Story Action</h2>
                    </div>

                    <textarea
                        className="action-input"
                        placeholder={
                            "What should happen next?"
                        }
                        value={actionRequest}
                        onChange={(event) =>
                            setActionRequest(
                                event.target.value
                            )
                        }
                    />

                    <button
                        className="primary-button"
                        disabled={submitting}
                        onClick={
                            handleSubmitAction
                        }
                    >
                        {submitting
                            ? "Writing scene…"
                            : "Generate scene"}
                    </button>
                </section>

            </div>


            <section className="panel actions-panel">
                <div className="panel-heading">
                    <h2>Authority Log</h2>

                    <span>
                        {actions.length} actions
                    </span>
                </div>

                <div className="action-list">
                    {actions.map((action) => (
                        <article
                            className="action-entry"
                            key={action.action_id}
                        >
                            <div className="action-top">
                                <strong>
                                    {
                                        action.action_type
                                    }
                                </strong>

                                {action.decision && (
                                    <span
                                        className={
                                            `decision decision-${action.decision.outcome.toLowerCase()}`
                                        }
                                    >
                                        {
                                            action
                                                .decision
                                                .outcome
                                        }
                                    </span>
                                )}
                            </div>

                            <p>
                                {action.request}
                            </p>

                            {action.decision && (
                                <div className="decision-reason">
                                    {
                                        action
                                            .decision
                                            .reason
                                    }
                                </div>
                            )}
                        </article>
                    ))}
                </div>
            </section>

            <section className="panel scenes-panel">
                <div className="panel-heading">
                    <h2>Story</h2>

                    <span>
                        {scenes.length} scenes
                    </span>
                </div>

                {scenes.length === 0 ? (
                    <div className="scene-empty">
                        <p>No scenes yet.</p>

                        <span>
                            Describe what should happen
                            next and generate the first scene.
                        </span>
                    </div>
                ) : (
                    <div className="scene-list">
                        {scenes.map((scene) => (
                            <article
                                key={scene.scene_id}
                                className="scene"
                            >
                                <div className="scene-heading">
                                    Scene {
                                        scene.sequence_number
                                    }
                                </div>

                                <div className="scene-content">
                                    {scene.content
                                        .split("\n")
                                        .map(
                                            (
                                                paragraph,
                                                index,
                                            ) =>
                                                paragraph.trim()
                                                ? (
                                                    <p key={index}>
                                                        {paragraph}
                                                    </p>
                                                )
                                                : null
                                        )}
                                </div>
                            </article>
                        ))}
                    </div>
                )}
            </section>

        </main>
    );
}