// Mirrors backend/app/stories/metadata.py; shared by creation and editing.
export const languages = { en: "English", id: "Indonesian", ja: "Japanese", ko: "Korean", "zh-CN": "Simplified Chinese", fr: "French", de: "German", es: "Spanish", und: "Undetermined" };
export const genres = ["fantasy", "science_fiction", "mystery", "thriller", "romance", "horror", "adventure", "drama", "comedy", "historical", "slice_of_life", "other", "unknown"];
export const genreLabel = (value: string) => value.replaceAll("_", " ");

