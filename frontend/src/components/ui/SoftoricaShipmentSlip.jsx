import { useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'react-toastify';
import html2canvas from 'html2canvas';
import QRCode from 'qrcode';
import { Copy, Download, Printer, ExternalLink } from 'lucide-react';
import Button from './Button';
import { Mark } from './Logo';
import { absolutePublicTrackUrl, publicTrackUrl } from '../../utils/tracking';
import {
  PAYMENT_COD,
  formatPickupDisplay,
  paymentMethodFromShipment,
} from '../../utils/shipmentForm';

function barcodeBars(trackingNumber) {
  const seed = String(trackingNumber || '');
  const bars = [];
  for (let i = 0; i < seed.length; i += 1) {
    const code = seed.charCodeAt(i);
    bars.push(1 + (code % 3));
    bars.push(1 + ((code >> 2) % 2));
  }
  return bars;
}

/**
 * Softorica shipment receipt / slip. Uses only real shipment API fields.
 */
const SoftoricaShipmentSlip = ({ shipment, trackUrl }) => {
  const slipRef = useRef(null);
  const [qrDataUrl, setQrDataUrl] = useState('');
  const [busy, setBusy] = useState(false);

  const trackingNumber = shipment?.tracking_number || '';
  const resolvedTrackUrl =
    trackUrl || absolutePublicTrackUrl(trackingNumber);

  useEffect(() => {
    let cancelled = false;
    if (!resolvedTrackUrl) return undefined;
    QRCode.toDataURL(resolvedTrackUrl, {
      width: 160,
      margin: 1,
      color: { dark: '#1C1917', light: '#FFFFFF' },
    })
      .then((url) => {
        if (!cancelled) setQrDataUrl(url);
      })
      .catch(() => {
        if (!cancelled) setQrDataUrl('');
      });
    return () => {
      cancelled = true;
    };
  }, [resolvedTrackUrl]);

  const bars = useMemo(() => barcodeBars(trackingNumber), [trackingNumber]);

  const copyTracking = async () => {
    try {
      await navigator.clipboard.writeText(trackingNumber);
      toast.success('Tracking number copied');
    } catch {
      toast.error('Could not copy tracking number');
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownload = async () => {
    if (!slipRef.current) return;
    setBusy(true);
    try {
      const canvas = await html2canvas(slipRef.current, {
        scale: 2,
        backgroundColor: '#ffffff',
        useCORS: true,
      });
      const link = document.createElement('a');
      link.download = `orvia-slip-${trackingNumber || shipment?.id}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
      toast.success('Slip downloaded');
    } catch {
      toast.error('Could not download slip');
    } finally {
      setBusy(false);
    }
  };

  if (!shipment) return null;

  const sender = shipment.sender || {};
  const receiver = shipment.receiver || {};
  const parcel = shipment.parcel || {};

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 print:hidden">
        <Button type="button" onClick={handleDownload} disabled={busy}>
          <Download className="h-4 w-4" /> Download Slip
        </Button>
        <Button type="button" variant="outline" onClick={handlePrint}>
          <Printer className="h-4 w-4" /> Print
        </Button>
        <Button type="button" variant="outline" onClick={copyTracking}>
          <Copy className="h-4 w-4" /> Copy Tracking ID
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => window.open(publicTrackUrl(trackingNumber), '_blank', 'noopener,noreferrer')}
        >
          <ExternalLink className="h-4 w-4" /> Track Shipment
        </Button>
      </div>

      <div
        ref={slipRef}
        className="overflow-hidden rounded-lg border border-line bg-white text-ink shadow-sm print:shadow-none"
      >
        <div className="flex flex-col gap-4 border-b-2 border-olive bg-olive px-5 py-4 text-peach sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Mark inverted className="h-10 w-10" />
            <div>
              <p className="font-display text-2xl font-semibold tracking-[0.08em]">ORVIA</p>
              <p className="text-xs uppercase tracking-[0.18em] text-peach/80">
                Shipment slip · Softorica
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-[10px] uppercase tracking-[0.16em] text-peach/70">Tracking Number</p>
              <p className="font-mono text-sm font-bold sm:text-base">{trackingNumber}</p>
            </div>
            {qrDataUrl ? (
              <img
                src={qrDataUrl}
                alt={`QR code for ${trackingNumber}`}
                className="h-20 w-20 rounded-md bg-white p-1"
              />
            ) : (
              <div className="flex h-20 w-20 items-center justify-center rounded-md bg-white/10 text-[10px]">
                QR
              </div>
            )}
          </div>
        </div>

        <div className="border-b border-line px-5 py-3">
          <div className="flex h-12 items-end gap-[1px] overflow-hidden" aria-hidden>
            {bars.map((w, idx) => (
              <span
                key={`${idx}-${w}`}
                className="bg-ink"
                style={{ width: `${w}px`, height: `${18 + (w % 3) * 8}px` }}
              />
            ))}
          </div>
          <p className="mt-1 text-center font-mono text-xs tracking-[0.2em] text-ink-secondary">
            {trackingNumber}
          </p>
        </div>

        <div className="grid gap-0 sm:grid-cols-2">
          <section className="border-b border-line p-5 sm:border-r">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-olive">
              Consignee Information
            </h3>
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-ink-muted">Name</dt>
                <dd className="font-semibold">{receiver.name || '—'}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Contact</dt>
                <dd>{receiver.phone || '—'}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Delivery Address</dt>
                <dd>
                  {[receiver.address, receiver.city, receiver.state, receiver.country]
                    .filter(Boolean)
                    .join(', ') || '—'}
                </dd>
              </div>
            </dl>
          </section>

          <section className="border-b border-line p-5">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-olive">
              Shipper Information
            </h3>
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-ink-muted">Name</dt>
                <dd className="font-semibold">{sender.name || '—'}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Contact</dt>
                <dd>{sender.phone || '—'}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Pickup Address</dt>
                <dd>
                  {[sender.address, sender.city, sender.state, sender.country]
                    .filter(Boolean)
                    .join(', ') || '—'}
                </dd>
              </div>
              <div>
                <dt className="text-ink-muted">Return City</dt>
                <dd>{sender.city || '—'}</dd>
              </div>
            </dl>
          </section>

          <section className="border-b border-line p-5 sm:border-r">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-olive">
              Shipment Information
            </h3>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-ink-muted">Origin</dt>
                <dd className="font-semibold">{sender.city || '—'}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Destination</dt>
                <dd className="font-semibold">{receiver.city || '—'}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Pickup Date</dt>
                <dd>{formatPickupDisplay(shipment.pickup_at)}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Pieces</dt>
                <dd>{parcel.quantity ?? 1}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Weight</dt>
                <dd>{parcel.weight_kg != null ? `${parcel.weight_kg} kg` : '—'}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Package</dt>
                <dd>{parcel.package_type || '—'}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Service</dt>
                <dd>{shipment.service_type || '—'}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Status</dt>
                <dd className="font-semibold">{shipment.status || '—'}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-ink-muted">Order Reference</dt>
                <dd>{shipment.reference_number || '—'}</dd>
              </div>
            </dl>
          </section>

          <section className="border-b border-line p-5">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-olive">
              Order / Payment
            </h3>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-ink-muted">Payment Method</dt>
                <dd className="font-semibold">
                  {paymentMethodFromShipment(shipment) === PAYMENT_COD
                    ? 'Cash on Delivery (COD)'
                    : 'Prepaid'}
                </dd>
              </div>
              <div>
                <dt className="text-ink-muted">Currency</dt>
                <dd>{shipment.currency || '—'}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">COD Amount</dt>
                <dd>
                  {shipment.cod_amount != null
                    ? `${shipment.currency || ''} ${shipment.cod_amount}`.trim()
                    : '—'}
                </dd>
              </div>
              <div>
                <dt className="text-ink-muted">COD Service Charges</dt>
                <dd>
                  {shipment.cod_amount != null ? 'Not applied' : '—'}
                </dd>
              </div>
              <div className="col-span-2">
                <dt className="text-ink-muted">Total Collectable Amount</dt>
                <dd className="font-semibold">
                  {shipment.cod_amount != null
                    ? `${shipment.currency || ''} ${shipment.cod_amount}`.trim()
                    : '—'}
                </dd>
              </div>
              <div className="col-span-2">
                <dt className="text-ink-muted">Remarks</dt>
                <dd>{shipment.notes || parcel.description || '—'}</dd>
              </div>
            </dl>
          </section>
        </div>

        <div className="bg-muted/60 px-5 py-4 text-center">
          <p className="text-xs uppercase tracking-[0.18em] text-ink-muted">Track with ORVIA</p>
          <p className="mt-1 font-mono text-lg font-bold text-olive">{trackingNumber}</p>
          <p className="mt-2 text-xs text-ink-secondary">
            Scan the QR code or open{' '}
            <a
              href={publicTrackUrl(trackingNumber)}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-olive underline"
            >
              public ORVIA tracking
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SoftoricaShipmentSlip;
