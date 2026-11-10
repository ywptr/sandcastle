import { useState } from "react";
import { createStory, type Story } from "../api/sandcastle";
import { useI18n } from "../i18n/context";
import { StoryMetadataForm } from "./StoryMetadataForm";

export function StorySelector({ stories, selectedStoryId, onSelect, onCreated, onStart }: {
    onStart: () => void; stories: Story[]; selectedStoryId: string | null; onSelect: (story: Story) => void; onCreated: (story: Story) => void;
}) {
    const {t} = useI18n();
    const [creating, setCreating] = useState(false);
    return <aside className="story-sidebar">
        <div className="story-sidebar-heading"><div><span className="eyebrow">{t("series.studio")}</span><h2>{t("nav.series")}</h2></div>
            <button type="button" className="primary-button" onClick={onStart}>{t("series.new")}</button></div>
        <p className="muted">{t("series.hint")}</p>
        <button type="button" className="text-button" onClick={() => setCreating((v) => !v)}>{t("create.basic")}</button>
        {creating && <section className="story-create-form"><h3>{t("create.new")}</h3><StoryMetadataForm onCancel={() => setCreating(false)} onSave={async (input) => {
            const story = await createStory(input); onCreated(story); setCreating(false);
        }} /></section>}
        {!stories.length && <p className="empty-state">{t("series.empty")}</p>}
        <div className="story-list">{stories.map((story, index) => <button type="button" key={story.story_id}
            aria-current={story.story_id === selectedStoryId ? "true" : undefined}
            className={`story-list-item ${story.story_id === selectedStoryId ? "active" : ""}`} onClick={() => onSelect(story)}>
            <span className="series-cover" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
            <strong>{story.title}</strong><span>{story.premise || t("series.possibility")}</span>
            <small>{t(`series.status.${story.status}`)} · {story.primary_genre ? t(`genre.${story.primary_genre}`) : t("format.story")}{story.language ? ` · ${story.language}` : ""}</small>
        </button>)}</div>
    </aside>;
}
