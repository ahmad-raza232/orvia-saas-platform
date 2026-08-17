const Input = ({
  label,
  error,
  hint,
  className = '',
  id,
  required,
  ...props
}) => {
  const inputId = id || props.name;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-semibold text-ink">
          {label}
          {required && <span className="text-danger"> *</span>}
        </label>
      )}
      <input
        id={inputId}
        required={required}
        className={`w-full rounded-md border bg-surface px-4 py-3 text-ink placeholder:text-ink-muted transition-colors duration-200 focus:outline-none focus:ring-4 focus:ring-olive/15 disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-70 ${
          error ? 'border-danger' : 'border-line focus:border-olive'
        } ${className}`}
        {...props}
      />
      {error && <p className="mt-1.5 text-sm text-danger">{error}</p>}
      {hint && !error && <p className="mt-1.5 text-xs text-ink-muted">{hint}</p>}
    </div>
  );
};

export default Input;
