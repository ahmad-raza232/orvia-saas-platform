import { Clock3, MapPinned, Wallet, Building2, Globe, Warehouse } from 'lucide-react';
import { createElement } from 'react';
import Container from './ui/Container';
import SectionHeading from './ui/SectionHeading';
import Card from './ui/Card';

const services = [
  {
    title: 'Same-day delivery',
    description: 'Fast intra-city delivery for urgent packages within Lahore.',
    icon: Clock3,
  },
  {
    title: 'Cash on delivery',
    description: 'Reliable COD for e-commerce sellers and small businesses.',
    icon: Wallet,
  },
  {
    title: 'Nationwide shipping',
    description: 'Affordable parcel services to major cities across Pakistan.',
    icon: MapPinned,
  },
  {
    title: 'Business solutions',
    description: 'Discounted rates and dashboards for high-volume shippers.',
    icon: Building2,
  },
  {
    title: 'Proof of delivery',
    description: 'Capture recipient name, delivery notes, and photo or signature evidence.',
    icon: Globe,
  },
  {
    title: 'Logistics support',
    description: 'Warehousing, inventory handling, and scheduled deliveries.',
    icon: Warehouse,
  },
];

const Services = () => (
  <section className="bg-canvas py-20" id="services">
    <Container>
      <SectionHeading
        eyebrow="Services"
        title="Logistics that stay out of the way"
        description="ORVIA covers the operational loop your team already runs — booking, riders, COD, tracking, and POD."
      />
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {services.map((service) => (
          <Card key={service.title} hover className="p-7">
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-md bg-olive-light text-olive">
              {createElement(service.icon, { className: 'h-5 w-5', 'aria-hidden': true })}
            </div>
            <h3 className="font-display text-h3 text-ink">{service.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-secondary">{service.description}</p>
          </Card>
        ))}
      </div>
    </Container>
  </section>
);

export default Services;
