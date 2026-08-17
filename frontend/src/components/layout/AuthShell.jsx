import Logo from '../ui/Logo';
import Card from '../ui/Card';

/**
 * Softorica auth layout. Use `wide` for multi-section registration.
 */
const AuthShell = ({ title, subtitle, children, wide = false, footer }) => (
  <div className="relative flex min-h-[calc(100vh-4.25rem)] items-center justify-center overflow-hidden bg-[#1a2332] px-4 py-12 sm:py-16">
    <div
      className="pointer-events-none absolute inset-0 opacity-40"
      style={{
        background:
          'radial-gradient(ellipse at 20% 20%, rgba(85,107,47,0.45), transparent 50%), radial-gradient(ellipse at 80% 80%, rgba(255,218,185,0.12), transparent 45%)',
      }}
      aria-hidden
    />
    <Card
      className={`relative z-10 w-full border-line/40 bg-surface/95 p-6 shadow-md backdrop-blur sm:p-8 ${
        wide ? 'max-w-3xl' : 'max-w-md'
      }`}
    >
      <div className="mb-8 text-center">
        <div className="mb-5 flex justify-center">
          <Logo to="/" />
        </div>
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-olive">
          Softorica
        </p>
        <h1 className="font-display text-3xl text-ink sm:text-[2rem]">{title}</h1>
        {subtitle && <p className="mt-2 text-sm text-ink-secondary">{subtitle}</p>}
      </div>
      {children}
      {footer}
    </Card>
  </div>
);

export default AuthShell;
