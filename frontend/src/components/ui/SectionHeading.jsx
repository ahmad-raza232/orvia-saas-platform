const SectionHeading = ({
  eyebrow,
  title,
  description,
  align = 'left',
  action = null,
  className = '',
}) => (
  <div
    className={`mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between ${
      align === 'center' ? 'mx-auto max-w-2xl text-center sm:flex-col sm:items-center' : ''
    } ${className}`}
  >
    <div className={align === 'center' ? 'max-w-2xl' : 'max-w-2xl'}>
      {eyebrow && (
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-olive">
          {eyebrow}
        </p>
      )}
      <h1 className="font-display text-h2 text-ink">{title}</h1>
      {description && (
        <p className="mt-2 text-base leading-relaxed text-ink-secondary">{description}</p>
      )}
    </div>
    {action && <div className="shrink-0">{action}</div>}
  </div>
);

export default SectionHeading;
