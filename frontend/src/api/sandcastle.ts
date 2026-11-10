import { resolveApiBase } from "./baseUrl";

export interface Story {
    story_id: string;
    user_id: string;
    title: string;
    premise: string | null;
    objective: string | null;
    language: string | null;
    primary_genre: string | null;
    secondary_genres: string[];
    status: string;
    created_at: string;
    updated_at: string;
}

export interface StoryCreateInput {
    title: string;
    premise?: string | null;
    objective?: string | null;
    language?: string | null;
    primary_genre?: string | null;
    secondary_genres?: string[];
}

export interface CanonEntry {
    canon_entry_id: string;
    story_id: string;
    type: string;
    key: string;
    value: string;
    status: string;
    created_at: string;
    updated_at: string;
}

export interface AuthorityDecision {
    decision_id: string;
    action_id: string;
    outcome: string;
    reason: string;
    confidence: number | null;
    evaluator: string;
    created_at: string;
}

export interface StoryAction {
    action_id: string;
    story_id: string;
    action_type: string;
    request: string;
    status: string;
    created_at: string;
    decision: AuthorityDecision | null;
}

export interface Scene {
    scene_id: string;
    story_id: string;
    source_action_id: string | null;
    sequence_number: number;
    title: string | null;
    content: string;
    status: string;
    created_at: string;
    updated_at: string;
}


export interface SceneGenerateResponse {
    action: StoryAction;
    scene: Scene | null;
}


export function listScenes(
    storyId: string,
) {
    return request<Scene[]>(
        `/stories/${storyId}/scenes`
    );
}


export function generateScene(
    storyId: string,
    sceneRequest: string,
) {
    return request<SceneGenerateResponse>(
        `/stories/${storyId}/scenes/generate`,
        {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/json",
            },
            body: JSON.stringify({
                request: sceneRequest,
            }),
        },
    );
}

export function updateScene(
    storyId: string,
    sceneId: string,
    title: string | null,
    content: string,
) {
    return request<Scene>(
        `/stories/${storyId}/scenes/${sceneId}`,
        {
            method: "PATCH",
            headers: {
                "Content-Type":
                    "application/json",
            },
            body: JSON.stringify({
                title,
                content,
            }),
        },
    );
}

const API_BASE_URL = resolveApiBase(
    import.meta.env.DEV,
    import.meta.env.VITE_API_BASE_URL,
);

export class ApiError extends Error {
    status: number;

    constructor(status: number, message: string) {
        super(message);
        this.status = status;
    }
}

export function loginUrl() {
    return `${API_BASE_URL}/auth/login`;
}

async function request<T>(
    path: string,
    options?: RequestInit,
): Promise<T> {
    const response = await fetch(
        `${API_BASE_URL}${path}`, {
            credentials: "include",
            ...options,
        },
    );

    if (!response.ok) {
        const payload = await response.json().catch(() => null);
        const detail = payload?.detail;
        const message = typeof detail === "string" ? detail
            : Array.isArray(detail) ? detail.map((item: { msg: string }) => item.msg).join("; ")
            : `Request failed: ${response.status}`;
        throw new ApiError(response.status, message);
    }

    const contentType = response.headers.get("content-type");

    if (
        !contentType?.includes("application/json")
    ) {
        return undefined as T;
    }

    return response.json();
}


export function listStories() {
    return request<Story[]>("/stories");
}

export function createStory (
    input: StoryCreateInput,
) {
    return request<Story>(
        "/stories",
        {
            method: "POST",
            headers: {
                "Content-Type":"application/json",
            },
            body: JSON.stringify(input),
        },
    );
}

export function getStory(
    storyId: string,
) {
    return request<Story>(
        `/stories/${storyId}`
    );
}


export function listCanon(
    storyId: string,
) {
    return request<CanonEntry[]>(
        `/stories/${storyId}/canon`
    );
}


export function createCanonEntry(
    storyId: string,
    type: string,
    key: string,
    value: string,
) {
    return request<CanonEntry>(
        `/stories/${storyId}/canon`,
        {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/json",
            },
            body: JSON.stringify({
                type,
                key,
                value,
            }),
        }
    );
}


export function listActions(
    storyId: string,
) {
    return request<StoryAction[]>(
        `/stories/${storyId}/actions`
    );
}


export function createAction(
    storyId: string,
    actionType: string,
    actionRequest: string,
) {
    return request<StoryAction>(
        `/stories/${storyId}/actions`,
        {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/json",
            },
            body: JSON.stringify({
                action_type: actionType,
                request: actionRequest,
            }),
        },
    );
}

export interface AuthUser {
    user_id: string;
    email: string;
    name: string | null;
}

export async function getCurrentUser(): Promise<AuthUser | null> {
    try {
        return await request<AuthUser>("/auth/me");
    } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
    }
}

export async function logout() {
    await request<void>(
        "/auth/logout",
        {
            method: "POST",
        },
    );
}


export interface CharacterInput {
    name: string;
    description: string;
    appearance: string;
    outfit: string;
    personality: string;
}

export interface Character extends CharacterInput {
    character_id: string;
    story_id: string;
    created_at: string;
    updated_at: string;
}

export interface PlaceInput {
    name: string;
    description: string;
    appearance: string;
    atmosphere: string;
}

export interface Place extends PlaceInput {
    place_id: string;
    story_id: string;
    created_at: string;
    updated_at: string;
}

export interface CanonInput {
    type: string;
    key: string;
    value: string;
}

