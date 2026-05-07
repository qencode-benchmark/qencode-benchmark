"use client";

import { useEffect } from "react";

function emitTrack(eventName, payload) {
  if (typeof window === "undefined") return;

  try {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event: eventName, ...payload });
  } catch {}

  try {
    if (typeof window.gtag === "function") {
      window.gtag("event", eventName, payload || {});
    }
  } catch {}
}

export default function AnalyticsClickTracker() {
  useEffect(() => {
    function onClick(e) {
      const target = e.target instanceof Element ? e.target : null;
      if (!target) return;
      const el = target.closest("[data-track]");
      if (!el) return;

      const name = el.getAttribute("data-track");
      if (!name) return;

      const href = el.getAttribute("href") || "";
      const label = (el.textContent || "").trim().slice(0, 120);
      emitTrack("cta_click", {
        track_name: name,
        href,
        label
      });
    }

    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  return null;
}

