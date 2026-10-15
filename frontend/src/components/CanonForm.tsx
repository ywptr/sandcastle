import { useState } from "react";

import {
    type CanonEntry,
} from "../api/sandcastle";


const CANON_TYPES = [
    "character",
    "outfit",
    "world",
    "timeline",
    "relationship",
    "rule",
    "plot",
];


interface CanonFormProps {
    onCreate: (
        type: string,
        key: string,
        value: string,
    ) => Promise<CanonEntry>;
}


export function CanonForm({
    onCreate,
}: CanonFormProps) {
    const [type, setType] =
        useState("character");

    const [key, setKey] =
        useState("");

    const [value, setValue] =
        useState("");

    const [submitting, setSubmitting] =
        useState(false);

    const [error, setError] =
        useState<string | null>(null);


    function resetForm() {
        setType("character");
        setKey("");
        setValue("");
        setError(null);
    }


    async function handleSubmit() {
        const cleanKey = key.trim();
        const cleanValue = value.trim();

        if (!cleanKey || !cleanValue) {
            setError(
                "Key and value are required."
            );
            return;
        }

        try {
            setSubmitting(true);
            setError(null);

            await onCreate(
                type,
                cleanKey,
                cleanValue,
            );

            resetForm();

        } catch (error) {
            setError(
                error instanceof Error
                    ? error.message
                    : "Failed to create canon entry"
            );

        } finally {
            setSubmitting(false);
        }
    }


    return (
        <div className="canon-form">

            <select
                value={type}
                onChange={(event) =>
                    setType(event.target.value)
                }
            >
                {CANON_TYPES.map((item) => (
                    <option
                        key={item}
                        value={item}
                    >
                        {item}
                    </option>
                ))}
            </select>

            <input
                placeholder="Key"
                value={key}
                onChange={(event) =>
                    setKey(event.target.value)
                }
            />

            <textarea
                placeholder="Canon fact"
                value={value}
                onChange={(event) =>
                    setValue(event.target.value)
                }
            />

            {error && (
                <div className="error">
                    {error}
                </div>
            )}

            <button
                className="primary-button"
                disabled={submitting}
                onClick={handleSubmit}
            >
                {submitting
                    ? "Adding…"
                    : "Add canon"}
            </button>

        </div>
    );
}