import { useEffect, useRef, useState } from "react";

const CHARSETS = { numeric: "0123456789", alphabetic: " ABCDEFGHIJKLMNOPQRSTUVWXYZ", alphanumeric: " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" };

function FlapTile({ character, delay, flipDuration, flipsPerChar, charset, intro }) {
  const initial = character;
  const [frame, setFrame] = useState({ previous: initial, current: initial, sequence: 0, moving: false });
  const current = useRef(initial);
  const introduced = useRef(false);
  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const timers = new Set();
    const settle = () => {
      timers.forEach(window.clearTimeout);
      timers.clear();
      current.current = character;
      setFrame((previous) => ({ previous: character, current: character, sequence: previous.sequence, moving: false }));
    };
    const introduce = intro && !introduced.current;
    if (reducedMotion.matches || !charset.includes(character) || (!introduce && current.current === character)) { settle(); return; }
    let step = 0;
    const steps = Math.max(1, Math.floor(flipsPerChar));
    const startIndex = Math.max(0, charset.indexOf(current.current));
    const schedule = (callback, milliseconds) => {
      const timer = window.setTimeout(() => { timers.delete(timer); callback(); }, milliseconds);
      timers.add(timer);
    };
    const flip = () => {
      introduced.current = true;
      step += 1;
      const next = step === steps ? character : charset[(startIndex + step) % charset.length];
      const previous = current.current;
      current.current = next;
      setFrame((old) => ({ previous, current: next, sequence: old.sequence + 1, moving: true }));
      schedule(step < steps ? flip : settle, flipDuration * 1000);
    };
    schedule(flip, delay * 1000);
    const onPreferenceChange = (event) => { if (event.matches) settle(); };
    reducedMotion.addEventListener("change", onPreferenceChange);
    return () => { timers.forEach(window.clearTimeout); reducedMotion.removeEventListener("change", onPreferenceChange); };
  }, [character, delay, flipDuration, flipsPerChar, charset, intro]);

  if (character !== " " && !charset.includes(character)) return <span className="split-flap-punctuation">{character}</span>;
  return <span className="split-flap-tile">
    <span className="split-flap-half split-flap-top"><span>{frame.current}</span></span>
    <span className="split-flap-half split-flap-bottom"><span>{frame.moving ? frame.previous : frame.current}</span></span>
    {frame.moving && <span key={frame.sequence} className="split-flap-moving">
      <span className="split-flap-half split-flap-top split-flap-leaf-top"><span>{frame.previous}</span></span>
      <span className="split-flap-half split-flap-bottom split-flap-leaf-bottom"><span>{frame.current}</span></span>
    </span>}
    <span className="split-flap-seam" />
  </span>;
}

export default function SplitFlapText({ words = [], flipDuration = .12, stagger = .06, cycleDelay = 2400, charset = "alphanumeric", flipsPerChar = 8, order = "left", align = "left", tileStyle = "board", tileColor = "#111827", textColor = "#f8fafc", glare = 0, depth = .5, tileRadius = 8, gap = 6, fontSize = 52, loop = false, padTo = 0, intro = true, className = "" }) {
  const [wordIndex, setWordIndex] = useState(0);
  const elementRef = useRef(null);
  const [introVisible, setIntroVisible] = useState(false);
  const wordsKey = JSON.stringify(words);
  const duration = Math.max(.04, flipDuration);
  const target = String(words[wordIndex % Math.max(1, words.length)] ?? "");
  const characters = Array.from(target.padEnd(Math.max(target.length, padTo), " "));
  useEffect(() => {
    if (!intro || !elementRef.current) return;
    if (typeof IntersectionObserver === "undefined") { setIntroVisible(true); return; }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) { setIntroVisible(true); observer.disconnect(); }
    }, { threshold: .15 });
    observer.observe(elementRef.current);
    return () => observer.disconnect();
  }, [intro]);
  useEffect(() => {
    if (!loop || words.length < 2) return;
    const interval = window.setInterval(() => setWordIndex((index) => index + 1), Math.max(0, cycleDelay) + duration * Math.max(1, flipsPerChar) * 1000 + Math.max(0, stagger) * characters.length * 1000);
    return () => window.clearInterval(interval);
  }, [wordsKey, loop, cycleDelay, duration, flipsPerChar, stagger, characters.length, words.length]);
  return <span ref={elementRef} className={`split-flap-text ${className}`} style={{ "--flap-color": tileColor, "--flap-text": textColor, "--flap-font": typeof fontSize === "number" ? `${fontSize}px` : fontSize, "--flap-radius": `${tileRadius}px`, "--flap-gap": typeof gap === "number" ? `${gap}px` : gap, "--flap-duration": `${duration}s`, "--flap-depth": Math.max(0, depth), "--flap-glare": Math.min(1, Math.max(0, glare)), justifyContent: align === "right" ? "flex-end" : align === "center" ? "center" : "flex-start" }}>
    <span className={`split-flap-board split-flap-style-${tileStyle}`} aria-hidden="true">{characters.map((character, index) => <FlapTile key={index} character={character} delay={(introVisible ? .3 : 0) + Math.max(0, stagger) * (order === "right" ? characters.length - index - 1 : order === "center" ? Math.abs(index - (characters.length - 1) / 2) : index)} flipDuration={duration} flipsPerChar={flipsPerChar} charset={CHARSETS[charset] || charset} intro={intro && introVisible} />)}</span>
    <span className="split-flap-sr-only">{target}</span>
  </span>;
}
