import { useState } from "react";
import { createStory, type Story } from "../api/sandcastle";
import { StoryMetadataForm } from "./StoryMetadataForm";

export function StorySelector({ stories, selectedStoryId, onSelect, onCreated }: {
    stories: Story[]; selectedStoryId: string | null; onSelect: (story: Story) => void; onCreated: (story: Story) => void;
}) {
    const [creating, setCreating] = useState(false);
    return <aside className="story-sidebar">
        <div className="story-sidebar-heading"><div><span className="eyebrow">Your studio</span><h2>Series</h2></div>
            <button type="button" className="primary-button" onClick={() => setCreating(true)}>+ New series</button></div>
        <p className="muted">Every world starts with an idea.</p>
        {creating && <section className="story-create-form"><h3>Start something new</h3><StoryMetadataForm onCancel={() => setCreating(false)} onSave={async (input) => {
            const story = await createStory(input); onCreated(story); setCreating(false);
        }} /></section>}
        {!stories.length && <p className="empty-state">Your first series belongs here. Start with a title; develop the details as you go.</p>}
        <div className="story-list">{stories.map((story, index) => <button type="button" key={story.story_id}
            aria-current={story.story_id === selectedStoryId ? "true" : undefined}
            className={`story-list-item ${story.story_id === selectedStoryId ? "active" : ""}`} onClick={() => onSelect(story)}>
            <span className="series-cover" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
            <strong>{story.title}</strong><span>{story.premise || "An unwritten possibility"}</span>
            <small>{story.status} · {story.primary_genre?.replaceAll("_", " ") || "Story"}{story.language ? ` · ${story.language}` : ""}</small>
        </button>)}</div>
    </aside>;
}
