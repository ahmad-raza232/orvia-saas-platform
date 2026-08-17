import { useLocation, useNavigate } from 'react-router-dom';
import Logo from './ui/Logo';
import Container from './ui/Container';

const Footer = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const scrollToSection = (id) => {
    if (location.pathname !== '/') {
      navigate('/', { state: { scrollTo: id } });
      return;
    }
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <footer className="border-t border-line bg-olive text-peach">
      <Container className="grid gap-10 py-14 md:grid-cols-3">
        <div>
          <Logo to="/" inverted />
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-peach/80">
            ORVIA is a multi-tenant logistics SaaS for shipments, riders, customers, and proof of delivery. Built by Softorica.
          </p>
          <p className="mt-4 text-xs uppercase tracking-[0.18em] text-peach/70">
            Routes that arrive.
          </p>
        </div>

        <div>
          <h3 className="text-sm font-semibold uppercase tracking-[0.16em]">Explore</h3>
          <ul className="mt-4 space-y-2 text-sm text-peach/80">
            {['services', 'pricing', 'tracking', 'faq'].map((id) => (
              <li key={id}>
                <button
                  type="button"
                  onClick={() => scrollToSection(id)}
                  className="capitalize transition-colors hover:text-peach"
                >
                  {id}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-semibold uppercase tracking-[0.16em]">Contact</h3>
          <p className="mt-4 text-sm text-peach/80">Lahore, Pakistan</p>
          <a href="tel:+923263253256" className="mt-2 block text-sm hover:text-peach">
            +92 326 3253256
          </a>
          <p className="mt-2 text-sm text-peach/80">Mon – Sat: 9AM – 6PM</p>
        </div>
      </Container>

      <div className="border-t border-peach/15">
        <Container className="flex flex-col items-center justify-between gap-3 py-5 text-xs text-peach/70 sm:flex-row">
          <p>© {new Date().getFullYear()} Softorica. ORVIA is a Softorica product.</p>
          <p>Professional logistics operations software.</p>
        </Container>
      </div>
    </footer>
  );
};

export default Footer;
