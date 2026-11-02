import { useState } from "react";
import { RecordEditor, type EditorField } from "./RecordEditor";

export interface WorldRecord {
    id: string;
    title: string;
    values: Record<string, string>;
}

interface Props {
    title: string;
    singular: string;
    fields: EditorField[];
    createFields?: EditorField[];
    records: WorldRecord[];
    onSave: (id: string | null, values: Record<string, string>) => Promise<void>;
}

export function WorldPanel({ title, singular, fields, createFields, records, onSave }: Props) {
    const [editing, setEditing] = useState<string | null>(null);
    const selected = records.find((record) => record.id === editing);
    return (
        <section className="panel" id={title.toLowerCase()}>
            <div className="panel-heading">
                <h2>{title} <small>({records.length})</small></h2>
                <button className="secondary-button" disabled={editing !== null} onClick={() => setEditing("new")}>Add {singular}</button>
            </div>
            {editing !== null && (
                <RecordEditor key={editing} fields={editing === "new" ? createFields ?? fields : fields} initial={selected?.values}
                    submitLabel={editing === "new" ? `Create ${singular}` : `Save ${singular}`}
                    onCancel={() => setEditing(null)} onSave={async (values) => {
                        await onSave(editing === "new" ? null : editing, values);
                        setEditing(null);
                    }} />
            )}
            {records.length === 0 && <p className="muted">No {title.toLowerCase()} yet. Add one to build your story world.</p>}
            <div className="record-list">
                {records.map((record) => (
                    <article className="world-record" key={record.id}>
                        <div className="panel-heading">
                            <h3>{record.title}</h3>
                            <button className="secondary-button" disabled={editing !== null}
                                onClick={() => setEditing(record.id)}>Edit {singular}</button>
                        </div>
                        <dl>{fields.filter((field) => field.name !== "name" && record.values[field.name]).map((field) => (
                            <div key={field.name}><dt>{field.label}</dt><dd>{record.values[field.name]}</dd></div>
                        ))}</dl>
                    </article>
                ))}
            </div>
        </section>
    );
}
