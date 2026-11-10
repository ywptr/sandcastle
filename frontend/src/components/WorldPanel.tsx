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
    onSave: (id: string | null, values: Record<string, string>) => Promise<void | string>;
}

export function WorldPanel({ title, singular, fields, createFields, records, onSave }: Props) {
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [editing, setEditing] = useState<string | null>(null);
    const selected = records.find((record) => record.id === editing);
    const detail = records.find((record) => record.id === selectedId) ?? records[0];
    return (
        <section className="panel" id={title.toLowerCase()}>
            <div className="panel-heading">
                <h2>{title} <small>({records.length})</small></h2>
                <button className="secondary-button" disabled={editing !== null} onClick={() => setEditing("new")}>Add {singular}</button>
            </div>
            {records.length === 0 && <p className="muted">No {title.toLowerCase()} yet. Add one to build your story world.</p>}
            <div className="record-browser"><nav className="record-picker" aria-label={`${title} list`}>{records.map((record) => <button type="button" key={record.id} disabled={editing !== null} aria-current={detail?.id === record.id ? "true" : undefined} onClick={() => { setSelectedId(record.id); setEditing(null); }}>{record.title}<small>{record.values.status || record.values.description?.slice(0, 90)}</small></button>)}</nav><div className="record-list">            {editing !== null && (
                <RecordEditor key={editing} fields={editing === "new" ? createFields ?? fields : fields} initial={selected?.values}
                    submitLabel={editing === "new" ? `Create ${singular}` : `Save ${singular}`}
                    onCancel={() => setEditing(null)} onSave={async (values) => {
                        const savedId = await onSave(editing === "new" ? null : editing, values);
                        if (savedId) setSelectedId(savedId);
                        else if (editing !== "new") setSelectedId(editing);
                        setEditing(null);
                    }} />
            )}

                {(editing === null && detail ? [detail] : []).map((record) => (
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
            </div></div>
        </section>
    );
}
