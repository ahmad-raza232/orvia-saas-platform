import { createElement } from 'react';
import Button from './Button';

const EmptyState = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  to,
  className = '',
}) => (
  <div className={`px-6 py-14 text-center ${className}`}>
    {icon && (
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-lg bg-peach-soft text-olive">
        {createElement(icon, { className: 'h-6 w-6', 'aria-hidden': true })}
      </div>
    )}
    <h3 className="font-display text-xl text-ink">{title}</h3>
    {description && (
      <p className="mx-auto mt-2 max-w-md text-sm text-ink-secondary">{description}</p>
    )}
    {actionLabel && to && (
      <Button to={to} className="mt-6">
        {actionLabel}
      </Button>
    )}
    {actionLabel && onAction && !to && (
      <Button onClick={onAction} className="mt-6">
        {actionLabel}
      </Button>
    )}
  </div>
);

export default EmptyState;
