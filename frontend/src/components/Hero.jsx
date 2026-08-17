import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Clock, ShieldCheck, Search } from 'lucide-react';
import heroImg from '../assets/hero.jpg';
import Button from './ui/Button';
import Container from './ui/Container';

const Hero = () => {
  const [trackingId, setTrackingId] = useState('');
  const navigate = useNavigate();

  const scrollToBooking = () => {
    document.getElementById('contact')?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleTrack = (event) => {
    event.preventDefault();
    if (trackingId.trim()) {
      navigate(`/track?tracking_id=${trackingId.trim().toUpperCase()}`);
    }
  };

  return (
    <section className="relative overflow-hidden bg-canvas pt-6 pb-16 lg:pt-10 lg:pb-24">
      <Container className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="animate-fade-up">
          <p className="mb-4 text-xs font-semibold uppercase tracking-[0.22em] text-olive">
            Softorica logistics
          </p>
          <h1 className="font-display text-display text-ink">
            Move what matters.
            <span className="block text-olive">We’ll get it there.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-secondary">
            Reliable parcel delivery and logistics for individuals and businesses
            across Pakistan — same-day, nationwide, and COD, handled with care.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button size="lg" onClick={scrollToBooking}>
              Book a pickup
              <ArrowRight className="h-4 w-4" />
            </Button>
            <Button href="tel:+923263253256" variant="outline" size="lg">
              Call us
            </Button>
          </div>

          <form
            onSubmit={handleTrack}
            className="mt-8 flex flex-col gap-3 rounded-lg border border-line bg-surface p-3 shadow-xs sm:flex-row sm:items-center"
          >
            <label htmlFor="hero-tracking" className="sr-only">
              Tracking ID
            </label>
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
              <input
                id="hero-tracking"
                value={trackingId}
                onChange={(event) => setTrackingId(event.target.value.toUpperCase())}
                placeholder="ORVIA-… or GBQ…"
                className="w-full rounded-md border border-transparent bg-muted py-3 pl-10 pr-4 text-sm uppercase text-ink placeholder:normal-case placeholder:text-ink-muted focus:border-olive focus:outline-none"
              />
            </div>
            <Button type="submit">Track shipment</Button>
          </form>

          <div className="mt-8 grid max-w-md grid-cols-2 gap-3">
            <div className="rounded-lg border border-line bg-surface px-4 py-3">
              <Clock className="mb-2 h-4 w-4 text-olive" />
              <p className="font-display text-2xl text-olive">98%</p>
              <p className="text-xs text-ink-muted">On-time deliveries</p>
            </div>
            <div className="rounded-lg border border-line bg-peach-soft px-4 py-3">
              <ShieldCheck className="mb-2 h-4 w-4 text-olive" />
              <p className="font-display text-2xl text-olive">100%</p>
              <p className="text-xs text-ink-muted">Secure handling</p>
            </div>
          </div>
        </div>

        <div className="relative animate-fade-up stagger-2">
          <div className="absolute -left-6 -top-6 hidden h-28 w-28 rounded-lg bg-peach lg:block" />
          <div className="absolute -bottom-5 -right-5 hidden h-24 w-24 rounded-lg bg-olive lg:block" />
          <img
            src={heroImg}
            alt="Carefully wrapped Softorica parcel on a warm editorial surface"
            className="relative z-10 aspect-[4/3] w-full rounded-lg object-cover shadow-md"
          />
        </div>
      </Container>
    </section>
  );
};

export default Hero;
