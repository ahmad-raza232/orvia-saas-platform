import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import Container from './ui/Container';
import SectionHeading from './ui/SectionHeading';

const faqs = [
  {
    question: 'Do you offer COD?',
    answer: 'Yes, we specialize in COD services for online sellers and small businesses.',
  },
  {
    question: 'How can I track my parcel?',
    answer: 'Use the tracking section with your GoBurq tracking ID for real-time updates.',
  },
  {
    question: 'Which areas do you cover?',
    answer: 'We cover Lahore for same-day delivery and all major Pakistani cities for nationwide shipping.',
  },
  {
    question: 'Do you provide bulk discounts?',
    answer: 'Yes, we have special business plans for high-volume shippers.',
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
          description="The essentials about coverage, COD, and tracking."
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
