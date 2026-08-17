import { createElement, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  Bell,
  Building2,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  Truck,
  Users,
  X,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import Logo from '../ui/Logo';
import Button from '../ui/Button';

const AppShell = () => {
  const { user, organization, organizations, permissions, switchOrganization, logout } =
    useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [switching, setSwitching] = useState(false);

  const links = [
    { to: '/app', label: 'Dashboard', icon: LayoutDashboard, end: true, show: true },
    {
      to: '/app/shipments',
      label: 'Shipments',
      icon: Package,
      show: permissions.canReadShipments,
    },
    {
      to: '/app/customers',
      label: 'Customers',
      icon: Users,
      show: permissions.canManageCustomers,
    },
    {
      to: '/app/riders',
      label: 'Riders',
      icon: Truck,
      show: permissions.canReadRiders,
    },
    {
      to: '/app/notifications',
      label: 'Notifications',
      icon: Bell,
      show: permissions.canReadNotifications,
    },
    {
      to: '/app/organization',
      label: 'Organization',
      icon: Building2,
      show: true,
    },
  ].filter((item) => item.show);

  const onSwitch = async (event) => {
    const next = event.target.value;
    if (!next) return;
    setSwitching(true);
    try {
      await switchOrganization(next);
    } catch {
      /* toast handled upstream if needed */
    } finally {
      setSwitching(false);
    }
  };

  const NavItems = ({ onNavigate }) => (
    <nav className="flex-1 space-y-1 px-3" aria-label="Softorica workspace">
      {links.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
              isActive
                ? 'bg-olive text-peach'
                : 'text-ink-secondary hover:bg-muted hover:text-ink'
            }`
          }
        >
          {createElement(item.icon, { className: 'h-4 w-4', 'aria-hidden': true })}
          {item.label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen bg-canvas lg:grid lg:grid-cols-[16.5rem_1fr]">
      <aside className="hidden border-r border-line bg-surface lg:flex lg:flex-col">
        <div className="px-5 py-5">
          <Logo to="/app" />
        </div>
        <NavItems />
        <div className="border-t border-line p-4">
          <p className="truncate text-sm font-semibold text-ink">{user?.name}</p>
          <p className="truncate text-xs text-ink-muted">{user?.email}</p>
          {organization && (
            <p className="mt-2 truncate text-xs font-medium text-olive">
              {organization.name}
            </p>
          )}
          <button
            type="button"
            onClick={async () => {
              await logout();
              navigate('/');
            }}
            className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-ink-secondary hover:text-danger"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-40 border-b border-line bg-canvas/95 backdrop-blur-md">
          <div className="flex items-center justify-between gap-3 px-4 py-3 lg:px-8">
            <div className="flex items-center gap-3">
              <button
                type="button"
                className="rounded-md p-2 text-ink-secondary hover:bg-muted lg:hidden"
                aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
                onClick={() => setMobileOpen((v) => !v)}
              >
                {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
              <div className="lg:hidden">
                <Logo to="/app" compact />
              </div>
              <div className="hidden lg:block">
                <p className="text-sm text-ink-secondary">
                  {organization?.name || 'Softorica workspace'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {organizations.length > 1 && (
                <label className="sr-only" htmlFor="org-switcher">
                  Switch organization
                </label>
              )}
              {organizations.length > 1 && (
                <select
                  id="org-switcher"
                  className="max-w-[12rem] rounded-md border border-line bg-surface px-2 py-2 text-sm text-ink"
                  value={organization?.id || ''}
                  onChange={onSwitch}
                  disabled={switching}
                >
                  {organizations.map((org) => (
                    <option key={org.id} value={org.id}>
                      {org.name}
                    </option>
                  ))}
                </select>
              )}
              {permissions.canWriteShipments && (
                <Button to="/app/shipments/new" size="sm" className="hidden sm:inline-flex">
                  New shipment
                </Button>
              )}
            </div>
          </div>
          {mobileOpen && (
            <div className="border-t border-line bg-surface px-2 py-3 lg:hidden">
              <NavItems onNavigate={() => setMobileOpen(false)} />
            </div>
          )}
        </header>
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AppShell;
