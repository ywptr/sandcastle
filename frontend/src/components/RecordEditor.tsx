import { useState, type FormEvent } from "react";

export interface EditorField {
    name: string;
    label: string;
    required?: boolean;
    multiline?: boolean;
    maxLength?: number;
    options?: string[];
}

interface Props {
    fields: EditorField[];
    initial?: Record<string, string>;
    submitLabel?: string;
    onSave: (values: Record<string, string>) => Promise<void>;
    onCancel: () => void;
}

export function RecordEditor({ fields, initial = {}, submitLabel = "Save", onSave, onCancel }: Props) {
    const [values, setValues] = useState<Record<string, string>>(() => ({
        ...Object.fromEntries(fields.map((field) => [field.name, field.options?.[0] ?? ""])),
        ...initial,
    }));
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (saving) return;
        const clean = Object.fromEntries(fields.map((field) => [field.name, (values[field.name] ?? "").trim()]));
        if (fields.some((field) => field.required && !clean[field.name])) {
            setError("Please fill in the required fields.");
            return;
        }
        setSaving(true);
        setError(null);
        try {
            await onSave(clean);
        } catch (failure) {
            setError(failure instanceof Error ? failure.message : "Could not save. Please retry.");
        } finally {
            setSaving(false);
        }
    }

    return (
        <form className="record-editor" onSubmit={submit}>
            <fieldset disabled={saving}>
                {fields.map((field) => {
                    const props = {
                        value: values[field.name] ?? "",
                        required: field.required,
                        maxLength: field.maxLength,
                        onChange: (event: { target: { value: string } }) =>
                            setValues((current) => ({ ...current, [field.name]: event.target.value })),
                    };
                    return (
                        <label key={field.name}>
                            <span>{field.label}{field.required ? " *" : ""}</span>
                            {field.options ? (
                                <select {...props}>
                                    {field.options.map((option) => <option key={option} value={option}>{option}</option>)}
                                </select>
                            ) : field.multiline ? <textarea {...props} rows={field.name === "content" ? 12 : 3} />
                                : <input {...props} />}
                        </label>
                    );
                })}
                {error && <p className="error" role="alert">{error}</p>}
                <div className="editor-actions">
                    <button type="button" className="secondary-button" onClick={onCancel}>Cancel</button>
                    <button type="submit" className="primary-button">{saving ? "Saving…" : submitLabel}</button>
                </div>
            </fieldset>
        </form>
    );
}
