import { Link } from 'react-router-dom';

const variants = {
  primary:
    'bg-olive text-peach hover:bg-olive-hover shadow-xs hover:shadow-sm',
  secondary:
    'bg-peach text-olive-dark hover:bg-peach-deep',
  outline:
    'border border-line bg-surface text-ink hover:border-olive/40 hover:bg-peach-soft',
  ghost:
    'text-ink-secondary hover:bg-muted hover:text-ink',
  destructive:
    'bg-danger text-white hover:bg-[#9b1c14]',
};

const sizes = {
  sm: 'h-9 px-3.5 text-sm',
  md: 'h-11 px-5 text-sm',
  lg: 'h-12 px-6 text-base',
};

const Button = ({
  to,
  href,
  variant = 'primary',
  size = 'md',
  className = '',
  disabled = false,
  children,
  type = 'button',
  onClick,
  ...props
}) => {
  const classes = `inline-flex items-center justify-center gap-2 rounded-md font-semibold tracking-tight transition-all duration-200 ${variants[variant] || variants.primary} ${sizes[size] || sizes.md} ${
    disabled ? 'pointer-events-none cursor-not-allowed opacity-50' : 'cursor-pointer'
  } ${className}`;

  if (to) {
    return (
      <Link
        to={to}
        className={classes}
        aria-disabled={disabled || undefined}
        onClick={onClick}
        {...props}
      >
        {children}
      </Link>
    );
  }

  if (href) {
    return (
      <a href={href} className={classes} onClick={onClick} {...props}>
        {children}
      </a>
    );
  }

  return (
    <button
      type={type}
      disabled={disabled}
      className={classes}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;
