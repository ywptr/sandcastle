import { useEffect, useRef, useState, type FormEvent } from "react";
import { listLLMProviders, listLLMRoles, removeLLMCredentials, saveLLMProvider, saveLLMRole,
    type LLMProviderConfig, type LLMProviderId, type LLMRoleBinding } from "../api/sandcastle";
import { aiCopy, canRoute, providerNames, providerTasks, roleNames, settingsError, type SettingsDetail } from "../settings/copy";

function ProviderCard({ provider, roles, detail, onSaved }: {
    provider: LLMProviderConfig; roles: LLMRoleBinding[]; detail: SettingsDetail; onSaved: (value: LLMProviderConfig) => Promise<void>;
}) {
    const [configuring, setConfiguring] = useState(false);
    const [enabled, setEnabled] = useState(provider.enabled);
    const [model, setModel] = useState(provider.config.default_model ?? "");
    const [busy, setBusy] = useState(false);
    const [removing, setRemoving] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const secretInput = useRef<HTMLInputElement>(null);
    const name = providerNames[provider.provider];
    const usedFor = providerTasks(provider, roles);
    const affected = roles.filter((r) => r.provider === provider.provider && !r.available);
    async function update(input: Parameters<typeof saveLLMProvider>[1], success: string) {
        setBusy(true); setMessage(null); setError(null);
        try { const saved = await saveLLMProvider(provider.provider, input); setEnabled(saved.enabled); await onSaved(saved); setMessage(success); }
        catch (failure) { setError(settingsError(failure)); } finally { setBusy(false); }
    }
    async function save(event: FormEvent) {
        event.preventDefault(); if (busy) return;
        const key = secretInput.current?.value ?? "";
        if (secretInput.current) secretInput.current.value = "";
        await update({ enabled, config: { default_model: model.trim() || null }, ...(key ? { credentials: { api_key: key } } : {}) }, aiCopy.saved);
    }
    async function remove() {
        if (busy) return; setBusy(true); setError(null); setMessage(null);
        if (secretInput.current) secretInput.current.value = "";
        try { const saved = await removeLLMCredentials(provider.provider); setEnabled(false); await onSaved(saved); setRemoving(false); setMessage(aiCopy.removed); }
        catch (failure) { setError(settingsError(failure)); } finally { setBusy(false); }
    }
    function configure() { setModel(provider.config.default_model ?? ""); setEnabled(provider.enabled); setConfiguring((v) => !v); setError(null); }
    return <section className="panel provider-card"><div className="panel-heading"><h3>{name}</h3><span className="status-badge">Supported</span></div>
        <div className="provider-status"><strong>{provider.has_credentials ? "Connected" : "Not connected"}</strong><span>{provider.enabled ? "Enabled" : "Disabled"}</span></div>
        {provider.has_credentials && <p className="muted">Key saved · not yet verified by a live call</p>}
        {detail !== "easy" && <p>Default model: {provider.config.default_model || "Not set"}</p>}
        <p>Selected: {usedFor.length ? "yes" : "no"}</p><p className="muted">Used for: {usedFor.join(", ") || "No tasks currently selected"}</p>
        {provider.has_credentials && !provider.config.default_model && <p className="context-note">Add a default model in Configure before this provider can handle tasks.</p>}
        {affected.length > 0 && <p role="status" className="context-note">Routing affected: {affected.map((r) => roleNames[r.role]).join(", ")} unavailable. Enable this provider or choose Automatic in Advanced routing.</p>}
        <div className="button-row"><button type="button" className="secondary-button" aria-expanded={configuring} disabled={busy} onClick={configure}>{configuring ? `Close ${name} configuration` : `Configure ${name}`}</button>
            <button type="button" className="secondary-button" disabled={busy || configuring || !provider.has_credentials} onClick={() => update({ enabled: !provider.enabled }, provider.enabled ? "Personal provider disabled. Explicitly bound tasks may be unavailable." : "Personal provider enabled.")}>{provider.enabled ? `Disable ${name}` : `Enable ${name}`}</button></div>
        {configuring && <form onSubmit={save}><fieldset disabled={busy}><legend>Configure {name}</legend>
            <label className="checkbox-label"><input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />Enable {name}</label>
            <label>Default model for {name}<input value={model} maxLength={160} onChange={(e) => setModel(e.target.value)} placeholder="Provider model ID" autoComplete="off" /></label>
            <p className="muted">A model ID is required for personal AI requests. This is connection setup; task-specific model routing is in advanced Settings views.</p>
            <label>{name} API key<input ref={secretInput} type="password" autoComplete="new-password" spellCheck={false} maxLength={4096} placeholder={provider.has_credentials ? "Leave blank to keep saved credential" : "Enter your API key"} /></label>
            <p className="muted">Encrypted on the server. Blank keeps the saved key; a new key replaces it. The input clears when submitted.</p>
            <button type="submit" className="primary-button">{busy ? "Saving…" : `Save ${name}`}</button>
        </fieldset></form>}
        {provider.has_credentials && !removing && <button type="button" className="secondary-button" disabled={busy} onClick={() => setRemoving(true)}>Remove {name} credential</button>}
        {removing && <div className="context-note"><p>{aiCopy.removal}</p><div className="button-row"><button type="button" className="secondary-button" disabled={busy} onClick={() => setRemoving(false)}>Keep credential</button><button type="button" className="secondary-button" disabled={busy} onClick={remove}>Confirm removal for {name}</button></div></div>}
        {message && <p role="status">{message}</p>}{error && <p role="alert" className="error">{error}</p>}
    </section>;
}

