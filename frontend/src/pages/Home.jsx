import Hero from '../components/Hero';
import Services from '../components/Services';
import Pricing from '../components/Pricing';
import Stats from '../components/Stats';
import TrackingSection from '../components/TrackingSection';
import FAQ from '../components/FAQ';
import Container from '../components/ui/Container';
import SectionHeading from '../components/ui/SectionHeading';
import Button from '../components/ui/Button';
import { Package, Search, Truck } from 'lucide-react';
import { createElement } from 'react';

const steps = [
  {
    icon: Package,
    title: 'Book',
    text: 'Capture independent sender and receiver details, parcel data, pickup date, and COD or prepaid.',
  },
  {
    icon: Truck,
    title: 'Operate',
    text: 'Advance status, assign a rider, and record proof of delivery with evidence in your ORVIA workspace.',
  },
  {
    icon: Search,
    title: 'Track',
    text: 'Share an ORVIA-XXXXXXXXXX tracking ID and a public tracking page — no login required.',
  },
];

const Home = () => (
  <div>
    <Hero />
    <Stats />
    <TrackingSection />
    <Services />
    <Pricing />

    <section className="bg-surface py-20" id="business">
      <Container className="grid items-center gap-10 lg:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-olive">
            For operations teams
          </p>
          <h2 className="mt-3 font-display text-h2 text-ink">
            A workspace for shops that ship every day
          </h2>
          <p className="mt-4 max-w-xl text-ink-secondary">
            ORVIA keeps shipments, customers, riders, and notifications in one
            tenant-isolated SaaS. Softorica builds and operates the platform.
          </p>
          <Button to="/register" className="mt-6">
            Get Started
          </Button>
        </div>
        <div className="rounded-lg bg-olive p-8 text-peach">
          <p className="font-display text-3xl">COD, tracking, and POD — in one product.</p>
          <p className="mt-4 text-sm leading-relaxed text-peach/80">
            Create an organization, invite your team, and start booking shipments
            with printable ORVIA slips and QR codes that open public tracking.
          </p>
        </div>
      </Container>
    </section>

    <section className="bg-canvas py-20" id="how">
      <Container>
        <SectionHeading
          eyebrow="How it works"
          title="Three calm steps"
          description="From booking to a public ORVIA tracking page."
        />
        <div className="grid gap-5 md:grid-cols-3">
          {steps.map((step, index) => (
            <div key={step.title} className="rounded-lg border border-line bg-surface p-7">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-olive">
                0{index + 1}
              </p>
              {createElement(step.icon, { className: 'mt-4 h-5 w-5 text-olive' })}
              <h3 className="mt-3 font-display text-xl text-ink">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-secondary">{step.text}</p>
            </div>
          ))}
        </div>
      </Container>
    </section>

    <section className="bg-muted py-20" id="contact">
      <Container className="max-w-3xl text-center">
        <SectionHeading
          eyebrow="Get started"
          title="Open your ORVIA workspace"
          description="Create a Softorica-powered account, set up your organization, and book the first shipment."
        />
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button to="/register" size="lg">
            Get Started
          </Button>
          <Button to="/login" variant="outline" size="lg">
            Login
          </Button>
        </div>
      </Container>
    </section>

    <FAQ />

    <section className="bg-olive py-16 text-center text-peach">
      <Container>
        <h2 className="font-display text-h2">Ready when the parcel is.</h2>
        <p className="mx-auto mt-3 max-w-lg text-peach/80">
          Sign in to manage shipments, riders, customers, COD, and public ORVIA tracking.
        </p>
        <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button to="/login" variant="secondary">
            Login
          </Button>
          <Button
            to="/register"
            variant="outline"
            className="border-peach/30 bg-transparent text-peach hover:bg-olive-dark"
          >
            Get Started
          </Button>
        </div>
      </Container>
    </section>
  </div>
);

export default Home;
