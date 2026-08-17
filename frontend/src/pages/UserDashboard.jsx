import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Package, Clock, CircleCheck, Truck, Plus, Search } from 'lucide-react';
import { createElement } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { formatDate } from '../utils/format';
import { StatusBadge } from '../components/ui/Badge';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import LoadingState from '../components/ui/LoadingState';
import EmptyState from '../components/ui/EmptyState';
import ErrorState from '../components/ui/ErrorState';
import { API_URL } from '../config/api';

const UserDashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    inTransit: 0,
    delivered: 0,
  });

  useEffect(() => {
    fetchBookings();
  }, []);

  const fetchBookings = async () => {
    try {
      setLoading(true);
      setError('');
      const token = localStorage.getItem('goburq_token');
      if (!token) {
        setLoading(false);
        logout();
        navigate('/login');
        return;
      }

      const response = await axios.get(`${API_URL}/bookings/my-bookings`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.data.success) {
        const userBookings = Array.isArray(response.data.bookings)
          ? response.data.bookings
          : [];
        setBookings(userBookings);
        setStats({
          total: userBookings.length,
          pending: userBookings.filter((booking) =>
            ['pending', 'confirmed'].includes(booking.status?.toLowerCase())
          ).length,
          inTransit: userBookings.filter((booking) =>
            ['in_transit', 'picked_up', 'out_for_delivery'].includes(booking.status?.toLowerCase())
          ).length,
          delivered: userBookings.filter((booking) => booking.status?.toLowerCase() === 'delivered').length,
        });
      }
    } catch (error) {
      console.error('Fetch Bookings Error:', error);
      if (error.response?.status === 401) {
        toast.error('Session expired. Please login again.');
        logout();
        navigate('/login');
      } else {
        setError('Failed to load bookings');
        toast.error('Failed to load bookings');
      }
    } finally {
      setLoading(false);
    }
  };

  const recentBookings = bookings.slice(0, 5);

  if (loading) {
    return <LoadingState label="Loading your dashboard..." />;
  }

  const statCards = [
    { label: 'Total bookings', value: stats.total, icon: Package },
    { label: 'Pending', value: stats.pending, icon: Clock },
    { label: 'In transit', value: stats.inTransit, icon: Truck },
    { label: 'Delivered', value: stats.delivered, icon: CircleCheck },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-olive">Dashboard</p>
        <h1 className="mt-2 font-display text-h1 text-ink">
          Welcome back, {user?.name || 'there'}
        </h1>
        <p className="mt-1 text-ink-secondary">A quiet overview of your parcels.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {statCards.map((stat) => (
          <Card key={stat.label} className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-ink-muted">{stat.label}</p>
                <p className="mt-2 font-display text-3xl text-ink">{stat.value}</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-olive-light text-olive">
                {createElement(stat.icon, { className: 'h-5 w-5' })}
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Button to="/book-parcel" className="h-auto flex-col py-5">
          <Plus className="h-5 w-5" />
          Book new parcel
        </Button>
        <Button to="/track-order" variant="secondary" className="h-auto flex-col py-5">
          <Search className="h-5 w-5" />
          Track order
        </Button>
        <Button to="/user/bookings" variant="outline" className="h-auto flex-col py-5">
          <Package className="h-5 w-5" />
          My bookings
        </Button>
      </div>

      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-6 py-4">
          <h2 className="font-display text-xl text-ink">Recent bookings</h2>
          <Link to="/user/bookings" className="text-sm font-semibold text-olive hover:underline">
            View all
          </Link>
        </div>

        {error && (
          <ErrorState className="mx-6 my-4" title={error} description="You can keep using the dashboard while we retry." />
        )}
        {recentBookings.length > 0 ? (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-sm">
                <thead className="bg-muted text-left text-ink-muted">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Tracking ID</th>
                    <th className="px-6 py-3 font-semibold">Route</th>
                    <th className="px-6 py-3 font-semibold">Status</th>
                    <th className="px-6 py-3 font-semibold">Pickup</th>
                    <th className="px-6 py-3 text-right font-semibold">Price</th>
                  </tr>
                </thead>
                <tbody>
                  {recentBookings.map((booking, index) => (
                    <tr key={booking.id || index} className="border-t border-line">
                      <td className="px-6 py-4 font-mono text-olive">{booking.tracking_id}</td>
                      <td className="px-6 py-4">
                        {booking.sender_city} → {booking.receiver_city}
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={booking.status} />
                      </td>
                      <td className="px-6 py-4">{formatDate(booking.pickup_date)}</td>
                      <td className="px-6 py-4 text-right font-semibold">
                        PKR {parseFloat(booking.price || 0).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="space-y-3 p-4 md:hidden">
              {recentBookings.map((booking, index) => (
                <div key={booking.id || index} className="rounded-md border border-line p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-mono text-sm text-olive">{booking.tracking_id}</p>
                    <StatusBadge status={booking.status} />
                  </div>
                  <p className="mt-2 text-sm text-ink">
                    {booking.sender_city} → {booking.receiver_city}
                  </p>
                  <p className="mt-1 text-xs text-ink-muted">
                    {formatDate(booking.pickup_date)} · PKR {parseFloat(booking.price || 0).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </>
        ) : (
          <EmptyState
            icon={Package}
            title="No bookings yet"
            description="When you book a parcel, it will appear here."
            actionLabel="Book your first parcel"
            to="/book-parcel"
          />
        )}
      </Card>
    </div>
  );
};

export default UserDashboard;
