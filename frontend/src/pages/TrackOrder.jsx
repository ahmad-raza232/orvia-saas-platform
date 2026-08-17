import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  MapPin,
  CircleCheck,
  Truck,
  Clock,
  Package,
  TriangleAlert,
} from 'lucide-react';
import axios from 'axios';
import { createElement } from 'react';
import { toast } from 'react-toastify';
import { formatDate, formatStatus } from '../utils/format';
import { StatusBadge } from '../components/ui/Badge';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import ErrorState from '../components/ui/ErrorState';
import Container from '../components/ui/Container';
import { API_URL } from '../config/api';
import {
  fetchSoftoricaPublicTracking,
  isGbqTrackingId,
  isOrviaTrackingId,
  looksLikeOrviaTrackingId,
} from '../utils/tracking';

/**
 * Public ORVIA tracking. GBQ IDs are resolved only as a silent legacy compatibility path.
 */
const TrackOrder = () => {
  const [searchParams] = useSearchParams();
  const [trackingId, setTrackingId] = useState('');
  const [parcel, setParcel] = useState(null);
  const [history, setHistory] = useState([]);
  const [source, setSource] = useState(null); // 'orvia' | 'legacy'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const trackParcelById = useCallback(async (id) => {
    const trimmedId = String(id || '').trim().toUpperCase();
    if (!trimmedId) {
      toast.error('Please enter a tracking ID');
      return;
    }

    setLoading(true);
    setError('');
    setParcel(null);
    setHistory([]);
    setSource(null);

    try {
      if (looksLikeOrviaTrackingId(trimmedId) && !isOrviaTrackingId(trimmedId)) {
        const message =
          'That is not a valid ORVIA tracking ID. Use the format ORVIA-XXXXXXXXXX.';
        setError(message);
        toast.error(message);
        return;
      }

      if (isOrviaTrackingId(trimmedId)) {
        const data = await fetchSoftoricaPublicTracking(trimmedId);
        setSource('orvia');
        setParcel({
          tracking_id: data.tracking_number,
          status: data.status,
          sender_city: data.origin_city,
          receiver_city: data.destination_city,
          receiver_name: data.receiver_name,
          service_type: data.service_type,
          pieces: data.pieces,
          package_type: data.package_type,
          reference_number: data.reference_number,
          has_pod: data.has_pod,
          created_at: data.created_at,
        });
        setHistory(
          (data.history || []).map((item) => ({
            status: item.status,
            description: item.note || undefined,
            created_at: item.created_at,
          }))
        );
        toast.success('Shipment found');
        return;
      }

      if (isGbqTrackingId(trimmedId)) {
        const { data } = await axios.get(`${API_URL}/bookings/track/${trimmedId}`, {
          headers: { 'Content-Type': 'application/json' },
        });
        if (data && data.parcel) {
          setSource('legacy');
          setParcel(data.parcel);
          setHistory(Array.isArray(data.history) ? data.history : []);
          toast.success('Shipment found');
        } else {
          setError('No shipment data returned for this tracking ID.');
          toast.error('No shipment data found');
        }
        return;
      }

      const message =
        'Enter a valid ORVIA tracking ID in the format ORVIA-XXXXXXXXXX.';
      setError(message);
      toast.error(message);
    } catch (err) {
      console.error('Tracking Error:', err);
      let message = 'Unable to track this shipment';
      if (err.response) {
        if (err.response.status === 400) {
          message =
            err.response.data?.error?.message ||
            'That is not a valid ORVIA tracking ID. Use the format ORVIA-XXXXXXXXXX.';
        } else if (err.response.status === 404) {
          message = 'No shipment found for this ORVIA tracking ID. Check the ID and try again.';
        } else if (err.response.status === 500) {
          message = 'Server error. Please try again later.';
        } else {
          message =
            err.response.data?.error?.message ||
            err.response.data?.message ||
            `Error: ${err.response.status}`;
        }
      } else if (err.request) {
        message = 'Cannot connect to the ORVIA tracking service. Please try again.';
      } else {
        message = err.message || 'An unexpected error occurred';
      }
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const urlTrackingId =
      searchParams.get('tracking_id') ||
      searchParams.get('id') ||
      searchParams.get('tracking');
    if (urlTrackingId) {
      const normalized = urlTrackingId.toUpperCase();
      setTrackingId(normalized);
      trackParcelById(normalized);
    }
  }, [searchParams, trackParcelById]);

  const handleTrack = async (event) => {
    event.preventDefault();
    await trackParcelById(trackingId);
  };

  const getStatusIcon = (status = '') => {
    switch (status.toLowerCase()) {
      case 'delivered':
        return CircleCheck;
      case 'out_for_delivery':
      case 'in_transit':
        return Truck;
      case 'picked_up':
      case 'booked':
        return Package;
      case 'confirmed':
      case 'pending':
      case 'draft':
        return Clock;
      case 'cancelled':
        return TriangleAlert;
      default:
        return MapPin;
    }
  };

  return (
    <div className="bg-canvas py-12">
      <Container className="max-w-4xl space-y-8">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-olive">ORVIA tracking</p>
          <h1 className="mt-3 font-display text-h1 text-ink">Track your shipment</h1>
          <p className="mt-2 text-ink-secondary">
            Public tracking uses <span className="font-mono">ORVIA-XXXXXXXXXX</span>. No login required.
          </p>
        </div>

        <Card className="p-6">
          <form onSubmit={handleTrack} className="flex flex-col gap-3 md:flex-row">
            <label htmlFor="tracking-id" className="sr-only">
              Tracking ID
            </label>
            <input
              id="tracking-id"
              type="text"
              value={trackingId}
              onChange={(event) => {
                setTrackingId(event.target.value.toUpperCase());
                setError('');
              }}
              placeholder="ORVIA-XXXXXXXXXX"
              maxLength={24}
              className="flex-1 rounded-md border border-line bg-surface px-4 py-3 uppercase focus:border-olive focus:outline-none focus:ring-4 focus:ring-olive/15"
            />
            <Button type="submit" disabled={loading}>
              {loading ? (
                'Searching…'
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Track
                </>
              )}
            </Button>
          </form>
          {error && (
            <ErrorState className="mt-4" title="Tracking failed" description={error} />
          )}
          <p className="mt-4 text-sm text-ink-muted">
            Example: <strong className="font-mono">ORVIA-KJTDMF2XMK</strong>
          </p>
        </Card>

        {parcel && (
          <div className="space-y-5 animate-fade-up">
            <Card className="bg-olive p-6 text-peach">
              <p className="text-xs uppercase tracking-[0.16em] text-peach/70">
                {source === 'legacy' ? 'Legacy shipment' : 'ORVIA shipment'}
              </p>
              <div className="mt-2 flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-display text-3xl">{formatStatus(parcel.status)}</h2>
                  <p className="mt-1 font-mono text-sm text-peach/80">
                    {parcel.tracking_id || parcel.tracking_number}
                  </p>
                </div>
                <StatusBadge status={parcel.status} />
              </div>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              <Card className="p-5">
                <p className="text-xs uppercase tracking-[0.14em] text-ink-muted">Origin</p>
                <h3 className="mt-1 font-display text-2xl">{parcel.sender_city || 'N/A'}</h3>
                {parcel.sender_name && (
                  <p className="mt-1 text-sm text-ink-secondary">{parcel.sender_name}</p>
                )}
              </Card>
              <Card className="bg-peach-soft p-5">
                <p className="text-xs uppercase tracking-[0.14em] text-olive">Destination</p>
                <h3 className="mt-1 font-display text-2xl">{parcel.receiver_city || 'N/A'}</h3>
                {parcel.receiver_name && (
                  <p className="mt-1 text-sm text-ink-secondary">{parcel.receiver_name}</p>
                )}
              </Card>
            </div>

            <Card className="p-6">
              <h3 className="font-display text-xl">Shipment details</h3>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {parcel.service_type && (
                  <div>
                    <p className="text-sm text-ink-muted">Service</p>
                    <p className="font-semibold">{parcel.service_type}</p>
                  </div>
                )}
                {parcel.pieces != null && (
                  <div>
                    <p className="text-sm text-ink-muted">Pieces</p>
                    <p className="font-semibold">{parcel.pieces}</p>
                  </div>
                )}
                {parcel.package_type && (
                  <div>
                    <p className="text-sm text-ink-muted">Package</p>
                    <p className="font-semibold">{parcel.package_type}</p>
                  </div>
                )}
                {parcel.reference_number && (
                  <div>
                    <p className="text-sm text-ink-muted">Reference</p>
                    <p className="font-semibold">{parcel.reference_number}</p>
                  </div>
                )}
                {parcel.weight != null && (
                  <div>
                    <p className="text-sm text-ink-muted">Weight</p>
                    <p className="font-semibold">{parcel.weight} kg</p>
                  </div>
                )}
                {parcel.parcel_type && (
                  <div>
                    <p className="text-sm text-ink-muted">Type</p>
                    <p className="font-semibold">{parcel.parcel_type}</p>
                  </div>
                )}
                {parcel.has_pod != null && source === 'orvia' && (
                  <div>
                    <p className="text-sm text-ink-muted">Proof of delivery</p>
                    <p className="font-semibold">{parcel.has_pod ? 'Recorded' : 'Not yet'}</p>
                  </div>
                )}
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="mb-6 font-display text-xl">Tracking timeline</h3>
              {history.length > 0 ? (
                <div className="space-y-5">
                  {history.map((item, index) => (
                    <div key={`${item.status}-${index}`} className="relative flex gap-4">
                      {index < history.length - 1 && (
                        <div className="absolute left-4 top-10 h-full w-px bg-line" />
                      )}
                      <div className="z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-olive text-peach">
                        {createElement(getStatusIcon(item.status), { className: 'h-4 w-4' })}
                      </div>
                      <div className="pb-2">
                        <p className="font-semibold">{formatStatus(item.status)}</p>
                        {item.description && (
                          <p className="mt-1 text-sm text-ink-secondary">{item.description}</p>
                        )}
                        {item.location && (
                          <p className="mt-1 flex items-center gap-1 text-sm text-ink-muted">
                            <MapPin className="h-3 w-3" />
                            {item.location}
                          </p>
                        )}
                        <p className="mt-1 text-xs text-ink-muted">
                          {formatDate(item.created_at || item.timestamp, true)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="No tracking history available yet" />
              )}
            </Card>
          </div>
        )}

        {!parcel && !loading && !error && (
          <EmptyState
            icon={Search}
            title="Enter a tracking ID to get started"
            description="Use your ORVIA-XXXXXXXXXX tracking ID from the shipment slip."
          />
        )}
      </Container>
    </div>
  );
};

export default TrackOrder;
