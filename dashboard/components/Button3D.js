export default function Button3D({ children, onClick, disabled = false, busy = false, className = "", title }) {
  return (
    <button
      type="button"
      className={`button-3d ${className}`}
      onClick={onClick}
      disabled={disabled}
      aria-busy={busy || undefined}
      title={title}
    >
      <span className="button-3d-content">
        {busy ? (
          <svg className="button-3d-spinner" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="2" opacity=".25" />
            <path d="M12 3a9 9 0 0 1 9 9" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
            <polygon points="6 3 20 12 6 21 6 3" />
          </svg>
        )}
        <span>{children}</span>
      </span>
    </button>
  );
}
