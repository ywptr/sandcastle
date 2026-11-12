import { useI18n } from "../../i18n/context";

import { homeCopy } from "./homeCopy";

export function HomeWelcome() {
    const {locale}=useI18n(); const copy=homeCopy[locale];
    return <><section className="home-hero"><span className="eyebrow">{copy.kicker}</span><h1>{copy.title}</h1><p>{copy.intro}</p><div className="home-hero-art" aria-hidden="true"><span>✦</span><i/><b/><em/></div></section><div className="home-welcome"><span aria-hidden="true">✦</span><div><strong>{copy.welcome}</strong><p>{copy.welcomeHelp}</p></div></div></>;
}
