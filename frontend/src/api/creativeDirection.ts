import { request, write, type Story, type StoryCreateInput } from "./sandcastle";
export const formats = ["story", "webtoon", "short_drama", "story_reel"] as const;
export type CreationFormat = typeof formats[number];
export const ratings = ["all_ages", "teen_13", "young_adult_16", "mature_18"] as const;
export const visuals = ["match_style", "anime_2d", "korean_webtoon", "cinematic_realism", "illustrated_storybook", "painterly", "stylized_3d"] as const;
export interface StorytellingStyle { id: string; version: string; name: {en:string;id:string}; summary: {en:string;id:string}; region: string; supported_formats: CreationFormat[]; narrative_guidance: string; dialogue_guidance: string; image_guidance: string; video_guidance: string; localized_guidance?: {id: {narrative:string;dialogue:string;image:string;video:string}}; status: string; }
export interface DirectionInput { target_format: CreationFormat; storytelling_style_id: string; style_version: string; audience_rating: string; visual_style: string; cultural_setting: string | null; historical_era: string | null; tone: string | null; tropes: string[]; expected_revision: number; }
export interface DirectionSnapshot { direction_id: string; story_id: string; revision: number; direction: DirectionInput & {language_at_approval?:string|null}; style: StorytellingStyle; approved_at: string; }
export interface Recommendation {target_format:CreationFormat;primary_genre:string|null;secondary_genres:string[];language:string|null;storytelling_style_id:string;audience_rating:string;visual_style:string;tone:string|null;rationale:string;warnings:string[];}
export function listStyles(){return request<StorytellingStyle[]>("/styles");}
export function recommendDirection(idea:string,target_format:CreationFormat){return write<Recommendation>("/styles/recommend","POST",{idea,target_format});}
export function startSeries(story:StoryCreateInput,creative_direction:DirectionInput){return write<Story>("/stories/start","POST",{story,creative_direction});}
export function getDirection(storyId:string){return request<DirectionSnapshot|null>(`/stories/${storyId}/creative-direction`);}
export function saveDirection(storyId:string,input:DirectionInput){const {language_at_approval: _historicalLanguage,...editable} = input as DirectionSnapshot["direction"]; return write<DirectionSnapshot>(`/stories/${storyId}/creative-direction`,"PUT",editable);}
export function initialDirection():DirectionInput { return {target_format:"story",storytelling_style_id:"american_cinematic_drama",style_version:"1.0.0",audience_rating:"teen_13",visual_style:"match_style",cultural_setting:null,historical_era:null,tone:null,tropes:[],expected_revision:0}; }
export interface ImportProposal {story:{proposed_title:string|null;premise:string|null;objective:string|null;detected_language:string;primary_genre:string;secondary_genres:string[];evidence:string[]};characters: {name:string; evidence:string[]}[];places:{name:string;evidence:string[]}[];canon_candidates:{key:string;value:string;evidence:string[]}[];warnings:string[];}
export function analyzeStory(content:string,source_type:string){return write<ImportProposal>("/stories/import/analyze","POST",{content,source_type});}
