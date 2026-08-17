import { statusTone } from '../../utils/format';

const tones = {
  success: 'bg-success-soft text-success',
  warning: 'bg-warning-soft text-warning',
  danger: 'bg-danger-soft text-danger',
  info: 'bg-info-soft text-info',
  olive: 'bg-olive-light text-olive-dark',
  peach: 'bg-peach-soft text-olive-dark',
  neutral: 'bg-muted text-ink-secondary',
};

const Badge = ({ children, tone = 'neutral', className = '' }) => (
  <span
    className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${tones[tone] || tones.neutral} ${className}`}
  >
    {children}
  </span>
);

export const StatusBadge = ({ status }) => (
  <Badge tone={statusTone(status)}>
    {status?.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())}
  </Badge>
);

export default Badge;
