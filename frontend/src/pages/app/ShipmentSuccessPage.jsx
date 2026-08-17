import { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { Copy, ExternalLink } from 'lucide-react';
import { shipmentApi } from '../../services/tenantApi';
import { getApiErrorMessage } from '../../services/errors';
import { absolutePublicTrackUrl, publicTrackUrl } from '../../utils/tracking';
import SoftoricaShipmentSlip from '../../components/ui/SoftoricaShipmentSlip';
import SectionHeading from '../../components/ui/SectionHeading';
import Button from '../../components/ui/Button';
import LoadingState from '../../components/ui/LoadingState';
import ErrorState from '../../components/ui/ErrorState';

const ShipmentSuccessPage = () => {
  const { id } = useParams();
  const location = useLocation();
  const [shipment, setShipment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setShipment(null);
    setLoading(true);
    setError('');

    const boot = async () => {
      try {
        const fromNav = location.state?.shipment;
        if (fromNav && String(fromNav.id) === String(id)) {
          if (!cancelled) setShipment(fromNav);
        }
        const res = await shipmentApi.get(id);
        if (!cancelled) setShipment(res.data);
      } catch (err) {
        if (!cancelled) {
          setError(getApiErrorMessage(err, 'The requested shipment could not be found.'));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    boot();
    return () => {
      cancelled = true;
    };
  }, [id, location.state]);

  if (loading) return <LoadingState label="Loading ORVIA shipment receipt…" />;
  if (error) {
    return (
      <ErrorState
        title="Shipment unavailable"
        description={error}
        onRetry={() => window.location.reload()}
      />
    );
  }
  if (!shipment) return null;

  const trackUrl = absolutePublicTrackUrl(shipment.tracking_number);
  const relativeTrack = publicTrackUrl(shipment.tracking_number);

  const copyTracking = async () => {
    try {
      await navigator.clipboard.writeText(shipment.tracking_number);
      toast.success('Tracking ID copied');
    } catch {
      toast.error('Could not copy tracking ID');
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-fade-up">
      <SectionHeading
        title="Shipment created successfully"
        description="Your ORVIA tracking ID was issued by the API."
        action={
          <div className="flex flex-wrap gap-2">
            <Button to="/app" variant="outline" size="sm">
              Back to Dashboard
            </Button>
            <Button to="/app/shipments/new" size="sm">
              Create Another Shipment
            </Button>
          </div>
        }
      />

      <div className="rounded-md border border-success/25 bg-success-soft px-4 py-4 text-success">
        <p className="text-xs font-semibold uppercase tracking-[0.16em]">Tracking ID</p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <p className="font-mono text-xl font-bold text-ink">{shipment.tracking_number}</p>
          <Button type="button" size="sm" variant="outline" onClick={copyTracking}>
            <Copy className="h-4 w-4" /> Copy Tracking ID
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={() => window.open(relativeTrack, '_blank', 'noopener,noreferrer')}
          >
            <ExternalLink className="h-4 w-4" /> Track Shipment
          </Button>
        </div>
        <p className="mt-2 text-sm text-success/90">
          Opens public ORVIA tracking at{' '}
          <span className="font-mono text-xs">{relativeTrack}</span>
        </p>
      </div>

      <SoftoricaShipmentSlip shipment={shipment} trackUrl={trackUrl} />

      <p className="text-center text-sm text-ink-secondary print:hidden">
        <Link to={`/app/shipments/${shipment.id}`} className="font-semibold text-olive hover:underline">
          Open shipment detail
        </Link>
        {' · '}
        <Link to="/app/shipments" className="font-semibold text-olive hover:underline">
          All shipments
        </Link>
      </p>
    </div>
  );
};

export default ShipmentSuccessPage;
