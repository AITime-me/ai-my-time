import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAnalyticsConfig } from "@/lib/site.functions";

export function Analytics() {
  const { data } = useQuery({
    queryKey: ["analytics_config"],
    queryFn: () => getAnalyticsConfig(),
    staleTime: 5 * 60_000,
  });
  const s = data ?? { analytics_enabled: false, yandex_metrika_id: "", google_analytics_id: "" };
  useEffect(() => {
    if (!s.analytics_enabled) return;
    if (s.yandex_metrika_id) {
      const id = s.yandex_metrika_id;
      (window as unknown as { __YM_ID__: string }).__YM_ID__ = id;
      if (!document.getElementById("ym-script")) {
        const script = document.createElement("script");
        script.id = "ym-script";
        script.innerHTML = `
          (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
          m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
          (window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");
          ym(${id}, "init", { clickmap:true, trackLinks:true, accurateTrackBounce:true, webvisor:true });
        `;
        document.head.appendChild(script);
      }
    }
    if (s.google_analytics_id) {
      const id = s.google_analytics_id;
      if (!document.getElementById("ga-script")) {
        const s1 = document.createElement("script");
        s1.id = "ga-script";
        s1.async = true;
        s1.src = `https://www.googletagmanager.com/gtag/js?id=${id}`;
        document.head.appendChild(s1);
        const s2 = document.createElement("script");
        s2.innerHTML = `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','${id}');`;
        document.head.appendChild(s2);
      }
    }
  }, [s.analytics_enabled, s.yandex_metrika_id, s.google_analytics_id]);
  return null;
}