import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import { customerApi } from '../../services/tenantApi';
import { getApiErrorMessage } from '../../services/errors';
import SectionHeading from '../../components/ui/SectionHeading';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import LoadingState from '../../components/ui/LoadingState';
import EmptyState from '../../components/ui/EmptyState';
import ErrorState from '../../components/ui/ErrorState';
import { StatusBadge } from '../../components/ui/Badge';
import Modal from '../../components/ui/Modal';

const CustomersPage = () => {
  const { permissions } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: '',
    phone: '',
    email: '',
    city: '',
    country: 'PK',
  });

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await customerApi.list({ page: 1, page_size: 50 });
      setItems(res.data.items || []);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (permissions.canManageCustomers) load();
    else setLoading(false);
  }, [permissions.canManageCustomers]);

  if (!permissions.canManageCustomers) {
    return (
      <EmptyState
        title="Customers unavailable"
        description="Your role cannot access customer CRM."
      />
    );
  }

  const create = async (event) => {
    event.preventDefault();
    try {
      await customerApi.create({
        ...form,
        email: form.email || null,
        city: form.city || null,
      });
      toast.success('Customer created');
      setOpen(false);
      setForm({ name: '', phone: '', email: '', city: '', country: 'PK' });
      load();
    } catch (err) {
      toast.error(getApiErrorMessage(err));
    }
  };

  return (
    <div className="space-y-6 animate-fade-up">
      <SectionHeading
        title="Customers"
        description="Tenant-scoped CRM records"
        action={
          <Button size="sm" onClick={() => setOpen(true)}>
            New customer
          </Button>
        }
      />
      {loading && <LoadingState label="Loading Softorica customers…" />}
      {error && (
        <ErrorState title="Customers unavailable" description={error} onRetry={load} />
      )}
      {!loading && !error && items.length === 0 && (
        <EmptyState
          title="No customers yet"
          description="Add a Softorica customer to link them to shipments."
          actionLabel="New customer"
          onAction={() => setOpen(true)}
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
                  <tr key={item.id} className="hover:bg-muted/40">
                    <td className="px-4 py-3 font-mono text-xs">{item.customer_code}</td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/app/customers/${item.id}`}
                        className="font-semibold text-olive hover:underline"
                      >
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
        <h2 className="mb-4 font-display text-xl text-ink">New customer</h2>
        <form onSubmit={create} className="space-y-3" autoComplete="off">
          <Input
            label="Name"
            name="customer-name"
            required
            autoComplete="off"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
          <Input
            label="Phone"
            name="customer-phone"
            required
            autoComplete="off"
            value={form.phone}
            onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
          />
          <Input
            label="Email"
            type="email"
            name="customer-email"
            autoComplete="off"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          />
          <Input
            label="City"
            name="customer-city"
            autoComplete="off"
            value={form.city}
            onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))}
          />
          <Input
            label="Country"
            name="customer-country"
            autoComplete="off"
            value={form.country}
            onChange={(e) => setForm((f) => ({ ...f, country: e.target.value.toUpperCase() }))}
            maxLength={2}
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

export default CustomersPage;
