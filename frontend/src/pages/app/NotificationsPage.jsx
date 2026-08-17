import { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import { notificationApi } from '../../services/tenantApi';
import { getApiErrorMessage } from '../../services/errors';
import { formatDate } from '../../utils/format';
import SectionHeading from '../../components/ui/SectionHeading';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import LoadingState from '../../components/ui/LoadingState';
import EmptyState from '../../components/ui/EmptyState';
import ErrorState from '../../components/ui/ErrorState';
import { StatusBadge } from '../../components/ui/Badge';

const NotificationsPage = () => {
  const { permissions } = useAuth();
  const [items, setItems] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [settingsLoadError, setSettingsLoadError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    let listError = '';
    let settingsError = '';
    try {
      const listRes = await notificationApi.list({ page: 1, page_size: 50 });
      setItems(listRes.data.items || []);
    } catch (err) {
      listError = getApiErrorMessage(err, 'Notifications failed to load');
      setItems([]);
    }
    if (permissions.canReadNotifications) {
      try {
        const settingsRes = await notificationApi.getSettings();
        setSettings(settingsRes.data);
      } catch (err) {
        settingsError = getApiErrorMessage(err, 'Email settings failed to load');
        setSettings(null);
      }
    }
    setError(listError);
    setSettingsLoadError(settingsError);
    setLoading(false);
  };

  useEffect(() => {
    if (permissions.canReadNotifications) load();
    else setLoading(false);
  }, [permissions.canReadNotifications]);

  if (!permissions.canReadNotifications) {
    return (
      <EmptyState
        title="Notifications unavailable"
        description="Notification history is limited to tenant admins and operations managers."
      />
    );
  }

  if (loading) return <LoadingState label="Loading Softorica notifications…" />;
  if (error) {
    return (
      <ErrorState title="Notifications unavailable" description={error} onRetry={load} />
    );
  }

  const emailSettings = settings?.email || {};

  return (
    <div className="space-y-6 animate-fade-up">
      <SectionHeading
        title="Notifications"
        description="Delivery history from the Softorica transactional outbox"
      />

      {permissions.canWriteNotificationSettings && (
        <Card className="space-y-3 p-5">
          <h2 className="font-display text-lg text-ink">Email settings</h2>
          {settingsLoadError ? (
            <ErrorState
              title="Settings unavailable"
              description={settingsLoadError}
              onRetry={load}
            />
          ) : (
            <>
              <p className="text-sm text-ink-muted">
                Toggle which domain events send email. Changes are organization-scoped.
              </p>
              <ul className="space-y-2">
                {Object.entries(emailSettings).map(([key, enabled]) => (
                  <li key={key} className="flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium text-ink">{key}</span>
                    <Button
                      size="sm"
                      variant={enabled ? 'primary' : 'outline'}
                      onClick={async () => {
                        try {
                          const next = { email: { ...emailSettings, [key]: !enabled } };
                          const res = await notificationApi.updateSettings(next);
                          setSettings(res.data);
                          toast.success('Settings updated');
                        } catch (err) {
                          toast.error(getApiErrorMessage(err));
                        }
                      }}
                    >
                      {enabled ? 'Enabled' : 'Disabled'}
                    </Button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      )}

      {items.length === 0 ? (
        <EmptyState
          title="No notifications yet"
          description="When Softorica shipments change status, notification rows appear after the worker processes the outbox."
        />
      ) : (
        <Card className="overflow-hidden p-0">
          <ul className="divide-y divide-line">
            {items.map((item) => (
              <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-ink">
                    {item.event_type || item.subject || 'Notification'}
                  </p>
                  <p className="truncate text-xs text-ink-muted">
                    {item.recipient || item.channel} · {formatDate(item.created_at, true)}
                  </p>
                </div>
                <StatusBadge status={item.status} />
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
};

export default NotificationsPage;
