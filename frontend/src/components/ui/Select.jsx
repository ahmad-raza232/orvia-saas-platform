const Select = ({
  label,
  error,
  className = '',
  id,
  required,
  children,
  ...props
}) => {
  const selectId = id || props.name;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={selectId} className="mb-1.5 block text-sm font-semibold text-ink">
          {label}
          {required && <span className="text-danger"> *</span>}
        </label>
      )}
      <select
        id={selectId}
        required={required}
        className={`w-full rounded-md border bg-surface px-4 py-3 text-ink transition-colors duration-200 focus:outline-none focus:ring-4 focus:ring-olive/15 disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-70 ${
          error ? 'border-danger' : 'border-line focus:border-olive'
        } ${className}`}
        {...props}
      >
        {children}
      </select>
      {error && <p className="mt-1.5 text-sm text-danger">{error}</p>}
    </div>
  );
};

export default Select;
