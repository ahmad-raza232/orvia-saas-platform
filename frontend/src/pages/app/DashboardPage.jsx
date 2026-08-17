import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Package, Truck, Users, Bell } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { customerApi, notificationApi, riderApi, shipmentApi } from '../../services/tenantApi';
import { getApiErrorMessage } from '../../services/errors';
import { formatDate } from '../../utils/format';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import LoadingState from '../../components/ui/LoadingState';
import EmptyState from '../../components/ui/EmptyState';
import ErrorState from '../../components/ui/ErrorState';
import { StatusBadge } from '../../components/ui/Badge';
import SectionHeading from '../../components/ui/SectionHeading';

const DashboardPage = () => {
  const { organization, permissions } = useAuth();
  const [shipments, setShipments] = useState([]);
  const [total, setTotal] = useState(0);
  const [statusTotals, setStatusTotals] = useState({});
  const [notifications, setNotifications] = useState([]);
  const [counts, setCounts] = useState({ customers: 0, riders: 0, notifications: 0 });
  const [countErrors, setCountErrors] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [shipmentsError, setShipmentsError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    setShipmentsError('');
    setCountErrors({});
    const nextStatus = {};
    const nextErrors = {};
    try {
      const tasks = [];
      if (permissions.canReadShipments) {
        tasks.push(
          Promise.all([
            shipmentApi.list({ page: 1, page_size: 8 }),
            shipmentApi.list({ page: 1, page_size: 1, status: 'BOOKED' }),
            shipmentApi.list({ page: 1, page_size: 1, status: 'IN_TRANSIT' }),
            shipmentApi.list({ page: 1, page_size: 1, status: 'OUT_FOR_DELIVERY' }),
            shipmentApi.list({ page: 1, page_size: 1, status: 'DELIVERED' }),
          ])
            .then(([recent, booked, transit, ofd, delivered]) => {
              setShipments(recent.data.items || []);
              setTotal(recent.data.total || 0);
              setStatusTotals({
                BOOKED: booked.data.total || 0,
                IN_TRANSIT: transit.data.total || 0,
                OUT_FOR_DELIVERY: ofd.data.total || 0,
                DELIVERED: delivered.data.total || 0,
              });
            })
            .catch((err) => {
              setShipmentsError(getApiErrorMessage(err, 'Shipments failed to load'));
              setShipments([]);
              setTotal(0);
              setStatusTotals({});
            })
        );
      }
      if (permissions.canManageCustomers) {
        tasks.push(
          customerApi
            .list({ page: 1, page_size: 1 })
            .then((res) => {
              nextStatus.customers = res.data.total || 0;
            })
            .catch(() => {
              nextStatus.customers = null;
              nextErrors.customers = true;
            })
        );
      }
      if (permissions.canReadRiders) {
        tasks.push(
          riderApi
            .list({ page: 1, page_size: 1 })
            .then((res) => {
              nextStatus.riders = res.data.total || 0;
            })
            .catch(() => {
              nextStatus.riders = null;
              nextErrors.riders = true;
            })
        );
      }
      if (permissions.canReadNotifications) {
        tasks.push(
          notificationApi
            .list({ page: 1, page_size: 5 })
            .then((res) => {
              setNotifications(res.data.items || []);
              nextStatus.notifications = res.data.total || 0;
            })
            .catch((err) => {
              console.warn('[ORVIA] dashboard notifications:', getApiErrorMessage(err));
              setNotifications([]);
              nextStatus.notifications = null;
              nextErrors.notifications = true;
            })
        );
      }
      await Promise.all(tasks);
      setCounts({
        customers: nextStatus.customers ?? 0,
        riders: nextStatus.riders ?? 0,
        notifications: nextStatus.notifications ?? 0,
      });
      setCountErrors(nextErrors);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to load dashboard'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organization?.id, permissions.canReadShipments, permissions.canReadNotifications]);

  const statusCounts = statusTotals;

  if (loading) return <LoadingState label="Loading ORVIA dashboard…" />;
  if (error) {
    return (
      <ErrorState title="Dashboard unavailable" description={error} onRetry={load} />
    );
  }

  if (permissions.isCustomer) {
    return (
      <EmptyState
        title="Customer access"
        description="Operational shipment tools are not available for the CUSTOMER role. Contact your organization admin."
      />
    );
  }

  return (
    <div className="space-y-8 animate-fade-up">
      <SectionHeading
        title="Dashboard"
        description={
          organization
            ? `Operational overview for ${organization.name}`
            : 'Operational overview'
        }
        action={
          permissions.canWriteShipments ? (
            <Button to="/app/shipments/new">New shipment</Button>
          ) : null
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <Package className="h-5 w-5 text-olive" aria-hidden />
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
                Total shipments
              </p>
              <p className="mt-1 font-display text-2xl text-ink">{total}</p>
            </div>
          </div>
        </Card>
        {permissions.canManageCustomers && (
          <Card className="p-5">
            <div className="flex items-center gap-3">
              <Users className="h-5 w-5 text-olive" aria-hidden />
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
                  Customers
                </p>
                  <p className="mt-1 font-display text-2xl text-ink">
                    {countErrors.customers ? '—' : counts.customers}
                  </p>
              </div>
            </div>
          </Card>
        )}
        {permissions.canReadRiders && (
          <Card className="p-5">
            <div className="flex items-center gap-3">
              <Truck className="h-5 w-5 text-olive" aria-hidden />
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
                  Riders
                </p>
                  <p className="mt-1 font-display text-2xl text-ink">
                    {countErrors.riders ? '—' : counts.riders}
                  </p>
              </div>
            </div>
          </Card>
        )}
        {permissions.canReadNotifications && (
          <Card className="p-5">
            <div className="flex items-center gap-3">
              <Bell className="h-5 w-5 text-olive" aria-hidden />
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
                  Notifications
                </p>
                  <p className="mt-1 font-display text-2xl text-ink">
                    {countErrors.notifications ? '—' : counts.notifications}
                  </p>
              </div>
            </div>
          </Card>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ['BOOKED', 'Pending'],
          ['IN_TRANSIT', 'In transit'],
          ['OUT_FOR_DELIVERY', 'Out for delivery'],
          ['DELIVERED', 'Delivered'],
        ].map(([key, label]) => (
          <Card key={key} className="p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{label}</p>
            <p className="mt-2 font-display text-2xl text-ink">{statusCounts[key] || 0}</p>
          </Card>
        ))}
      </div>

      {shipmentsError && (
        <ErrorState
          title="Shipments unavailable"
          description={shipmentsError}
          onRetry={load}
        />
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="overflow-hidden p-0">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <h2 className="font-display text-lg text-ink">Recent shipments</h2>
            <Link to="/app/shipments" className="text-sm font-semibold text-olive hover:underline">
              View all
            </Link>
          </div>
          {!shipmentsError && shipments.length === 0 ? (
            <div className="p-6">
              <EmptyState
                title="No shipments yet"
                description="Create your first ORVIA shipment to start operations."
                actionLabel={permissions.canWriteShipments ? 'Create shipment' : undefined}
                to={permissions.canWriteShipments ? '/app/shipments/new' : undefined}
              />
            </div>
          ) : !shipmentsError ? (
            <ul className="divide-y divide-line">
              {shipments.map((item) => (
                <li key={item.id}>
                  <Link
                    to={`/app/shipments/${item.id}`}
                    className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-muted/60"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-ink">{item.tracking_number}</p>
                      <p className="truncate text-xs text-ink-muted">
                        {item.receiver_name} · {formatDate(item.created_at, true)}
                      </p>
                    </div>
                    <StatusBadge status={item.status} />
                  </Link>
                </li>
              ))}
            </ul>
          ) : null}
        </Card>

        <Card className="p-0 overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <h2 className="font-display text-lg text-ink">Notifications</h2>
            {permissions.canReadNotifications && (
              <Link
                to="/app/notifications"
                className="text-sm font-semibold text-olive hover:underline"
              >
                View all
              </Link>
            )}
          </div>
          {!permissions.canReadNotifications ? (
            <div className="p-6 text-sm text-ink-muted">
              Notification history is available to tenant admins and operations managers.
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-6">
              <EmptyState
                title="No notifications yet"
                description="Delivery events will appear here when the outbox worker processes them."
              />
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {notifications.map((item) => (
                <li key={item.id} className="px-5 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-ink">
                        {item.event_type || item.subject || 'Notification'}
                      </p>
                      <p className="truncate text-xs text-ink-muted">
                        {item.recipient || item.channel} · {formatDate(item.created_at, true)}
                      </p>
                    </div>
                    <StatusBadge status={item.status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="flex flex-wrap gap-3">
        {permissions.canManageCustomers && (
          <Button to="/app/customers" variant="outline">
            <Users className="h-4 w-4" /> Customers
          </Button>
        )}
        {permissions.canReadRiders && (
          <Button to="/app/riders" variant="outline">
            <Truck className="h-4 w-4" /> Riders
          </Button>
        )}
        {permissions.canReadNotifications && (
          <Button to="/app/notifications" variant="outline">
            <Bell className="h-4 w-4" /> Notifications
          </Button>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;
