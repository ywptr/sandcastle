import { useState, type ReactNode } from "react";

// Load a section on first use, then keep its controller and unsaved draft in memory.
export function RetainedPanel({ active, children }: { active: boolean; children: ReactNode }) {
    const [visited, setVisited] = useState(active);
    if (active && !visited) setVisited(true);
    return <div hidden={!active}>{(active || visited) ? children : null}</div>;
}
