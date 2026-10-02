import { useEffect, useRef, useState } from "react";

type CursorMode = "default" | "interactive" | "text";

function isTextTarget(el: Element | null): boolean {
  if (!el) return false;
  const node = el as HTMLElement;
  const tag = node.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (node.isContentEditable) return true;
  if (node.closest("input, textarea, select, [contenteditable='true']")) return true;
  return false;
}

function isInteractiveTarget(el: Element | null): boolean {
  if (!el) return false;
  const hit = (el as HTMLElement).closest(
    "a, button, [role='button'], label[for], summary, [data-cursor='interactive']",
  );
  return Boolean(hit);
}

/**
 * Desktop-only square target reticle. Hidden on touch and over form/text fields.
 * Uses rAF + direct DOM transforms — no React state on mousemove.
 */
export function TargetCursor() {
  const rootRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);
  const targetRef = useRef({ x: -100, y: -100 });
  const currentRef = useRef({ x: -100, y: -100 });
  const modeRef = useRef<CursorMode>("default");
  const reduceMotionRef = useRef(false);
  const [active, setActive] = useState(false);

  useEffect(() => {
    const finePointer = window.matchMedia("(pointer: fine) and (hover: hover)");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    const syncCapability = () => {
      const ok = finePointer.matches;
      setActive(ok);
      document.documentElement.classList.toggle("has-target-cursor", ok);
      reduceMotionRef.current = reduceMotion.matches;
      if (!ok && rootRef.current) {
        rootRef.current.style.opacity = "0";
      }
    };

    syncCapability();
    finePointer.addEventListener("change", syncCapability);
    reduceMotion.addEventListener("change", syncCapability);

    return () => {
      finePointer.removeEventListener("change", syncCapability);
      reduceMotion.removeEventListener("change", syncCapability);
      document.documentElement.classList.remove("has-target-cursor");
    };
  }, []);

  useEffect(() => {
    if (!active) return;
    const el = rootRef.current;
    if (!el) return;

    const setMode = (mode: CursorMode) => {
      if (modeRef.current === mode) return;
      modeRef.current = mode;
      el.dataset.mode = mode;
      el.style.opacity = mode === "text" ? "0" : "1";
    };

    const onMove = (e: MouseEvent) => {
      targetRef.current.x = e.clientX;
      targetRef.current.y = e.clientY;
      const under = document.elementFromPoint(e.clientX, e.clientY);
      if (isTextTarget(under)) setMode("text");
      else if (isInteractiveTarget(under)) setMode("interactive");
      else setMode("default");
    };

    const onLeave = () => {
      el.style.opacity = "0";
    };

    const onEnter = () => {
      if (modeRef.current !== "text") el.style.opacity = "1";
    };

    const tick = () => {
      const t = targetRef.current;
      const c = currentRef.current;
      if (reduceMotionRef.current) {
        c.x = t.x;
        c.y = t.y;
      } else {
        c.x += (t.x - c.x) * 0.28;
        c.y += (t.y - c.y) * 0.28;
      }
      el.style.transform = `translate3d(${c.x}px, ${c.y}px, 0) translate(-50%, -50%)`;
      rafRef.current = requestAnimationFrame(tick);
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    document.documentElement.addEventListener("mouseleave", onLeave);
    document.documentElement.addEventListener("mouseenter", onEnter);
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("mousemove", onMove);
      document.documentElement.removeEventListener("mouseleave", onLeave);
      document.documentElement.removeEventListener("mouseenter", onEnter);
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, [active]);

  if (!active) return null;

  return (
    <div ref={rootRef} className="target-cursor" data-mode="default" aria-hidden="true">
      <span className="target-cursor__frame" />
    </div>
  );
}
