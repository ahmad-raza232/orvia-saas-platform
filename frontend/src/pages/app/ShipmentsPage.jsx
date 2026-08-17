import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { shipmentApi } from '../../services/tenantApi';
import { getApiErrorMessage } from '../../services/errors';
import { formatDate } from '../../utils/format';
import SectionHeading from '../../components/ui/SectionHeading';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import Select from '../../components/ui/Select';
import Card from '../../components/ui/Card';
import LoadingState from '../../components/ui/LoadingState';
import EmptyState from '../../components/ui/EmptyState';
import ErrorState from '../../components/ui/ErrorState';
import { StatusBadge } from '../../components/ui/Badge';

const STATUSES = [
  '',
  'DRAFT',
  'BOOKED',
  'PICKED_UP',
  'IN_TRANSIT',
  'OUT_FOR_DELIVERY',
  'DELIVERED',
  'CANCELLED',
];

const ShipmentsPage = () => {
  const { permissions } = useAuth();
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const page = Number(params.get('page') || 1);
  const status = params.get('status') || '';
  const q = params.get('q') || '';

  const load = async () => {
    if (!permissions.canReadShipments) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await shipmentApi.list({
        page,
        page_size: 20,
        ...(status ? { status } : {}),
        ...(q ? { q } : {}),
      });
      setItems(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, status, q, permissions.canReadShipments]);

  if (!permissions.canReadShipments) {
    return (
      <EmptyState
        title="Shipments unavailable"
        description="Your role cannot access operational shipments."
      />
    );
  }

  return (
    <div className="space-y-6 animate-fade-up">
      <SectionHeading
        title="Shipments"
        description={`${total} total in this organization`}
        action={
          permissions.canWriteShipments ? (
            <Button to="/app/shipments/new">New shipment</Button>
          ) : null
        }
      />

      <Card className="p-4">
        <form
          className="grid gap-3 md:grid-cols-[1fr_12rem_auto]"
          onSubmit={(e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            const next = new URLSearchParams(params);
            next.set('page', '1');
            next.set('q', String(form.get('q') || ''));
            next.set('status', String(form.get('status') || ''));
            setParams(next);
          }}
        >
          <Input name="q" defaultValue={q} placeholder="Search tracking, reference, receiver..." />
          <Select name="status" defaultValue={status} label="">
            {STATUSES.map((value) => (
              <option key={value || 'all'} value={value}>
                {value ? value.replace(/_/g, ' ') : 'All statuses'}
              </option>
            ))}
          </Select>
          <Button type="submit" variant="outline">
            Filter
          </Button>
        </form>
      </Card>

      {loading && <LoadingState label="Loading shipments..." />}
      {error && <ErrorState description={error} onRetry={load} />}
      {!loading && !error && items.length === 0 && (
        <EmptyState
          title="No shipments found"
          description="Try another filter or create a shipment."
          actionLabel={permissions.canWriteShipments ? 'Create shipment' : undefined}
          to={permissions.canWriteShipments ? '/app/shipments/new' : undefined}
        />
      )}
      {!loading && !error && items.length > 0 && (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-line bg-muted/50 text-xs uppercase tracking-wide text-ink-muted">
                <tr>
                  <th className="px-4 py-3 font-semibold">Tracking</th>
                  <th className="px-4 py-3 font-semibold">Receiver</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-muted/40">
                    <td className="px-4 py-3">
                      <Link
                        to={`/app/shipments/${item.id}`}
                        className="font-semibold text-olive hover:underline"
                      >
                        {item.tracking_number}
                      </Link>
                      {item.reference_number && (
                        <p className="text-xs text-ink-muted">{item.reference_number}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-ink">{item.receiver_name}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="px-4 py-3 text-ink-secondary">
                      {formatDate(item.created_at, true)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm">
            <span className="text-ink-muted">
              Page {page} · {total} total
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => {
                  const next = new URLSearchParams(params);
                  next.set('page', String(page - 1));
                  setParams(next);
                }}
              >
                Previous
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={page * 20 >= total}
                onClick={() => {
                  const next = new URLSearchParams(params);
                  next.set('page', String(page + 1));
                  setParams(next);
                }}
              >
                Next
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

export default ShipmentsPage;
