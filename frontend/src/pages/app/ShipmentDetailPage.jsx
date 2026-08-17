import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import {
  podEvidenceApi,
  riderApi,
  shipmentApi,
} from '../../services/tenantApi';
import { getApiErrorMessage } from '../../services/errors';
import { formatDate } from '../../utils/format';
import SectionHeading from '../../components/ui/SectionHeading';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import Select from '../../components/ui/Select';
import Input from '../../components/ui/Input';
import LoadingState from '../../components/ui/LoadingState';
import ErrorState from '../../components/ui/ErrorState';
import { StatusBadge } from '../../components/ui/Badge';
import { publicTrackUrl } from '../../utils/tracking';
import {
  PAYMENT_COD,
  formatPickupDisplay,
  paymentMethodFromShipment,
} from '../../utils/shipmentForm';
import { ExternalLink } from 'lucide-react';

const NEXT_STATUS = {
  DRAFT: ['BOOKED'],
  BOOKED: ['PICKED_UP'],
  PICKED_UP: ['IN_TRANSIT'],
  IN_TRANSIT: ['OUT_FOR_DELIVERY'],
  OUT_FOR_DELIVERY: ['DELIVERED'],
};

const ALLOWED_MIME = {
  SIGNATURE: ['image/png', 'image/jpeg', 'image/webp'],
  DELIVERY_PHOTO: ['image/png', 'image/jpeg', 'image/webp'],
};

