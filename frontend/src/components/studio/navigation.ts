export type StudioDestination = "home" | "series" | "workspace" | "characters" | "world" | "library" | "settings";
export type StudioIconName = "home" | "layers" | "message" | "film" | "users" | "globe" | "image" | "grid" | "download" | "calendar" | "wallet" | "help" | "settings" | "menu" | "close" | "plus";

interface StudioNavigationItem {
    id: string;
    label: string;
    icon: StudioIconName;
    destination?: StudioDestination;
    needsStory?: boolean;
    divider?: boolean;
}

// Both desktop and mobile render this same capability-aware navigation model.
export const studioNavigation: readonly StudioNavigationItem[] = [
    { id: "home", label: "nav.home", icon: "home", destination: "home" },
    { id: "series", label: "studio.mySeries", icon: "layers", destination: "series" },
    { id: "workspace", label: "studio.workspace", icon: "message", destination: "workspace", needsStory: true },
    { id: "episodes", label: "studio.episodeEditor", icon: "film" },
    { id: "characters", label: "workspace.characters", icon: "users", destination: "characters", needsStory: true },
    { id: "world", label: "studio.world", icon: "globe", destination: "world", needsStory: true },
    { id: "library", label: "studio.library", icon: "image", destination: "library", needsStory: true },
    { id: "templates", label: "studio.templates", icon: "grid" },
    { id: "export", label: "studio.export", icon: "download", divider: true },
    { id: "publish", label: "studio.publish", icon: "calendar" },
    { id: "billing", label: "studio.billing", icon: "wallet" },
    { id: "help", label: "studio.help", icon: "help" },
    { id: "settings", label: "nav.settings", icon: "settings", destination: "settings" },
];
