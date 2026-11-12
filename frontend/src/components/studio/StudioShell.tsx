import { useEffect, useRef, useState, type ReactNode, type KeyboardEvent } from "react";
import type { AuthUser } from "../../api/sandcastle";
import { useI18n } from "../../i18n/context";
import type { LocalePreference } from "../../i18n/core";
import { studioNavigation, type StudioDestination } from "./navigation";
import { StudioIcon } from "./StudioIcon";
import "../../styles/studio-shell.css";

interface NavigationProps {
    active: StudioDestination;
    hasStory: boolean;
    onNavigate: (destination: StudioDestination) => void;
}

function StudioNavigation({ active, hasStory, onNavigate }: NavigationProps) {
    const { t } = useI18n();
    return <>
        <button type="button" className="studio-create" onClick={() => onNavigate("home")}><StudioIcon name="plus" size={16} />{t("studio.createSeries")}</button>
        <nav className="studio-navigation" aria-label={t("studio.navigation")}>
            {studioNavigation.map((item) => {
                const disabled = !item.destination || (!!item.needsStory && !hasStory);
                return <div key={item.id} className={item.divider ? "studio-nav-divider" : undefined}>
                    <button type="button" className="studio-nav-item" data-destination={item.id}
                        aria-current={active === item.destination ? "page" : undefined} disabled={disabled}
                        onClick={() => { if (item.destination) onNavigate(item.destination); }}>
                        <StudioIcon name={item.icon} /><span>{t(item.label)}{disabled && <small>{t(item.destination ? "studio.selectSeries" : "studio.unavailable")}</small>}</span>
                    </button>
                </div>;
            })}
        </nav>
        <div className="studio-sidebar-footer"><p>{t("studio.footer")}</p><StudioIcon name="layers" size={40} /></div>
    </>;
}

export function StudioShell({ user, active, hasStory, onNavigate, onLogout, children }: NavigationProps & {
    user: AuthUser; onLogout: () => void; children: ReactNode;
}) {
    const { t, locale, preference, setPreference } = useI18n();
    const [mobileOpen, setMobileOpen] = useState(false);
    const dialog = useRef<HTMLDialogElement>(null);
    const menuButton = useRef<HTMLButtonElement>(null);
    const account = useRef<HTMLDetailsElement>(null);

    useEffect(() => {
        if (mobileOpen) dialog.current?.showModal();
        else dialog.current?.close();
        if (!mobileOpen) return;
        const previous = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        return () => { document.body.style.overflow = previous; };
    }, [mobileOpen]);

    useEffect(() => {
        const desktop = window.matchMedia("(min-width: 951px)");
        const close = () => { if (desktop.matches) setMobileOpen(false); };
        desktop.addEventListener("change", close);
        return () => desktop.removeEventListener("change", close);
    }, []);

    function keepNavigationFocus(event: KeyboardEvent<HTMLDialogElement>) {
        if (event.key !== "Tab") return;
        const buttons = [...event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not(:disabled)")];
        const first = buttons[0], last = buttons.at(-1);
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }

    function navigate(destination: StudioDestination) {
        setMobileOpen(false);
        if (account.current) account.current.open = false;
        onNavigate(destination);
    }

    return <div className="studio-shell">
        <a className="studio-skip-link" href="#studio-content">{t("studio.skipContent")}</a>
        <header className="studio-header">
            <button ref={menuButton} type="button" className="studio-menu-button" aria-label={t("studio.openNavigation")}
                aria-expanded={mobileOpen} aria-controls="studio-mobile-navigation" onClick={() => setMobileOpen(true)}><StudioIcon name="menu" /></button>
            <button type="button" className="studio-brand" aria-label={t("studio.brandHome")} onClick={() => navigate("home")}>
                <span className="studio-brand-mark"><StudioIcon name="layers" size={25} /></span><strong>Sandcastle</strong><span className="studio-brand-tag">Studio</span>
            </button>
            <span className="studio-tagline">{t("studio.tagline")} <span aria-hidden="true">✦</span></span>
            <div className="studio-header-actions">
                <span className="studio-plan-note"><StudioIcon name="layers" size={14} />{t("studio.plansUnavailable")}</span>
                <label className="studio-language"><StudioIcon name="globe" size={15} /><span className="studio-sr-only">{t("settings.language")}</span>
                    <select aria-label={t("settings.language")} value={preference} onChange={(event) => setPreference(event.target.value as LocalePreference)}>
                        <option value="en">EN</option><option value="id">ID</option><option value="auto">{t("studio.autoLanguage", { language: locale.toUpperCase() })}</option>
                    </select>
                </label>
                <details ref={account} className="studio-account" onKeyDown={(event) => { if (event.key === "Escape") { event.currentTarget.open = false; event.currentTarget.querySelector("summary")?.focus(); } }}>
                    <summary aria-label={t("studio.accountMenu")}><span aria-hidden="true">{(user.name?.trim() || user.email).slice(0, 1).toUpperCase()}</span></summary>
                    <div className="studio-account-popover"><strong>{user.name || user.email}</strong><span>{user.email}</span>
                        <button type="button" onClick={() => navigate("settings")}>{t("nav.settings")}</button>
                        <button type="button" onClick={() => { if (account.current) account.current.open = false; onLogout(); }}>{t("nav.signOut")}</button>
                    </div>
                </details>
            </div>
        </header>
        <div className="studio-layout">
            <aside className="studio-sidebar"><StudioNavigation active={active} hasStory={hasStory} onNavigate={navigate} /></aside>
            <div className="studio-content" id="studio-content" tabIndex={-1}>{children}</div>
        </div>
        <dialog ref={dialog} id="studio-mobile-navigation" className="studio-mobile-navigation" aria-labelledby="studio-navigation-title" aria-modal="true" onKeyDown={keepNavigationFocus}
            onCancel={() => setMobileOpen(false)} onClose={() => { setMobileOpen(false); if (menuButton.current?.getClientRects().length) menuButton.current.focus(); }}
            onClick={(event) => { const bounds = event.currentTarget.getBoundingClientRect(); if (event.target === event.currentTarget && (event.clientX > bounds.right || event.clientX < bounds.left || event.clientY < bounds.top || event.clientY > bounds.bottom)) setMobileOpen(false); }}>
            <div className="studio-mobile-navigation-heading"><strong id="studio-navigation-title">{t("studio.navigation")}</strong><button type="button" aria-label={t("studio.closeNavigation")} onClick={() => setMobileOpen(false)}><StudioIcon name="close" /></button></div>
            <StudioNavigation active={active} hasStory={hasStory} onNavigate={navigate} />
        </dialog>
    </div>;
}