function write<T>(path: string, method: "POST" | "PATCH", body: object) {
    return request<T>(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

export function updateStory(storyId: string, input: Partial<StoryCreateInput>) {
    return write<Story>(`/stories/${storyId}`, "PATCH", input);
}

export function listCharacters(storyId: string) {
    return request<Character[]>(`/stories/${storyId}/characters`);
}

export function saveCharacter(storyId: string, id: string | null, input: CharacterInput) {
    return write<Character>(`/stories/${storyId}/characters${id ? `/${id}` : ""}`, id ? "PATCH" : "POST", input);
}

export function listPlaces(storyId: string) {
    return request<Place[]>(`/stories/${storyId}/places`);
}

export function savePlace(storyId: string, id: string | null, input: PlaceInput) {
    return write<Place>(`/stories/${storyId}/places${id ? `/${id}` : ""}`, id ? "PATCH" : "POST", input);
}

export function updateCanon(storyId: string, id: string, input: Partial<CanonInput> & { status?: "approved" | "superseded" }) {
    return write<CanonEntry>(`/stories/${storyId}/canon/${id}`, "PATCH", input);
}

export function createScene(storyId: string, title: string | null, content: string) {
    return write<Scene>(`/stories/${storyId}/scenes`, "POST", { title, content });
}

export interface GuidanceProfileInput {
    audience: "child" | "teen" | "adult";
    maturity_rating: "general" | "mild" | "moderate" | "mature";
    tone: string | null;
    genre: string | null;
    guidance_notes: string | null;
    average_rating: number | null;
    rating_count: number;
    feedback_tags: string[];
}

export interface GuidanceProfile extends GuidanceProfileInput {
    story_id: string;
    created_at: string | null;
    updated_at: string | null;
}

export interface NextSceneSuggestion { id: string; title: string; text: string }

export function getGuidanceProfile(storyId: string) {
    return request<GuidanceProfile>(`/stories/${storyId}/guidance/profile`);
}

export function saveGuidanceProfile(storyId: string, profile: GuidanceProfileInput) {
    return request<GuidanceProfile>(`/stories/${storyId}/guidance/profile`, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(profile),
    });
}

export function suggestNextScene(storyId: string) {
    return write<{ story_id: string; suggestions: NextSceneSuggestion[] }>(`/stories/${storyId}/workflow/steps/narrative_guidance`, "POST", {});
}

export interface WorkflowConfig {
    steps: { step_id: string; enabled: boolean }[];
    order: string[];
    guidance: { count: number; recent_scene_count: number };
    review: { require_before_media: boolean; review_new: boolean; review_conflicts: boolean; review_uncertain: boolean };
    media: { aspect_ratio: string; output_format: "image" | "webtoon" };
    adaptation: { sensitivity_hints: string[] };
    references: { character_ids: string[] | null; place_ids: string[] | null; artifact_ids: string[] };
}
export interface WorkflowTemplate {
    workflow_template_id: string; version: number; name: string; description: string;
    difficulty_minimum: string; configuration: WorkflowConfig;
}
export interface Difficulty { id: string; label: string; capabilities: string[] }
export interface StoryWorkflow {
    story_id: string; difficulty: string; workflow_template_id: string; template_version: number;
    template_name: string; configuration: WorkflowConfig; capabilities: string[];
    step_definitions: { step_id: string; label: string; required: boolean; available: boolean; dependencies: string[] }[];
}
export function getStoryWorkflow(storyId: string) { return request<StoryWorkflow>(`/stories/${storyId}/workflow`); }
export function listWorkflowTemplates() { return request<WorkflowTemplate[]>("/workflows/templates"); }
export function listDifficulties() { return request<Difficulty[]>("/workflows/difficulties"); }
export function saveStoryWorkflow(storyId: string, selection: Pick<StoryWorkflow, "difficulty" | "workflow_template_id" | "template_version" | "configuration">) {
    return request<StoryWorkflow>(`/stories/${storyId}/workflow`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(selection) });
}
export function workflowStep<T>(storyId: string, stepId: string, sceneId?: string) {
    return write<T>(`/stories/${storyId}/workflow/steps/${stepId}`, "POST", { scene_id: sceneId ?? null });
}

export interface CanonCandidateSummary {
    canon_candidate_id: string; status: string; classification: string; key: string; value: string; reasoning: string;
    evidence: string; subject_name: string | null; subject_id: string | null;
}
export function reviewCanonCandidate(storyId: string, candidateId: string, approved: boolean, replace: boolean, uncertain: boolean) {
    return write<unknown>(`/stories/${storyId}/canon/candidates/${candidateId}/${approved ? "approve" : "reject"}`, "POST",
        approved ? { replace_conflicts: replace, accept_uncertain: uncertain } : {});
}

export function listCanonCandidates(storyId: string) {
    return request<CanonCandidateSummary[]>(`/stories/${storyId}/canon/candidates`);
}
export interface Universe { universe_id: string; name: string; description: string }
export interface UniverseReference { reference_id: string; canon_object_id: string; canon_version_id: string }
export function listUniverses() { return request<Universe[]>("/universes"); }
export function listUniverseMembers(id: string) { return request<{ story_id: string }[]>(`/universes/${id}/stories`); }
export function listUniverseReferences(id: string) { return request<UniverseReference[]>(`/universes/${id}/canon/references`); }
export function listCanonVersions(id: string) {
    return request<{ canon_version_id: string; version_number: number; data: Record<string, unknown> }[]>(`/canon/library/${id}/versions`);
}
export interface Artifact { artifact_id: string; display_name: string | null; source: string; media_type: string }
export interface ReferenceBinding { reference_id: string; artifact_id: string; target_type: string; target_id: string; role: string; label: string | null }
export function listArtifacts(storyId: string) { return request<Artifact[]>(`/artifacts?story_id=${encodeURIComponent(storyId)}`); }
export function listReferenceBindings(storyId: string) { return request<ReferenceBinding[]>(`/stories/${storyId}/references`); }
