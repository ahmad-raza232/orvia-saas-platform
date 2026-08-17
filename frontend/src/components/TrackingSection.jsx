import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Container from './ui/Container';
import SectionHeading from './ui/SectionHeading';
import Button from './ui/Button';

const TrackingSection = () => {
  const [trackingId, setTrackingId] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (event) => {
    event.preventDefault();
    if (trackingId.trim()) {
      navigate(`/track?tracking_id=${trackingId.trim().toUpperCase()}`);
    }
  };

  return (
    <section className="bg-olive py-20 text-peach" id="tracking">
      <Container className="max-w-3xl text-center">
        <SectionHeading
          eyebrow="Public tracking"
          title="Know where it is"
          description="Enter an ORVIA tracking ID. Recipients can check status without signing in."
          className="mb-8 [&_h2]:text-peach [&_p]:text-peach/80 [&_.text-olive]:text-peach/70"
        />
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
          <label htmlFor="home-tracking" className="sr-only">
            ORVIA tracking ID
          </label>
          <input
            id="home-tracking"
            type="text"
            value={trackingId}
            onChange={(event) => setTrackingId(event.target.value.toUpperCase())}
            placeholder="ORVIA-XXXXXXXXXX"
            required
            className="flex-1 rounded-md border border-peach/20 bg-olive-dark px-4 py-3 uppercase text-peach placeholder:normal-case placeholder:text-peach/50 focus:border-peach focus:outline-none"
          />
          <Button type="submit" variant="secondary">
            Track now
          </Button>
        </form>
        <p className="mt-4 text-sm text-peach/70">
          Format: <span className="font-mono text-peach">ORVIA-XXXXXXXXXX</span>
        </p>
      </Container>
    </section>
  );
};

export default TrackingSection;
