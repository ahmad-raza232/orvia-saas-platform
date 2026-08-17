import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import { riderApi } from '../../services/tenantApi';
import { getApiErrorMessage } from '../../services/errors';
import { formatDate } from '../../utils/format';
import SectionHeading from '../../components/ui/SectionHeading';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import Select from '../../components/ui/Select';
import LoadingState from '../../components/ui/LoadingState';
import ErrorState from '../../components/ui/ErrorState';
import EmptyState from '../../components/ui/EmptyState';
import { StatusBadge } from '../../components/ui/Badge';

const RiderDetailPage = () => {
  const { id } = useParams();
  const { permissions } = useAuth();
  const [rider, setRider] = useState(null);
  const [shipments, setShipments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [edit, setEdit] = useState({
    name: '',
    phone: '',
    email: '',
    vehicle_type: 'MOTORCYCLE',
    vehicle_number: '',
  });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [rRes, sRes] = await Promise.all([
        riderApi.get(id),
        riderApi.shipments(id, { page: 1, page_size: 20 }),
      ]);
      setRider(rRes.data);
      setEdit({
        name: rRes.data.name || '',
        phone: rRes.data.phone || '',
        email: rRes.data.email || '',
        vehicle_type: rRes.data.vehicle_type || 'MOTORCYCLE',
        vehicle_number: rRes.data.vehicle_number || '',
      });
      setShipments(sRes.data.items || []);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (permissions.canReadRiders) load();
    else setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, permissions.canReadRiders]);

  if (!permissions.canReadRiders) {
    return <EmptyState title="Not allowed" description="Rider access denied for this role." />;
  }
  if (loading) return <LoadingState label="Loading Softorica rider…" />;
  if (error) {
    return <ErrorState title="Rider unavailable" description={error} onRetry={load} />;
  }
  if (!rider) return null;

  return (
    <div className="space-y-6 animate-fade-up">
      <SectionHeading
        title={rider.name}
        description={rider.rider_code}
        action={
          <div className="flex gap-2">
            <Button to="/app/riders" variant="outline" size="sm">
              Back
            </Button>
            {permissions.canManageRiders && rider.status === 'ACTIVE' && (
              <Button
                size="sm"
                variant="destructive"
                onClick={async () => {
                  try {
                    await riderApi.deactivate(id);
                    toast.success('Rider deactivated');
                    load();
                  } catch (err) {
                    toast.error(getApiErrorMessage(err));
                  }
                }}
              >
                Deactivate
              </Button>
            )}
            {permissions.canManageRiders && rider.status !== 'ACTIVE' && (
              <Button
                size="sm"
                onClick={async () => {
                  try {
                    await riderApi.activate(id);
                    toast.success('Rider reactivated');
                    load();
                  } catch (err) {
                    toast.error(getApiErrorMessage(err));
                  }
                }}
              >
                Reactivate
              </Button>
            )}
          </div>
        }
      />
      <Card className="space-y-2 p-5 text-sm">
        <StatusBadge status={rider.status} />
        <p className="text-ink">{rider.phone}</p>
        <p className="text-ink-secondary">{rider.email || 'No email'}</p>
        <p className="text-ink-secondary">
          {[rider.vehicle_type, rider.vehicle_number].filter(Boolean).join(' · ')}
        </p>
      </Card>

      {permissions.canManageRiders && (
        <Card className="space-y-3 p-5">
          <h2 className="font-display text-lg text-ink">Edit rider</h2>
          <form
            className="grid gap-3 sm:grid-cols-2"
            onSubmit={async (e) => {
              e.preventDefault();
              setSaving(true);
              try {
                await riderApi.update(id, {
                  name: edit.name.trim(),
                  phone: edit.phone.trim(),
                  email: edit.email.trim() || null,
                  vehicle_type: edit.vehicle_type,
                  vehicle_number: edit.vehicle_number.trim() || null,
                });
                toast.success('Rider updated');
                load();
              } catch (err) {
                toast.error(getApiErrorMessage(err));
              } finally {
                setSaving(false);
              }
            }}
          >
            <Input
              label="Name"
              required
              value={edit.name}
              onChange={(e) => setEdit((v) => ({ ...v, name: e.target.value }))}
            />
            <Input
              label="Phone"
              required
              value={edit.phone}
              onChange={(e) => setEdit((v) => ({ ...v, phone: e.target.value }))}
            />
            <Input
              label="Email"
              type="email"
              value={edit.email}
              onChange={(e) => setEdit((v) => ({ ...v, email: e.target.value }))}
            />
            <Select
              label="Vehicle type"
              value={edit.vehicle_type}
              onChange={(e) => setEdit((v) => ({ ...v, vehicle_type: e.target.value }))}
            >
              <option value="MOTORCYCLE">Motorcycle</option>
              <option value="CAR">Car</option>
              <option value="VAN">Van</option>
              <option value="BICYCLE">Bicycle</option>
              <option value="OTHER">Other</option>
            </Select>
            <Input
              label="Vehicle number"
              value={edit.vehicle_number}
              onChange={(e) => setEdit((v) => ({ ...v, vehicle_number: e.target.value }))}
            />
            <div className="sm:col-span-2">
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : 'Save changes'}
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card className="overflow-hidden p-0">
        <div className="border-b border-line px-5 py-4">
          <h2 className="font-display text-lg text-ink">Assigned shipments</h2>
        </div>
        {shipments.length === 0 ? (
          <EmptyState
            title="No assigned shipments"
            description="Assignments appear when this rider is linked to out-for-delivery work."
          />
        ) : (
          <ul className="divide-y divide-line">
            {shipments.map((item) => (
              <li key={item.id} className="flex items-center justify-between px-5 py-3 text-sm">
                <a href={`/app/shipments/${item.id}`} className="font-semibold text-olive hover:underline">
                  {item.tracking_number}
                </a>
                <span className="text-xs text-ink-muted">{formatDate(item.created_at, true)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
};

export default RiderDetailPage;
