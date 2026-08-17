import { useState, useEffect } from 'react';
import { useLocation, useNavigate, NavLink } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Logo from './ui/Logo';
import Button from './ui/Button';

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  const scrollToSection = (id) => {
    const section = document.getElementById(id);
    if (section) {
      section.scrollIntoView({ behavior: 'smooth' });
      setIsOpen(false);
    }
  };

  const handleMenuNavigation = (id) => {
    if (location.pathname !== '/') {
      navigate('/', { state: { scrollTo: id } });
      setIsOpen(false);
    } else {
      scrollToSection(id);
    }
  };

  const navButtonClass =
    'text-sm font-medium text-ink-secondary transition-colors duration-200 hover:text-olive';

  return (
    <header className="sticky top-0 z-50 border-b border-line/80 bg-canvas/90 backdrop-blur-md">
      <div className="mx-auto flex h-[4.25rem] max-w-container items-center justify-between px-4 sm:px-6 lg:px-8">
        <Logo onClick={() => setIsOpen(false)} />

        <nav className="hidden items-center gap-7 lg:flex" aria-label="Primary">
          <button type="button" onClick={() => handleMenuNavigation('services')} className={navButtonClass}>
            Services
          </button>
          <button type="button" onClick={() => handleMenuNavigation('pricing')} className={navButtonClass}>
            Pricing
          </button>
          <button type="button" onClick={() => handleMenuNavigation('tracking')} className={navButtonClass}>
            Tracking
          </button>
          <button type="button" onClick={() => handleMenuNavigation('faq')} className={navButtonClass}>
            FAQ
          </button>
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          {!user ? (
            <>
              <Button variant="ghost" size="sm" onClick={() => navigate('/login')}>
                Login
              </Button>
              <Button size="sm" onClick={() => handleMenuNavigation('contact')}>
                Book pickup
              </Button>
            </>
          ) : (
            <>
              <NavLink
                to="/app"
                className="text-sm font-medium text-ink-secondary hover:text-olive"
              >
                Workspace
              </NavLink>
              <Button variant="ghost" size="sm" onClick={() => { logout(); navigate('/'); }}>
                Sign out
              </Button>
              <Button size="sm" onClick={() => navigate('/app/shipments/new')}>
                New shipment
              </Button>
            </>
          )}
        </div>

        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md text-ink lg:hidden"
          onClick={() => setIsOpen((open) => !open)}
          aria-expanded={isOpen}
          aria-label={isOpen ? 'Close menu' : 'Open menu'}
        >
          {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {isOpen && (
        <nav className="space-y-1 border-t border-line bg-canvas px-4 py-4 animate-fade-up lg:hidden">
          {['services', 'pricing', 'tracking', 'faq'].map((id) => (
            <button
              key={id}
              type="button"
              onClick={() => handleMenuNavigation(id)}
              className="block w-full rounded-md px-3 py-2.5 text-left text-sm font-medium capitalize text-ink hover:bg-muted"
            >
              {id}
            </button>
          ))}
          <div className="flex flex-col gap-2 pt-3">
            {!user ? (
              <>
                <Button variant="outline" onClick={() => { setIsOpen(false); navigate('/login'); }}>
                  Login
                </Button>
                <Button onClick={() => handleMenuNavigation('contact')}>Book pickup</Button>
              </>
            ) : (
              <>
                <Button variant="outline" onClick={() => { setIsOpen(false); navigate('/user/dashboard'); }}>
                  Dashboard
                </Button>
                <Button onClick={() => { setIsOpen(false); navigate('/book-parcel'); }}>
                  Book parcel
                </Button>
                <Button variant="ghost" onClick={() => { setIsOpen(false); logout(); navigate('/'); }}>
                  Logout
                </Button>
              </>
            )}
          </div>
        </nav>
      )}
    </header>
  );
};

export default Navbar;
