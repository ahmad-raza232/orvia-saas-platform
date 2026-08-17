import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check } from 'lucide-react';
import Container from './ui/Container';
import SectionHeading from './ui/SectionHeading';
import Card from './ui/Card';
import Button from './ui/Button';

const plans = [
  {
    name: 'Intra-City',
    subtitle: 'Within Lahore',
    price: 'PKR 200+',
    features: ['Same-day delivery', 'COD available', 'Pickup from doorstep'],
  },
  {
    name: 'Nationwide',
    subtitle: 'Across Pakistan',
    price: 'PKR 250+',
    features: ['Next-day delivery', 'COD remittance', 'Tracking portal'],
  },
  {
    name: 'Business',
    subtitle: 'Bulk shippers',
    price: 'Custom',
    features: ['Discounted rates', 'Dashboard & API', 'Dedicated support'],
  },
];

const Pricing = () => {
  const [selectedPlan, setSelectedPlan] = useState(1);
  const navigate = useNavigate();

  return (
    <section className="bg-peach-soft py-20" id="pricing">
      <Container>
        <SectionHeading
          eyebrow="Pricing"
          title="Clear rates. No theatre."
          description="Transparent and affordable rates for all your courier needs."
        />
        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {plans.map((plan, index) => {
            const selected = selectedPlan === index;
            return (
              <Card
                key={plan.name}
                className={`cursor-pointer p-8 transition-all duration-200 ${
                  selected ? 'border-olive ring-2 ring-olive/20' : ''
                }`}
                onClick={() => setSelectedPlan(index)}
              >
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-olive">
                  {plan.subtitle}
                </p>
                <h3 className="mt-2 font-display text-2xl text-ink">{plan.name}</h3>
                <p className="mt-4 font-display text-4xl text-olive">{plan.price}</p>
                <ul className="mt-6 space-y-3 text-sm text-ink-secondary">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-olive" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Button
                  className="mt-8 w-full"
                  variant={selected ? 'primary' : 'outline'}
                  onClick={(event) => {
                    event.stopPropagation();
                    setSelectedPlan(index);
                    navigate('/register');
                  }}
                >
                  {selected ? 'Continue' : 'Select'}
                </Button>
              </Card>
            );
          })}
        </div>
      </Container>
    </section>
  );
};

export default Pricing;
