const ErrorState = ({
  title = 'Something went wrong',
  description,
  onRetry,
  className = '',
}) => (
  <div
    className={`rounded-md border border-danger/20 bg-danger-soft px-4 py-3 text-sm text-danger ${className}`}
  >
    <p className="font-semibold">{title}</p>
    {description && <p className="mt-1 text-danger/80">{description}</p>}
    {onRetry && (
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 text-sm font-semibold underline underline-offset-2"
      >
        Try again
      </button>
    )}
  </div>
);

export default ErrorState;
