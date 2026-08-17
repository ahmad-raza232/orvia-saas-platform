import { ShieldCheck, Timer, Handshake } from 'lucide-react';
import { createElement } from 'react';
import Container from './ui/Container';
import SectionHeading from './ui/SectionHeading';

const values = [
  {
    icon: Timer,
    title: 'On the route, on time',
    text: 'Same-day in Lahore and dependable nationwide movement when speed actually matters.',
  },
  {
    icon: ShieldCheck,
    title: 'Handled like it is yours',
    text: 'Secure handling, clear tracking, and a human support line when something needs attention.',
  },
  {
    icon: Handshake,
    title: 'Built for sellers too',
    text: 'COD, remittance, and business plans for shops and e-commerce teams shipping every day.',
  },
];

const Stats = () => (
  <section className="bg-surface py-20" id="trust">
    <Container>
      <SectionHeading
        eyebrow="Why Softorica"
        title="A quieter kind of logistics"
        description="Premium enough for brands. Simple enough for a single parcel."
      />
      <div className="grid gap-5 md:grid-cols-3">
        {values.map((item) => (
          <div key={item.title} className="rounded-lg border border-line bg-canvas p-7">
            {createElement(item.icon, { className: 'h-5 w-5 text-olive' })}
            <h3 className="mt-4 font-display text-xl text-ink">{item.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-secondary">{item.text}</p>
          </div>
        ))}
      </div>
    </Container>
  </section>
);

export default Stats;
