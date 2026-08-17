import { Routes, Route, Link } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import MarketingLayout from './components/layout/MarketingLayout';
import DashboardLayout from './components/layout/DashboardLayout';
import AppShell from './components/layout/AppShell';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import BookParcel from './pages/BookParcel';
import TrackOrder from './pages/TrackOrder';
import UserDashboard from './pages/UserDashboard';
import MyBookings from './pages/MyBookings';
import Profile from './pages/Profile';
import ProtectedRoute from './components/ProtectedRoute';
import TenantProtectedRoute from './components/TenantProtectedRoute';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import DashboardPage from './pages/app/DashboardPage';
import OnboardingPage from './pages/app/OnboardingPage';
import ShipmentsPage from './pages/app/ShipmentsPage';
import ShipmentDetailPage from './pages/app/ShipmentDetailPage';
import ShipmentCreatePage from './pages/app/ShipmentCreatePage';
import ShipmentSuccessPage from './pages/app/ShipmentSuccessPage';
import CustomersPage from './pages/app/CustomersPage';
import CustomerDetailPage from './pages/app/CustomerDetailPage';
import RidersPage from './pages/app/RidersPage';
import RiderDetailPage from './pages/app/RiderDetailPage';
import NotificationsPage from './pages/app/NotificationsPage';
import OrganizationPage from './pages/app/OrganizationPage';

const NotFound = () => (
  <div className="flex min-h-[50vh] flex-col items-center justify-center px-4 py-16 text-center">
    <h1 className="font-display text-3xl text-ink">Page not found</h1>
    <p className="mt-2 text-sm text-ink-secondary">This page does not exist.</p>
    <Link to="/" className="mt-6 font-semibold text-olive hover:underline">
      Go home
    </Link>
  </div>
);

function App() {
  return (
    <div className="min-h-screen bg-canvas">
      <Routes>
        <Route element={<MarketingLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/track" element={<TrackOrder />} />
          <Route path="/tracking" element={<TrackOrder />} />
          <Route path="/track-order" element={<TrackOrder />} />
        </Route>

        <Route element={<TenantProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/app" element={<DashboardPage />} />
            <Route path="/app/dashboard" element={<DashboardPage />} />
            <Route path="/app/onboarding" element={<OnboardingPage />} />
            <Route path="/app/shipments" element={<ShipmentsPage />} />
            <Route path="/app/shipments/new" element={<ShipmentCreatePage />} />
            <Route path="/app/shipments/:id/receipt" element={<ShipmentSuccessPage />} />
            <Route path="/app/shipments/:id" element={<ShipmentDetailPage />} />
            <Route path="/app/customers" element={<CustomersPage />} />
            <Route path="/app/customers/:id" element={<CustomerDetailPage />} />
            <Route path="/app/riders" element={<RidersPage />} />
            <Route path="/app/riders/:id" element={<RiderDetailPage />} />
            <Route path="/app/notifications" element={<NotificationsPage />} />
            <Route path="/app/organization" element={<OrganizationPage />} />
          </Route>
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<DashboardLayout />}>
            <Route path="/book-parcel" element={<BookParcel />} />
            <Route path="/user/dashboard" element={<UserDashboard />} />
            <Route path="/user/bookings" element={<MyBookings />} />
            <Route path="/user/profile" element={<Profile />} />
          </Route>
        </Route>

        <Route element={<MarketingLayout />}>
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>

      <ToastContainer position="top-right" autoClose={2500} theme="light" />
    </div>
  );
}

export default App;
