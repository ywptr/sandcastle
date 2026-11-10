import type { CanonEntry, Character, Place, StoryCreateInput, WorkflowConfig } from "./sandcastle";
import { request, write } from "./sandcastle";

export type TargetFormat = "webtoon" | "short_drama" | "story_reel";
export type Framing = "wide" | "full" | "medium" | "close_up" | "detail" | "overhead";
export interface VisualBeat {
    narrative_purpose: string; source_excerpt: string; visual_description: string;
    character_ids: string[]; place_ids: string[]; artifact_ids: string[]; continuity_notes: string[];
}
export interface WebtoonPanel extends VisualBeat { panel_number: number; dialogue: string; caption: string; framing: Framing }
export interface DramaShot extends VisualBeat { shot_number: number; estimated_duration: number; shot_scale: Framing; camera_direction: string; performance_direction: string; dialogue: string; voiceover: string; audio_or_ambience: string }
export interface ReelBeat extends VisualBeat { beat_number: number; duration: number; on_screen_text: string; voiceover: string; transition_hint: string }
export type Production = { target_format: "webtoon"; panels: WebtoonPanel[]; reading_order: "top_to_bottom" | "left_to_right" | "right_to_left"; layout_hint: string }
    | { target_format: "short_drama"; target_duration_seconds: number; shots: DramaShot[]; audio_direction: string }
    | { target_format: "story_reel"; target_duration_seconds: number; beats: ReelBeat[]; narration_text_strategy: string; visual_strategy: string };
export type ProductionBeat = WebtoonPanel | DramaShot | ReelBeat;
export interface ProductionPlan {
    plan_id: string; story_id: string; scene_id: string; target_format: TargetFormat; source_digest: string; context_digest: string;
    summary: string; continuity_notes: string[]; warnings: { code: string; message: string }[]; production: Production;
    continuity_context: { story: StoryCreateInput; characters: Character[]; places: Place[]; canon: CanonEntry[];
        references: { kind: string; reference_id: string; role?: string | null }[]; reference_bindings?: { binding_id: string; artifact_id: string; target_type: string; target_id: string; role: string }[]; guidance: { audience: string; maturity_rating: string }; workflow_configuration: WorkflowConfig };
    instruction: string | null; overrides: { beat_number: number; instruction: string }[]; compiler_version: "production-v1";
    compiled_instructions: { beat_number: number; compiled: string; override: string | null; effective: string }[]; created_at: string;
}
export interface ProductionManifest { media_plan_id: string; story_id: string; requests: { media_request_id: string; media_type: string; purpose: string; prompt: string; references: unknown[]; context: unknown; aspect_ratio: string | null; created_at: string }[]; created_at: string }
export interface ApprovedProduction { adaptation_id: string; revision: number; plan: ProductionPlan; manifest: ProductionManifest; source_changed: boolean; context_changed: boolean; approved_at: string }
const base = (storyId: string, sceneId: string) => `/stories/${storyId}/scenes/${sceneId}/adaptations`;
export function translateProduction(storyId: string, sceneId: string, target_format: TargetFormat, instruction: string | null) {
    return write<ProductionPlan>(base(storyId, sceneId), "POST", { target_format, instruction });
}
export function compileProduction(storyId: string, sceneId: string, plan: ProductionPlan) {
    return write<{ plan: ProductionPlan; manifest: ProductionManifest }>(base(storyId, sceneId) + "/compile", "POST", { plan });
}
export function approveProduction(storyId: string, sceneId: string, plan: ProductionPlan) {
    return write<ApprovedProduction>(base(storyId, sceneId) + "/approve", "POST", { approved: true, plan });
}
export function listProductions(storyId: string, sceneId: string) { return request<ApprovedProduction[]>(base(storyId, sceneId)); }
