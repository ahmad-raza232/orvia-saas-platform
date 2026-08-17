import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Search, Eye, Trash2, Package } from 'lucide-react';
import { toast } from 'react-toastify';
import axios from 'axios';
import { formatDate } from '../utils/format';
import { StatusBadge } from '../components/ui/Badge';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import LoadingState from '../components/ui/LoadingState';
import EmptyState from '../components/ui/EmptyState';
import ErrorState from '../components/ui/ErrorState';
import { API_URL } from '../config/api';

const MyBookings = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [bookings, setBookings] = useState([]);
  const [filteredBookings, setFilteredBookings] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadBookings();
  }, []);

  useEffect(() => {
    filterBookings();
  }, [searchTerm, filterStatus, bookings]);

  const loadBookings = async () => {
    try {
      setLoading(true);
      setError('');
      const token = localStorage.getItem('goburq_token');
      if (!token) {
        toast.error('Please login to view your bookings');
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
        setFilteredBookings(userBookings);
      }
    } catch (error) {
      console.error('Load Bookings Error:', error);
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

  const filterBookings = () => {
    let result = bookings;
    if (searchTerm) {
      result = result.filter(
        (booking) =>
          booking.tracking_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          booking.sender_city?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          booking.receiver_city?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          booking.sender_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          booking.receiver_name?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    if (filterStatus !== 'all') {
      result = result.filter((booking) => booking.status?.toLowerCase() === filterStatus.toLowerCase());
    }
    setFilteredBookings(result);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to cancel this booking?')) return;

    try {
      const token = localStorage.getItem('goburq_token');
      await axios.delete(`${API_URL}/bookings/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      toast.success('Booking cancelled successfully');
      loadBookings();
    } catch (error) {
      console.error('Delete Booking Error:', error);
      toast.error(error.response?.data?.message || 'Failed to cancel booking');
    }
  };

  if (loading) {
    return <LoadingState label="Loading your bookings..." />;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-olive">Shipments</p>
          <h1 className="mt-2 font-display text-h1 text-ink">My bookings</h1>
          <p className="text-ink-secondary">Search, filter, and follow every parcel.</p>
        </div>
        <Button to="/book-parcel">
          New booking
        </Button>
      </div>

      <Card className="p-4">
        <div className="flex flex-col gap-3 md:flex-row">
          <label className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
            <input
              type="text"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search by tracking ID, city, or name..."
              className="w-full rounded-md border border-line bg-surface py-3 pl-10 pr-4 text-sm focus:border-olive focus:outline-none focus:ring-4 focus:ring-olive/15"
            />
          </label>
          <select
            value={filterStatus}
            onChange={(event) => setFilterStatus(event.target.value)}
            className="rounded-md border border-line bg-surface px-4 py-3 text-sm focus:border-olive focus:outline-none"
          >
            <option value="all">All status</option>
            <option value="pending">Pending</option>
            <option value="confirmed">Confirmed</option>
            <option value="picked_up">Picked Up</option>
            <option value="in_transit">In Transit</option>
            <option value="out_for_delivery">Out for Delivery</option>
            <option value="delivered">Delivered</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </Card>

      {error && <ErrorState title={error} description="The page is still usable. Try searching later or book a new parcel." />}

      <Card className="overflow-hidden">
        {filteredBookings.length > 0 ? (
          <>
            <div className="hidden overflow-x-auto lg:block">
              <table className="w-full text-sm">
                <thead className="bg-muted text-left text-ink-muted">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Tracking ID</th>
                    <th className="px-6 py-3 font-semibold">From</th>
                    <th className="px-6 py-3 font-semibold">To</th>
                    <th className="px-6 py-3 font-semibold">Status</th>
                    <th className="px-6 py-3 font-semibold">Pickup</th>
                    <th className="px-6 py-3 text-right font-semibold">Price</th>
                    <th className="px-6 py-3 text-center font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredBookings.map((booking) => (
                    <tr key={booking.id} className="border-t border-line">
                      <td className="px-6 py-4 font-mono text-olive">{booking.tracking_id}</td>
                      <td className="px-6 py-4">
                        <p className="font-semibold">{booking.sender_city}</p>
                        <p className="text-xs text-ink-muted">{booking.sender_name}</p>
                      </td>
                      <td className="px-6 py-4">
                        <p className="font-semibold">{booking.receiver_city}</p>
                        <p className="text-xs text-ink-muted">{booking.receiver_name}</p>
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={booking.status} />
                      </td>
                      <td className="px-6 py-4">{formatDate(booking.pickup_date)}</td>
                      <td className="px-6 py-4 text-right font-semibold">
                        PKR {parseFloat(booking.price || 0).toLocaleString()}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex justify-center gap-2">
                          <Link
                            to={`/track-order?id=${booking.tracking_id}`}
                            className="rounded-md p-2 text-olive hover:bg-olive-light"
                            title="Track parcel"
                          >
                            <Eye className="h-4 w-4" />
                          </Link>
                          {['pending', 'confirmed'].includes(booking.status?.toLowerCase()) && (
                            <button
                              type="button"
                              onClick={() => handleDelete(booking.id)}
                              className="rounded-md p-2 text-danger hover:bg-danger-soft"
                              title="Cancel booking"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="space-y-3 p-4 lg:hidden">
              {filteredBookings.map((booking) => (
                <div key={booking.id} className="rounded-md border border-line p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="font-mono text-sm text-olive">{booking.tracking_id}</p>
                    <StatusBadge status={booking.status} />
                  </div>
                  <p className="mt-2 text-sm font-semibold text-ink">
                    {booking.sender_city} → {booking.receiver_city}
                  </p>
                  <p className="text-xs text-ink-muted">
                    {booking.sender_name} to {booking.receiver_name}
                  </p>
                  <div className="mt-3 flex items-center justify-between">
                    <p className="text-sm font-semibold">
                      PKR {parseFloat(booking.price || 0).toLocaleString()}
                    </p>
                    <div className="flex gap-2">
                      <Link
                        to={`/track-order?id=${booking.tracking_id}`}
                        className="rounded-md p-2 text-olive hover:bg-olive-light"
                      >
                        <Eye className="h-4 w-4" />
                      </Link>
                      {['pending', 'confirmed'].includes(booking.status?.toLowerCase()) && (
                        <button
                          type="button"
                          onClick={() => handleDelete(booking.id)}
                          className="rounded-md p-2 text-danger hover:bg-danger-soft"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <EmptyState
            icon={Package}
            title={searchTerm || filterStatus !== 'all' ? 'No bookings match your filters' : 'No bookings found'}
            actionLabel={!searchTerm && filterStatus === 'all' ? 'Book your first parcel' : undefined}
            to={!searchTerm && filterStatus === 'all' ? '/book-parcel' : undefined}
          />
        )}
      </Card>

      {filteredBookings.length > 0 && (
        <p className="text-center text-sm text-ink-muted">
          Showing {filteredBookings.length} of {bookings.length} bookings
        </p>
      )}
    </div>
  );
};

export default MyBookings;
