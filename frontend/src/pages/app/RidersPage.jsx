import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import { riderApi } from '../../services/tenantApi';
import { getApiErrorMessage } from '../../services/errors';
import SectionHeading from '../../components/ui/SectionHeading';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import Select from '../../components/ui/Select';
import LoadingState from '../../components/ui/LoadingState';
import EmptyState from '../../components/ui/EmptyState';
import ErrorState from '../../components/ui/ErrorState';
import { StatusBadge } from '../../components/ui/Badge';
import Modal from '../../components/ui/Modal';

const RidersPage = () => {
  const { permissions } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: '',
    phone: '',
    email: '',
    vehicle_type: 'MOTORCYCLE',
    vehicle_number: '',
  });

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await riderApi.list({ page: 1, page_size: 50 });
      setItems(res.data.items || []);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (permissions.canReadRiders) load();
    else setLoading(false);
  }, [permissions.canReadRiders]);

  if (!permissions.canReadRiders) {
    return <EmptyState title="Riders unavailable" description="Your role cannot access riders." />;
  }

  const create = async (event) => {
    event.preventDefault();
    try {
      await riderApi.create({
        ...form,
        email: form.email || null,
        vehicle_number: form.vehicle_number || null,
      });
      toast.success('Rider created');
      setOpen(false);
      load();
    } catch (err) {
      toast.error(getApiErrorMessage(err));
    }
  };

  return (
    <div className="space-y-6 animate-fade-up">
      <SectionHeading
        title="Riders"
        description="Operational delivery riders for this organization"
        action={
          permissions.canManageRiders ? (
            <Button size="sm" onClick={() => setOpen(true)}>
              New rider
            </Button>
          ) : null
        }
      />
      {loading && <LoadingState label="Loading Softorica riders…" />}
      {error && (
        <ErrorState title="Riders unavailable" description={error} onRetry={load} />
      )}
      {!loading && !error && items.length === 0 && (
        <EmptyState
          title="No riders yet"
          description="Add Softorica riders before assigning out-for-delivery shipments."
          actionLabel={permissions.canManageRiders ? 'New rider' : undefined}
          onAction={permissions.canManageRiders ? () => setOpen(true) : undefined}
        />
      )}
      {!loading && !error && items.length > 0 && (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-line bg-muted/50 text-xs uppercase text-ink-muted">
                <tr>
                  <th className="px-4 py-3">Code</th>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Phone</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-3 font-mono text-xs">{item.rider_code}</td>
                    <td className="px-4 py-3">
                      <Link to={`/app/riders/${item.id}`} className="font-semibold text-olive hover:underline">
                        {item.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-ink-secondary">{item.phone}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Modal open={open} onClose={() => setOpen(false)} className="max-w-md p-5">
        <h2 className="mb-4 font-display text-xl text-ink">New rider</h2>
        <form onSubmit={create} className="space-y-3">
          <Input
            label="Name"
            required
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
          <Input
            label="Phone"
            required
            value={form.phone}
            onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
          />
          <Input
            label="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          />
          <Select
            label="Vehicle type"
            value={form.vehicle_type}
            onChange={(e) => setForm((f) => ({ ...f, vehicle_type: e.target.value }))}
          >
            <option value="MOTORCYCLE">Motorcycle</option>
            <option value="CAR">Car</option>
            <option value="VAN">Van</option>
            <option value="BICYCLE">Bicycle</option>
            <option value="OTHER">Other</option>
          </Select>
          <Input
            label="Vehicle number"
            value={form.vehicle_number}
            onChange={(e) => setForm((f) => ({ ...f, vehicle_number: e.target.value }))}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">Save</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default RidersPage;
