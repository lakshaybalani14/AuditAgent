import { useEffect, useRef, useState } from "react";

export default function AnimatedNumber({ value, digits = 0 }) {
  const valid = typeof value === "number" && Number.isFinite(value);
  const [display, setDisplay] = useState(valid ? 0 : null);
  const current = useRef(0);
  useEffect(() => {
    if (!valid || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      current.current = valid ? value : 0;
      setDisplay(valid ? value : null);
      return;
    }
    let frame;
    let started;
    const from = current.current;
    const animate = (time) => {
      if (started === undefined) started = time;
      const progress = Math.min(1, (time - started) / 550);
      current.current = progress === 1 ? value : from + (value - from) * (1 - (1 - progress) ** 3);
      setDisplay(current.current);
      if (progress < 1) frame = window.requestAnimationFrame(animate);
    };
    frame = window.requestAnimationFrame(animate);
    return () => window.cancelAnimationFrame(frame);
  }, [value, valid]);
  return <span className="animated-number"><span aria-hidden="true">{valid && display !== null ? display.toFixed(digits) : "—"}</span><span className="health-sr-only">{valid ? value.toFixed(digits) : "Unavailable"}</span></span>;
}