function RolePreference({ binding, providers, detail, onSaved }: { binding: LLMRoleBinding; providers: LLMProviderConfig[]; detail: SettingsDetail; onSaved: (roles: LLMRoleBinding[]) => void }) {
    const [selected, setSelected] = useState(binding.provider ?? "");
    const [model, setModel] = useState(binding.model ?? "");
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const label = roleNames[binding.role];
    return <form className="role-preference" onSubmit={async (e) => {
        e.preventDefault(); if (busy) return; setBusy(true); setError(null); setMessage(null);
        try { onSaved(await saveLLMRole(binding.role, selected ? selected as LLMProviderId : null, selected ? model.trim() || null : null)); setMessage(aiCopy.roleSaved); }
        catch (failure) { setError(settingsError(failure)); } finally { setBusy(false); }
    }}><fieldset disabled={busy}><legend>{label}</legend><label htmlFor={`provider-${binding.role}`}>{label} provider</label><select id={`provider-${binding.role}`} value={selected} onChange={(e) => { setSelected(e.target.value); setModel(""); }}><option value="">Automatic</option>{providers.map((p) => <option key={p.provider} value={p.provider} disabled={!p.enabled || !p.has_credentials || !p.config.default_model}>{providerNames[p.provider]}</option>)}</select>
        <p className="muted">Selected: {binding.selected_provider && binding.available ? providerNames[binding.selected_provider] : "Unavailable"}{binding.selected_model ? ` · ${binding.selected_model}` : ""}</p>
        {!binding.available && <p className="context-note">{aiCopy.unavailableRole}</p>}
        <details open={detail === "impossible" || undefined}><summary>Task model preference</summary><label>{label} model override<input maxLength={160} value={model} disabled={!selected} placeholder="Blank uses this provider's default model" onChange={(e) => setModel(e.target.value)} /></label><p className="muted">Changing provider clears the draft model override. Automatic uses each selected provider's default model.</p></details>
        <button type="submit" className="secondary-button">{busy ? "Saving…" : `Save ${label.toLowerCase()} preference`}</button></fieldset>
        {message && <p role="status">{message}</p>}{error && <p className="error" role="alert">{error}</p>}
    </form>;
}

