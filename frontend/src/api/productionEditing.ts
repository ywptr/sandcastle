import type { Production, ProductionBeat, ProductionPlan } from "./production";

export const formatNames = { webtoon: "Webtoon", short_drama: "Short Drama", story_reel: "Story Reel" };
export function productionBeats(production: Production): ProductionBeat[] {
    return production.target_format === "webtoon" ? production.panels : production.target_format === "short_drama" ? production.shots : production.beats;
}
export function replaceBeats(plan: ProductionPlan, beats: ProductionBeat[]): ProductionPlan {
    const production = structuredClone(plan.production);
    if (production.target_format === "webtoon") production.panels = beats.map((b, i) => ({ ...b, panel_number: i + 1 })) as typeof production.panels;
    else if (production.target_format === "short_drama") {
        production.shots = beats.map((b, i) => ({ ...b, shot_number: i + 1 })) as typeof production.shots;
        production.target_duration_seconds = production.shots.reduce((sum, b) => sum + b.estimated_duration, 0);
    } else {
        production.beats = beats.map((b, i) => ({ ...b, beat_number: i + 1 })) as typeof production.beats;
        production.target_duration_seconds = production.beats.reduce((sum, b) => sum + b.duration, 0);
    }
    return { ...plan, production, compiled_instructions: [] };
}
export function moveBeat(plan: ProductionPlan, index: number, offset: number): ProductionPlan {
    const beats = [...productionBeats(plan.production)], target = index + offset;
    if (target < 0 || target >= beats.length) return plan;
    [beats[index], beats[target]] = [beats[target], beats[index]];
    const overrides = plan.overrides.map((o) => ({ ...o, beat_number: o.beat_number === index + 1 ? target + 1 : o.beat_number === target + 1 ? index + 1 : o.beat_number }));
    return replaceBeats({ ...plan, overrides }, beats);
}
export async function sceneDigest(scene: { content: string; title: string | null }): Promise<string> {
    const bytes = new TextEncoder().encode(JSON.stringify({ content: scene.content, title: scene.title }));
    const hash = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join("");
}
