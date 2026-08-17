import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import Container from './ui/Container';
import SectionHeading from './ui/SectionHeading';

const faqs = [
  {
    question: 'Do you support cash on delivery?',
    answer:
      'Yes. ORVIA stores COD amount and currency on each shipment. Prepaid bookings omit COD fields.',
  },
  {
    question: 'How do I track a shipment?',
    answer:
      'Use the public tracking page with an ORVIA-XXXXXXXXXX tracking ID. Recipients do not need to sign in.',
  },
  {
    question: 'Who is Softorica?',
    answer:
      'Softorica is the company that builds and operates ORVIA, the multi-tenant logistics SaaS.',
  },
  {
    question: 'Can my team share one workspace?',
    answer:
      'Yes. Create an organization, invite members, and assign roles. Each organization stays tenant-isolated.',
  },
];

const FAQ = () => {
  const [open, setOpen] = useState(0);

  return (
    <section className="bg-canvas py-20" id="faq">
      <Container className="max-w-3xl">
        <SectionHeading
          eyebrow="FAQ"
          title="Questions, answered plainly"
          description="The essentials about ORVIA tracking, COD, and your Softorica workspace."
        />
        <div className="space-y-3">
          {faqs.map((faq, index) => {
            const isOpen = open === index;
            return (
              <div key={faq.question} className="rounded-lg border border-line bg-surface">
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
                  onClick={() => setOpen(isOpen ? -1 : index)}
                  aria-expanded={isOpen}
                >
                  <span className="font-semibold text-ink">{faq.question}</span>
                  <ChevronDown
                    className={`h-4 w-4 shrink-0 text-olive transition-transform ${isOpen ? 'rotate-180' : ''}`}
                  />
                </button>
                {isOpen && (
                  <p className="px-5 pb-5 text-sm leading-relaxed text-ink-secondary">
                    {faq.answer}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </Container>
    </section>
  );
};

export default FAQ;
