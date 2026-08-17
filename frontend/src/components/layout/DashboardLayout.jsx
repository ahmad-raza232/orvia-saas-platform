import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { createElement } from 'react';
import {
  LayoutDashboard,
  Package,
  Plus,
  Search,
  UserRound,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import Logo from '../ui/Logo';

const links = [
  { to: '/user/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/user/bookings', label: 'Bookings', icon: Package },
  { to: '/book-parcel', label: 'Book parcel', icon: Plus },
  { to: '/track-order', label: 'Track', icon: Search },
  { to: '/user/profile', label: 'Profile', icon: UserRound },
];

const DashboardLayout = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-canvas lg:grid lg:grid-cols-[16.5rem_1fr]">
      <aside className="hidden border-r border-line bg-surface lg:flex lg:flex-col">
        <div className="px-5 py-5">
          <Logo />
        </div>
        <nav className="flex-1 space-y-1 px-3" aria-label="Dashboard">
          {links.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
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
        <div className="border-t border-line p-4">
          <p className="truncate text-sm font-semibold text-ink">{user?.name}</p>
          <p className="truncate text-xs text-ink-muted">{user?.email}</p>
          <button
            type="button"
            onClick={() => {
              logout();
              navigate('/');
            }}
            className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-ink-secondary hover:text-danger"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </aside>

      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-40 flex items-center justify-between border-b border-line bg-canvas/90 px-4 py-3 backdrop-blur-md lg:px-8">
          <div className="lg:hidden">
            <Logo compact />
          </div>
          <p className="hidden text-sm text-ink-secondary lg:block">
            Welcome back{user?.name ? `, ${user.name}` : ''}
          </p>
          <nav className="flex items-center gap-2 overflow-x-auto lg:hidden" aria-label="Mobile dashboard">
            {links.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-semibold ${
                    isActive ? 'bg-olive text-peach' : 'bg-muted text-ink-secondary'
                  }`
                }
              >
                {createElement(item.icon, { className: 'h-3.5 w-3.5' })}
                {item.label}
              </NavLink>
            ))}
          </nav>
        </header>
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
