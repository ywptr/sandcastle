import { useEffect, useState } from "react";

import {
    createCanonEntry,
    createAction,
    listActions,
    listCanon,
    type CanonEntry,
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

            await createAction(
                story.story_id,
                "scene.generate",
                request,
            );

            setActionRequest("");

            await loadActions();
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
                            ? "Evaluating…"
                            : "Submit action"}
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

        </main>
    );
}