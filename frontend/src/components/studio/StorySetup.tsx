import type { Story } from "../../api/sandcastle";
import { useI18n } from "../../i18n/context";
import { CreativeDirectionPanel } from "../CreativeDirectionPanel";
import { workspaceCopy } from "./workspaceCopy";

export function StorySetup({ story, onEdit, onOpenScenes }: {
    story: Story; onEdit: () => void; onOpenScenes: () => void;
}) {
    const {t, locale} = useI18n();
    const copy = workspaceCopy[locale];
    return <div className="studio-story-setup">
        <p className="setup-saved-note">{copy.saved}</p>
        <dl className="setup-values">
            <div><dt>{copy.genre}</dt><dd>{[story.primary_genre, ...story.secondary_genres ?? []].filter(Boolean).map(g => t(`genre.${g}`)).join(" · ") || t("common.notSet")}</dd></div>
            <div><dt>{copy.language}</dt><dd>{story.language ? t(`language.${story.language}`) : t("common.notSet")}</dd></div>
        </dl>
        <p className="setup-language-note">{copy.languageNote}</p>
        <button type="button" className="secondary-button" onClick={onEdit}>{t("workspace.editDetails")}</button>
        <CreativeDirectionPanel storyId={story.story_id} storyLanguage={story.language} onOpenScenes={onOpenScenes} />
    </div>;
}
