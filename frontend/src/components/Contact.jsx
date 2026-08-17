import { useState } from 'react';
import { toast } from 'react-toastify';
import { contactService } from '../services/api';
import Container from './ui/Container';
import SectionHeading from './ui/SectionHeading';
import Input from './ui/Input';
import Textarea from './ui/Textarea';
import Button from './ui/Button';
import Card from './ui/Card';

const Contact = () => {
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    message: '',
  });
  const [loading, setLoading] = useState(false);

  const handleChange = (event) => {
    setFormData({
      ...formData,
      [event.target.name]: event.target.value,
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);

    try {
      const result = await contactService.submitContactForm(formData);

      if (result.success) {
        toast.success(result.message || "Message sent! We'll contact you soon.");
        setFormData({ name: '', phone: '', email: '', message: '' });
      } else {
        toast.error(result.message || 'Failed to send message');
      }
    } catch (error) {
      console.error('Contact form error:', error);
      toast.error('Failed to send message. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-muted py-20" id="contact">
      <Container className="max-w-3xl">
        <SectionHeading
          eyebrow="Pickup"
          title="Book a pickup"
          description="Share a few details and a rider will contact you within one business day."
        />
        <Card className="p-6 sm:p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid gap-5 md:grid-cols-2">
              <Input
                label="Name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="Enter your name"
                required
              />
              <Input
                label="Phone / WhatsApp"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                placeholder="03xx-xxxxxxx"
                required
              />
            </div>
            <Input
              label="Email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="you@example.com"
            />
            <Textarea
              label="Parcel details"
              name="message"
              value={formData.message}
              onChange={handleChange}
              placeholder="Write parcel details..."
              rows={5}
              required
            />
            <div className="flex flex-col items-center gap-3">
              <Button type="submit" disabled={loading} className="min-w-48">
                {loading ? 'Sending...' : 'Send request'}
              </Button>
              <p className="text-sm text-ink-muted">
                Or call us at{' '}
                <a href="tel:+923263253256" className="font-semibold text-olive">
                  0326 3253256
                </a>
              </p>
            </div>
          </form>
        </Card>
      </Container>
    </section>
  );
};

export default Contact;