export function AIProviderSettings({ detail }: { detail: SettingsDetail }) {
    const [page, setPage] = useState("mode");
    const [providers, setProviders] = useState<LLMProviderConfig[]>([]);
    const [roles, setRoles] = useState<LLMRoleBinding[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [retry, setRetry] = useState(0);
    useEffect(() => {
        let active = true;
        Promise.allSettled([listLLMProviders(), listLLMRoles()]).then(([p, r]) => {
            if (!active) return;
            if (p.status === "fulfilled") setProviders(p.value);
            if (r.status === "fulfilled") setRoles(r.value);
            setError(p.status === "rejected" || r.status === "rejected"); setLoading(false);
        });
        return () => { active = false; };
    }, [retry]);
    async function saved(value: LLMProviderConfig) {
        setProviders((current) => current.map((p) => p.provider === value.provider ? value : p));
        setRoles([]);
        try { setRoles(await listLLMRoles()); } catch { setError(true); }
    }
    const activePage = page === "routing" && !canRoute(detail) ? "mode" : page;
    return <section className="ai-settings"><h2>{aiCopy.title}</h2><nav className="settings-subnav" aria-label="AI settings"><button type="button" aria-current={activePage === "mode" ? "page" : undefined} onClick={() => setPage("mode")}>{aiCopy.modeTitle}</button><button type="button" aria-current={activePage === "providers" ? "page" : undefined} onClick={() => setPage("providers")}>{aiCopy.personalTitle}</button>{canRoute(detail) && <button type="button" aria-current={activePage === "routing" ? "page" : undefined} onClick={() => setPage("routing")}>{aiCopy.routingTitle}</button>}</nav>
        {loading && <p role="status">Loading personal AI settings…</p>}{error && <p role="alert" className="error">{aiCopy.loadError}<button type="button" className="secondary-button" onClick={() => setRetry((v) => v + 1)}>Retry settings</button></p>}
        {activePage === "mode" && <><fieldset className="panel ai-mode"><legend>AI provider</legend><label><input type="radio" name="ai-mode" disabled value="workspace" />{aiCopy.defaultTitle} <span className="status-badge">Unavailable</span></label><p className="muted">{aiCopy.defaultUnavailable}</p><label><input type="radio" name="ai-mode" value="personal" checked readOnly />{aiCopy.personalMode}</label><p>{aiCopy.personalHelp}</p><button type="button" className="primary-button" onClick={() => setPage("providers")}>Manage my providers</button></fieldset>
            <section className="panel"><h3>Personal AI status</h3><p>{providers.filter((p) => p.has_credentials).length} connected · {providers.filter((p) => p.enabled).length} enabled</p><p className="muted">{aiCopy.unverified}</p>{detail !== "easy" && <><h4>Current task selection</h4><ul>{roles.map((r) => <li key={r.role}>{roleNames[r.role]}: {r.available && r.selected_provider ? providerNames[r.selected_provider] : "Unavailable"}</li>)}</ul><p>{aiCopy.automatic}</p></>}</section>
            <details className="panel"><summary>Future Workspace AI</summary><p>{aiCopy.workspaceFuture}</p></details></>}
        {activePage === "providers" && <><h3>{aiCopy.personalTitle}</h3><p>Your keys are personal, apply across series, and remain a permanent option alongside future workspace AI.</p><details><summary>What do provider statuses mean?</summary><p>{aiCopy.statuses}</p><p>{aiCopy.unverified}</p></details><div className="provider-grid">{providers.map((p) => <ProviderCard key={p.provider} provider={p} roles={roles} detail={detail} onSaved={saved} />)}</div></>}
        {activePage === "routing" && <section className="panel"><h3>{aiCopy.routingTitle}</h3><p>{aiCopy.automatic}</p>{roles.map((r) => <RolePreference key={r.role} binding={r} providers={providers} detail={detail} onSaved={setRoles} />)}</section>}
        <details className="panel"><summary>Understanding AI availability and errors</summary><ul><li>Provider not configured: connect a personal provider and set its model.</li><li>Invalid configuration: review model IDs and routing choices.</li><li>Provider unavailable: retry later or check backend setup.</li><li>Credential rejected: if a later provider call rejects your key, rotate it in Configure.</li><li>Model unavailable: check that your provider account can use the configured model.</li></ul><p>No billable request is used to validate a saved key.</p></details>
    </section>;
}