const ShipmentDetailPage = () => {
  const { id } = useParams();
  const { permissions } = useAuth();
  const [shipment, setShipment] = useState(null);
  const [history, setHistory] = useState([]);
  const [pod, setPod] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [riders, setRiders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [riderId, setRiderId] = useState('');
  const [podForm, setPodForm] = useState({ recipient_name: '', delivery_note: '' });
  const [uploadType, setUploadType] = useState('DELIVERY_PHOTO');
  const [uploadFile, setUploadFile] = useState(null);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [shipRes, histRes] = await Promise.all([
        shipmentApi.get(id),
        shipmentApi.history(id),
      ]);
      setShipment(shipRes.data);
      setHistory(histRes.data.items || []);
      if (shipRes.data.status === 'OUT_FOR_DELIVERY' && permissions.canAssignRiders) {
        const ridersRes = await riderApi.list({ page: 1, page_size: 100, status: 'ACTIVE' });
        setRiders(ridersRes.data.items || []);
      }
      if (['DELIVERED'].includes(shipRes.data.status) && permissions.canReadPod) {
        try {
          const podRes = await shipmentApi.getPod(id);
          setPod(podRes.data);
          const evRes = await podEvidenceApi.list(id);
          setEvidence(evRes.data.items || []);
        } catch (err) {
          if (err?.response?.status !== 404) throw err;
          setPod(null);
          setEvidence([]);
        }
      }
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setShipment(null);
    setHistory([]);
    setPod(null);
    setEvidence([]);
    setRiders([]);
    setError('');
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const run = async (fn, successMessage) => {
    setBusy(true);
    try {
      await fn();
      if (successMessage) toast.success(successMessage);
      await load();
    } catch (err) {
      toast.error(getApiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const onUpload = async (event) => {
    event.preventDefault();
    if (!uploadFile) {
      toast.error('Choose a file');
      return;
    }
    const contentType = uploadFile.type;
    if (!ALLOWED_MIME[uploadType]?.includes(contentType)) {
      toast.error('Use JPEG, PNG, or WebP');
      return;
    }
    setBusy(true);
    try {
      const requested = await podEvidenceApi.requestUpload(id, {
        type: uploadType,
        filename: uploadFile.name,
        content_type: contentType,
        size_bytes: uploadFile.size,
      });
      const { upload_url, headers, upload_id } = requested.data;
      const putHeaders = headers || { 'Content-Type': contentType };
      const putRes = await fetch(upload_url, {
        method: 'PUT',
        headers: putHeaders,
        body: uploadFile,
      });
      if (!putRes.ok) throw new Error('Upload to storage failed');
      await podEvidenceApi.completeUpload(id, upload_id);
      toast.success('Evidence uploaded');
      setUploadFile(null);
      await load();
    } catch (err) {
      toast.error(getApiErrorMessage(err, err.message || 'Upload failed'));
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <LoadingState label="Loading shipment..." />;
  if (error) return <ErrorState description={error} onRetry={load} />;
  if (!shipment) return null;

  const nextStatuses = NEXT_STATUS[shipment.status] || [];

  return (
    <div className="space-y-6 animate-fade-up">
      <SectionHeading
        title={shipment.tracking_number}
        description={shipment.receiver?.name}
        action={
          <div className="flex flex-wrap gap-2">
            <Button to="/app" variant="outline" size="sm">
              Back to Dashboard
            </Button>
            <Button to="/app/shipments" variant="outline" size="sm">
              All shipments
            </Button>
            <Button to={`/app/shipments/${id}/receipt`} variant="outline" size="sm">
              Receipt
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() =>
                window.open(
                  publicTrackUrl(shipment.tracking_number),
                  '_blank',
                  'noopener,noreferrer'
                )
              }
            >
              <ExternalLink className="h-4 w-4" /> Track Shipment
            </Button>
            {permissions.canCancelShipments &&
              ['DRAFT', 'BOOKED'].includes(shipment.status) && (
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={busy}
                  onClick={() =>
                    run(() => shipmentApi.cancel(id, {}), 'Shipment cancelled')
                  }
                >
                  Cancel
                </Button>
              )}
          </div>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <StatusBadge status={shipment.status} />
        {shipment.rider && (
          <span className="text-sm text-ink-secondary">
            Rider: {shipment.rider.name} ({shipment.rider.rider_code})
          </span>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-3 p-5">
          <h2 className="font-display text-lg text-ink">Receiver</h2>
          <p className="text-sm text-ink">{shipment.receiver?.name}</p>
          <p className="text-sm text-ink-secondary">{shipment.receiver?.phone}</p>
          <p className="text-sm text-ink-secondary">
            {shipment.receiver?.address}, {shipment.receiver?.city}
          </p>
        </Card>
        <Card className="space-y-3 p-5">
          <h2 className="font-display text-lg text-ink">Sender</h2>
          <p className="text-sm text-ink">{shipment.sender?.name}</p>
          <p className="text-sm text-ink-secondary">{shipment.sender?.phone}</p>
          <p className="text-sm text-ink-secondary">
            {shipment.sender?.address}, {shipment.sender?.city}
          </p>
        </Card>
        <Card className="space-y-3 p-5 lg:col-span-2">
          <h2 className="font-display text-lg text-ink">Shipment & payment</h2>
          <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-ink-muted">Origin</dt>
              <dd className="font-semibold">{shipment.sender?.city || '—'}</dd>
            </div>
            <div>
              <dt className="text-ink-muted">Destination</dt>
              <dd className="font-semibold">{shipment.receiver?.city || '—'}</dd>
            </div>
            <div>
              <dt className="text-ink-muted">Pickup date</dt>
              <dd>{formatPickupDisplay(shipment.pickup_at)}</dd>
            </div>
            <div>
              <dt className="text-ink-muted">Service</dt>
              <dd>{shipment.service_type || '—'}</dd>
            </div>
            <div>
              <dt className="text-ink-muted">Payment</dt>
              <dd className="font-semibold">
                {paymentMethodFromShipment(shipment) === PAYMENT_COD
                  ? 'Cash on Delivery (COD)'
                  : 'Prepaid'}
              </dd>
            </div>
            <div>
              <dt className="text-ink-muted">COD amount</dt>
              <dd>
                {shipment.cod_amount != null
                  ? `${shipment.currency || ''} ${shipment.cod_amount}`.trim()
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-ink-muted">Weight</dt>
              <dd>
                {shipment.parcel?.weight_kg != null ? `${shipment.parcel.weight_kg} kg` : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-ink-muted">Reference</dt>
              <dd>{shipment.reference_number || '—'}</dd>
            </div>
          </dl>
        </Card>
      </div>

      {permissions.canChangeStatus && nextStatuses.length > 0 && (
        <Card className="flex flex-wrap items-center gap-3 p-5">
          <p className="text-sm font-semibold text-ink">Advance status</p>
          {nextStatuses.map((status) => (
            <Button
              key={status}
              size="sm"
              disabled={busy}
              onClick={() =>
                run(
                  () => shipmentApi.changeStatus(id, { status }),
                  `Marked ${status.replace(/_/g, ' ')}`
                )
              }
            >
              {status.replace(/_/g, ' ')}
            </Button>
          ))}
        </Card>
      )}

      {permissions.canAssignRiders && shipment.status === 'OUT_FOR_DELIVERY' && (
        <Card className="space-y-3 p-5">
          <h2 className="font-display text-lg text-ink">Rider assignment</h2>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Select
              label="Active rider"
              value={riderId}
              onChange={(e) => setRiderId(e.target.value)}
            >
              <option value="">Select rider</option>
              {riders.map((rider) => (
                <option key={rider.id} value={rider.id}>
                  {rider.name} · {rider.rider_code}
                </option>
              ))}
            </Select>
            <div className="flex items-end gap-2">
              <Button
                disabled={busy || !riderId}
                onClick={() =>
                  run(
                    () => shipmentApi.assignRider(id, { rider_id: riderId }),
                    'Rider assigned'
                  )
                }
              >
                Assign
              </Button>
              {shipment.rider_id && (
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() =>
                    run(() => shipmentApi.unassignRider(id), 'Rider unassigned')
                  }
                >
                  Unassign
                </Button>
              )}
            </div>
          </div>
        </Card>
      )}

      <Card className="p-0 overflow-hidden">
        <div className="border-b border-line px-5 py-4">
          <h2 className="font-display text-lg text-ink">Status history</h2>
        </div>
        <ul className="divide-y divide-line">
          {history.map((row) => (
            <li key={row.id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
              <div>
                <p className="font-semibold text-ink">
                  {row.previous_status || '—'} → {row.new_status}
                </p>
                {row.note && <p className="text-xs text-ink-muted">{row.note}</p>}
              </div>
              <span className="text-xs text-ink-muted">{formatDate(row.created_at, true)}</span>
            </li>
          ))}
        </ul>
      </Card>

      {permissions.canReadPod && shipment.status === 'DELIVERED' && (
        <Card className="space-y-4 p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-display text-lg text-ink">Proof of delivery</h2>
            {permissions.canCreatePod && !pod && (
              <form
                className="flex flex-col gap-2 sm:flex-row sm:items-end"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(
                    () =>
                      shipmentApi.createPod(id, {
                        recipient_name: podForm.recipient_name,
                        delivery_note: podForm.delivery_note || null,
                      }),
                    'POD recorded'
                  );
                }}
              >
                <Input
                  label="Recipient name"
                  value={podForm.recipient_name}
                  onChange={(e) =>
                    setPodForm((prev) => ({ ...prev, recipient_name: e.target.value }))
                  }
                  required
                />
                <Input
                  label="Delivery note"
                  value={podForm.delivery_note}
                  onChange={(e) =>
                    setPodForm((prev) => ({ ...prev, delivery_note: e.target.value }))
                  }
                  hint="Optional"
                />
                <Button type="submit" disabled={busy}>
                  Create POD
                </Button>
              </form>
            )}
          </div>
          {pod && (
            <>
              <p className="text-sm text-ink">
                Recipient: {pod.recipient_name} · Delivered{' '}
                {formatDate(pod.delivered_at, true)}
              </p>
              {permissions.canCreatePod && (
                <form onSubmit={onUpload} className="grid gap-3 md:grid-cols-3">
                  <Select
                    label="Evidence type"
                    value={uploadType}
                    onChange={(e) => setUploadType(e.target.value)}
                  >
                    <option value="DELIVERY_PHOTO">Delivery photo</option>
                    <option value="SIGNATURE">Signature</option>
                  </Select>
                  <Input
                    label="File"
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  />
                  <div className="flex items-end">
                    <Button type="submit" disabled={busy} className="w-full">
                      Upload evidence
                    </Button>
                  </div>
                </form>
              )}
              <ul className="divide-y divide-line rounded-md border border-line">
                {evidence.length === 0 && (
                  <li className="px-4 py-3 text-sm text-ink-muted">No evidence yet</li>
                )}
                {evidence.map((item) => (
                  <li
                    key={item.id}
                    className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm"
                  >
                    <div>
                      <p className="font-semibold text-ink">
                        {item.type} · {item.original_filename}
                      </p>
                      <StatusBadge status={item.status} />
                    </div>
                    {item.status === 'UPLOADED' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={async () => {
                          try {
                            const res = await podEvidenceApi.download(id, item.id);
                            window.open(res.data.download_url, '_blank', 'noopener');
                          } catch (err) {
                            toast.error(getApiErrorMessage(err));
                          }
                        }}
                      >
                        Download
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      )}
    </div>
  );
};

export default ShipmentDetailPage;
