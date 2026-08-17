import { Link } from 'react-router-dom';

const Mark = ({ className = 'h-9 w-9', inverted = false }) => (
  <svg
    viewBox="0 0 40 40"
    className={className}
    aria-hidden="true"
    focusable="false"
  >
    <rect width="40" height="40" rx="10" fill={inverted ? '#FFDAB9' : '#556B2F'} />
    <circle
      cx="20"
      cy="20"
      r="9"
      fill="none"
      stroke={inverted ? '#556B2F' : '#FFDAB9'}
      strokeWidth="2.6"
    />
    <circle cx="27.2" cy="26.4" r="2.3" fill={inverted ? '#556B2F' : '#FFDAB9'} />
  </svg>
);

const Logo = ({
  to = '/',
  showWordmark = true,
  compact = false,
  inverted = false,
  className = '',
  onClick,
}) => {
  const content = (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <Mark className={compact ? 'h-8 w-8' : 'h-9 w-9'} inverted={inverted} />
      {showWordmark && (
        <span className="leading-none">
          <span
            className={`block font-display text-[1.35rem] font-semibold tracking-[0.08em] ${
              inverted ? 'text-peach' : 'text-ink'
            }`}
          >
            ORVIA
          </span>
          <span
            className={`mt-0.5 block text-[10px] font-semibold uppercase tracking-[0.18em] ${
              inverted ? 'text-peach/75' : 'text-ink-muted'
            }`}
          >
            by Softorica
          </span>
        </span>
      )}
    </span>
  );

  if (!to) {
    return content;
  }

  return (
    <Link
      to={to}
      onClick={onClick}
      className="inline-flex items-center rounded-md focus-visible:outline-none"
      aria-label="ORVIA home"
    >
      {content}
    </Link>
  );
};

export default Logo;
export { Mark };
