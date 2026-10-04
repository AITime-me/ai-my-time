import { useEffect } from "react";
import { COOKIE_CONSENT_EVENT, hasAnalyticsConsent } from "@/lib/consent";

function readEnv(name: string): string {
  try {
    const viteVal = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env?.[
      name
    ];
    if (typeof viteVal === "string" && viteVal.trim() !== "") return viteVal.trim();
  } catch {
    // ignore
  }
  try {
    const procVal = typeof process !== "undefined" ? process.env?.[name] : undefined;
    if (typeof procVal === "string" && procVal.trim() !== "") return procVal.trim();
  } catch {
    // ignore
  }
  return "";
}

function loadYandex(yandexId: string): void {
  (window as unknown as { __YM_ID__: string }).__YM_ID__ = yandexId;
  if (document.getElementById("ym-script")) return;
  const script = document.createElement("script");
  script.id = "ym-script";
  script.innerHTML = `
    (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
    m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
    (window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");
    ym(${JSON.stringify(yandexId)}, "init", { clickmap:true, trackLinks:true, accurateTrackBounce:true, webvisor:true });
  `;
  document.head.appendChild(script);
}

function loadGoogle(gaId: string): void {
  if (document.getElementById("ga-script")) return;
  const s1 = document.createElement("script");
  s1.id = "ga-script";
  s1.async = true;
  s1.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(gaId)}`;
  document.head.appendChild(s1);
  const s2 = document.createElement("script");
  s2.innerHTML = `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config',${JSON.stringify(gaId)});`;
  document.head.appendChild(s2);
}

export function Analytics() {
  const yandexId = readEnv("VITE_YANDEX_METRIKA_ID");
  const gaId = readEnv("VITE_GA_ID");

  useEffect(() => {
    const activate = () => {
      if (!hasAnalyticsConsent()) return;
      if (yandexId) loadYandex(yandexId);
      if (gaId) loadGoogle(gaId);
    };

    activate();
    window.addEventListener(COOKIE_CONSENT_EVENT, activate);
    return () => window.removeEventListener(COOKIE_CONSENT_EVENT, activate);
  }, [yandexId, gaId]);

  return null;
}
