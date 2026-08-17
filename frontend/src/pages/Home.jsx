import Hero from '../components/Hero';
import Services from '../components/Services';
import Pricing from '../components/Pricing';
import Stats from '../components/Stats';
import TrackingSection from '../components/TrackingSection';
import FAQ from '../components/FAQ';
import Contact from '../components/Contact';
import Container from '../components/ui/Container';
import SectionHeading from '../components/ui/SectionHeading';
import Button from '../components/ui/Button';
import { Package, Search, Truck } from 'lucide-react';
import { createElement } from 'react';

const steps = [
  {
    icon: Package,
    title: 'Book',
    text: 'Share sender, receiver, and parcel details. See the price before you confirm.',
  },
  {
    icon: Truck,
    title: 'Move',
    text: 'We pick up on schedule and keep the shipment on a clear, tracked route.',
  },
  {
    icon: Search,
    title: 'Arrive',
    text: 'Follow the GoBurq tracking ID until it is delivered — and collected on COD if needed.',
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
            For commerce
          </p>
          <h2 className="mt-3 font-display text-h2 text-ink">
            Built for shops that ship every day
          </h2>
          <p className="mt-4 max-w-xl text-ink-secondary">
            COD collections, remittance, bulk rates, and a dashboard for high-volume
            sellers. Keep selling. We will keep the routes moving.
          </p>
          <Button to="/register" className="mt-6">
            Create a business account
          </Button>
        </div>
        <div className="rounded-lg bg-olive p-8 text-peach">
          <p className="font-display text-3xl">COD, nationwide, on your terms.</p>
          <p className="mt-4 text-sm leading-relaxed text-peach/80">
            Optional business and bank details at signup help settle collections faster.
            Custom pricing plans can be assigned to your account.
          </p>
        </div>
      </Container>
    </section>

    <section className="bg-canvas py-20" id="how">
      <Container>
        <SectionHeading
          eyebrow="How it works"
          title="Three calm steps"
          description="No clutter. Just a route from pickup to door."
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

    <Contact />
    <FAQ />

    <section className="bg-olive py-16 text-center text-peach">
      <Container>
        <h2 className="font-display text-h2">Ready when the parcel is.</h2>
        <p className="mx-auto mt-3 max-w-lg text-peach/80">
          Book a pickup or create an account to manage shipments, COD, and tracking in one place.
        </p>
        <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button to="/book-parcel" variant="secondary">
            Book a parcel
          </Button>
          <Button
            to="/register"
            variant="outline"
            className="border-peach/30 bg-transparent text-peach hover:bg-olive-dark"
          >
            Create account
          </Button>
        </div>
      </Container>
    </section>
  </div>
);

export default Home;
