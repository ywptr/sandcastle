export interface Story {
    story_id: string;
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

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL
    ?? "/api";

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
        throw new Error(
            `Request failed: ${response.status}`
        );
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

export function getCurrentUser() {
    return request<AuthUser>(
        "/auth/me"
    );
}

export async function logout() {
    await request<void>(
        "/auth/logout",
        {
            method: "POST",
        },
    );
}
