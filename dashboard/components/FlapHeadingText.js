import SplitFlapText from "./SplitFlapText";

export default function FlapHeadingText({ children, accentLastWord = false }) {
  const text = String(children);
  const words = text.split(/\s+/);
  return <span className="flap-heading-text">
    <span className="split-flap-sr-only">{text}</span>
    {words.map((word, index) => <span key={`${index}-${word}`} className={accentLastWord && index === words.length - 1 ? "flap-heading-word flap-heading-accent" : "flap-heading-word"} aria-hidden="true">
      <SplitFlapText words={[word.toUpperCase()]} flipDuration={.12} stagger={.035} flipsPerChar={5} charset="alphanumeric" order="left" fontSize="1em" tileColor="var(--surface2)" textColor="currentColor" tileRadius={5} gap=".045em" depth={.5} glare={0} intro />
    </span>)}
  </span>;
}
