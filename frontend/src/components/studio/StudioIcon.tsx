import type { StudioIconName } from "./navigation";

// Small, locally authored outline icons; no prototype artwork or icon package.
const paths: Record<StudioIconName, string> = {
    home: "m3 10 9-7 9 7v10H15v-7H9v7H3Z",
    layers: "m3 7 9-5 9 5-9 5Z M3 12l9 5 9-5 M3 17l9 5 9-5",
    message: "M21 11a9 9 0 0 1-9 9H4l-3 3 2-7A9 9 0 1 1 21 11Z",
    film: "M5 3h14v18H5Z M5 8h14 M5 16h14 M9 3v18 M15 3v18",
    users: "M16 21v-3a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v3 M9 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M18 3a4 4 0 0 1 0 8 M22 21v-3a4 4 0 0 0-3-4",
    globe: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20 M2 12h20 M12 2c6 6 6 14 0 20 M12 2c-6 6-6 14 0 20",
    image: "M3 3h18v18H3Z M3 17l6-6 4 4 3-3 5 5 M8 7h.01",
    grid: "M3 3h7v7H3Z M14 3h7v7h-7Z M3 14h7v7H3Z M14 14h7v7h-7Z",
    download: "M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5",
    calendar: "M3 5h18v16H3Z M3 10h18 M7 2v6 M17 2v6",
    wallet: "M21 7H3V4h15v3 M3 7v14h18V7 M21 12h-6v5h6 M17 14.5h.01",
    help: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20 M9 8a3 3 0 0 1 6 0c0 3-3 2-3 5 M12 17h.01",
    settings: "m9 3-1 3-3 1-2 3 2 2v3l3 1 1 3h6l1-3 3-1v-3l2-2-2-3-3-1-1-3Z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6",
    menu: "M4 6h16 M4 12h16 M4 18h16",
    close: "m6 6 12 12 M18 6 6 18",
    plus: "M12 5v14 M5 12h14",
};

export function StudioIcon({ name, size = 18 }: { name: StudioIconName; size?: number }) {
    return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
