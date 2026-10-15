export default function PipelineIcon({ type, className = "", glyphOnly = false }) {
  const glyphs = {
    model: <><path d="M40 18 50 13 60 18 50 24 40 18Z" /><path d="M40 18v11l10 6V24M60 18v11l-10 6" /></>,
    run: <><circle cx="50" cy="22" r="8" /><path d="M50 17v10m-5-5h10" /></>,
    log: <><path d="M43 17h15M43 22h15M43 27h11" /><circle cx="39" cy="17" r="1" /><circle cx="39" cy="22" r="1" /><circle cx="39" cy="27" r="1" /></>,
    explain: <><path d="M50 14v4m-8 2 3 3m10-3-3 3m-7 4h10m-9 4h8" /><path d="M44 25a7 7 0 1 1 12 4l-1 1h-9l-1-1a7 7 0 0 1-1-4Z" /></>,
    evaluation: <><path d="M45 15h10m-7 0v7l-6 10h16l-6-10v-7" /><path d="M45 27h10" /></>,
  };
  return <svg className={`${glyphOnly ? "pipeline-symbol" : "pipeline-cube"} ${className}`} viewBox={glyphOnly ? "34 9 32 28" : "0 0 100 88"} aria-hidden="true" focusable="false">
    {!glyphOnly && <>
      <polygon className="cube-face cube-left" points="12,25 50,45 50,82 12,62" />
      <polygon className="cube-face cube-right" points="50,45 88,25 88,62 50,82" />
      <polygon className="cube-face cube-top" points="50,5 88,25 50,45 12,25" />
    </>}
    <g className={glyphOnly ? undefined : "cube-glyph"} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{glyphs[type] || glyphs.model}</g>
  </svg>;
}
