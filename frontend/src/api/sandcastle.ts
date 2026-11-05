import { resolveApiBase } from "./baseUrl";

export interface Story {
    story_id: string;
    user_id: string;
    title: string;
    premise: string | null;
    objective: string | null;
    status: string;
    created_at: string;
    updated_at: string;
}

export interface StoryCreateInput {
    title: string;
    premise?: string;
    objective?: string;
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
    return write<{ story_id: string; suggestions: NextSceneSuggestion[] }>(`/stories/${storyId}/guidance/next-scene`, "POST", {});
}
