import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoadingState from './ui/LoadingState';

/** Protects Modules 1–11 SaaS routes under /app. */
const TenantProtectedRoute = () => {
  const { isAuthenticated, loading, currentOrganizationId, organizations } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingState label="Checking authentication..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  const needsOrg =
    !currentOrganizationId &&
    location.pathname !== '/app/onboarding' &&
    (organizations?.length || 0) === 0;

  if (needsOrg) {
    return <Navigate to="/app/onboarding" replace />;
  }

  if (
    !currentOrganizationId &&
    (organizations?.length || 0) > 0 &&
    location.pathname !== '/app/onboarding'
  ) {
    return <Navigate to="/app/onboarding" replace />;
  }

  return <Outlet />;
};

export default TenantProtectedRoute;
