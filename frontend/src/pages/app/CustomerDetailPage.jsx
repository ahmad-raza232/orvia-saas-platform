import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import { customerApi } from '../../services/tenantApi';
import { getApiErrorMessage } from '../../services/errors';
import { formatDate } from '../../utils/format';
import SectionHeading from '../../components/ui/SectionHeading';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import LoadingState from '../../components/ui/LoadingState';
import ErrorState from '../../components/ui/ErrorState';
import EmptyState from '../../components/ui/EmptyState';
import { StatusBadge } from '../../components/ui/Badge';

const CustomerDetailPage = () => {
  const { id } = useParams();
  const { permissions } = useAuth();
  const [customer, setCustomer] = useState(null);
  const [shipments, setShipments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [edit, setEdit] = useState({ name: '', phone: '', email: '', city: '' });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [cRes, sRes] = await Promise.all([
        customerApi.get(id),
        customerApi.shipments(id, { page: 1, page_size: 20 }),
      ]);
      setCustomer(cRes.data);
      setEdit({
        name: cRes.data.name || '',
        phone: cRes.data.phone || '',
        email: cRes.data.email || '',
        city: cRes.data.city || '',
      });
      setShipments(sRes.data.items || []);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (permissions.canManageCustomers) load();
    else setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, permissions.canManageCustomers]);

  if (!permissions.canManageCustomers) {
    return <EmptyState title="Not allowed" description="Customer access denied for this role." />;
  }
  if (loading) return <LoadingState label="Loading Softorica customer…" />;
  if (error) {
    return <ErrorState title="Customer unavailable" description={error} onRetry={load} />;
  }
  if (!customer) return null;

  return (
    <div className="space-y-6 animate-fade-up">
      <SectionHeading
        title={customer.name}
        description={customer.customer_code}
        action={
          <div className="flex gap-2">
            <Button to="/app/customers" variant="outline" size="sm">
              Back
            </Button>
            {permissions.canChangeCustomerStatus && customer.status === 'ACTIVE' && (
              <Button
                size="sm"
                variant="destructive"
                onClick={async () => {
                  try {
                    await customerApi.deactivate(id);
                    toast.success('Customer deactivated');
                    load();
                  } catch (err) {
                    toast.error(getApiErrorMessage(err));
                  }
                }}
              >
                Deactivate
              </Button>
            )}
            {permissions.canChangeCustomerStatus && customer.status !== 'ACTIVE' && (
              <Button
                size="sm"
                onClick={async () => {
                  try {
                    await customerApi.activate(id);
                    toast.success('Customer reactivated');
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
        <StatusBadge status={customer.status} />
        <p className="text-ink">{customer.phone}</p>
        <p className="text-ink-secondary">{customer.email || 'No email'}</p>
        <p className="text-ink-secondary">
          {[customer.city, customer.country].filter(Boolean).join(', ')}
        </p>
      </Card>

      {permissions.canManageCustomers && (
        <Card className="space-y-3 p-5">
          <h2 className="font-display text-lg text-ink">Edit customer</h2>
          <form
            className="grid gap-3 sm:grid-cols-2"
            onSubmit={async (e) => {
              e.preventDefault();
              setSaving(true);
              try {
                await customerApi.update(id, {
                  name: edit.name.trim(),
                  phone: edit.phone.trim(),
                  email: edit.email.trim() || null,
                  city: edit.city.trim() || null,
                });
                toast.success('Customer updated');
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
            <Input
              label="City"
              value={edit.city}
              onChange={(e) => setEdit((v) => ({ ...v, city: e.target.value }))}
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
          <h2 className="font-display text-lg text-ink">Shipments</h2>
        </div>
        {shipments.length === 0 ? (
          <EmptyState
            title="No linked shipments"
            description="Shipments assigned to this customer will appear here."
          />
        ) : (
          <ul className="divide-y divide-line">
            {shipments.map((item) => (
              <li key={item.id} className="flex items-center justify-between px-5 py-3 text-sm">
                <a
                  href={`/app/shipments/${item.id}`}
                  className="font-semibold text-olive hover:underline"
                >
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

export default CustomerDetailPage;
