const Card = ({ className = '', hover = false, children, ...props }) => (
  <div
    className={`rounded-lg border border-line bg-surface shadow-xs ${
      hover ? 'transition-all duration-200 hover:-translate-y-0.5 hover:shadow-sm' : ''
    } ${className}`}
    {...props}
  >
    {children}
  </div>
);

export default Card;
