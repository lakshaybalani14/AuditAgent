import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import PipelineIcon from "./PipelineIcon";
import Button3D from "./Button3D";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: "run" },
  { href: "/decisions", label: "Decision log", icon: "log" },
  { href: "/evaluation", label: "Evaluation", icon: "evaluation" },
];

export default function DashboardNavbar({ pathname, darkMode, onToggleTheme, onRun, showRunControls, runStatus, runButtonLabel }) {
  const [condensed, setCondensed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [hoveredIndex, setHoveredIndex] = useState(null);
  const headerRef = useRef(null);
  const menuButtonRef = useRef(null);
  const menuId = useId();
  const activeIndex = Math.max(0, NAV_ITEMS.findIndex((item) => item.href === pathname));

  useEffect(() => {
    let frame = null;
    const onScroll = () => {
      if (frame !== null) return;
      frame = window.requestAnimationFrame(() => {
        setCondensed(window.scrollY > 64);
        frame = null;
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (frame !== null) window.cancelAnimationFrame(frame);
    };
  }, []);

  useEffect(() => {
    setMenuOpen(false);
    setHoveredIndex(null);
  }, [pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    const closeOutside = (event) => {
      if (!headerRef.current?.contains(event.target)) setMenuOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    window.addEventListener("pointerdown", closeOutside);
    return () => {
      window.removeEventListener("keydown", closeOnEscape);
      window.removeEventListener("pointerdown", closeOutside);
    };
  }, [menuOpen]);

  return <header ref={headerRef} className={`dashboard-navbar${condensed ? " is-condensed" : ""}${menuOpen ? " is-menu-open" : ""}`}>
    <div className="navbar-body">
      <Link href="/" className="navbar-brand" aria-label="AuditAgent overview" onClick={() => setMenuOpen(false)}>
        <div className="brand-mark"><span /></div>
        <h1>AuditAgent</h1>
      </Link>
      <nav id={menuId} className="navbar-links" aria-label="Dashboard pages" style={{ "--nav-index": hoveredIndex ?? activeIndex }} onPointerLeave={() => setHoveredIndex(null)} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setHoveredIndex(null); }}>
        <span className="navbar-nav-highlight" aria-hidden="true" />
        {NAV_ITEMS.map((item, index) => <Link key={item.href} href={item.href} className={`navbar-link${pathname === item.href ? " active" : ""}`} aria-label={item.label} aria-current={pathname === item.href ? "page" : undefined} onPointerEnter={() => setHoveredIndex(index)} onFocus={() => setHoveredIndex(index)} onClick={() => setMenuOpen(false)}>
          <PipelineIcon type={item.icon} className="navbar-symbol" glyphOnly />
          <span className="navbar-link-label" aria-hidden="true">{item.label}</span>
        </Link>)}
      </nav>
      <div className="navbar-actions">
        {showRunControls && <Button3D className="run-button navbar-run-button" onClick={() => { setMenuOpen(false); onRun(); }} busy={runStatus?.status === "running"} disabled={runStatus?.status === "running" || runStatus?.modelAvailable === false} title={runStatus?.modelAvailable === false ? "A trained model checkpoint is required" : undefined}>{runButtonLabel}</Button3D>}
        <button className="icon-button navbar-theme-button" onClick={onToggleTheme} aria-label="Toggle colour theme">{darkMode ? "☼" : "◐"}</button>
        <button ref={menuButtonRef} className="navbar-menu-toggle" onClick={() => setMenuOpen((value) => !value)} aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"} aria-expanded={menuOpen} aria-controls={menuId}>
          <span /><span /><span />
        </button>
      </div>
    </div>
  </header>;
}
