import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { TOKEN_KEY, USER_KEY } from '../config/api';

/**
 * Protects legacy GoBurq portal routes (/book-parcel, /user/*).
 * Uses goburq_token / goburq_user — independent from Softorica SaaS session.
 */
const ProtectedRoute = () => {
  const location = useLocation();
  const token = localStorage.getItem(TOKEN_KEY);
  let hasUser = false;
  try {
    const raw = localStorage.getItem(USER_KEY);
    hasUser = Boolean(raw && raw !== 'undefined' && JSON.parse(raw));
  } catch {
    hasUser = false;
  }

  if (!token || !hasUser) {
    // Legacy portal sign-in historically shared /login; Softorica login no longer
    // writes goburq_token. Send users to public home with a clear path to track/book.
    return <Navigate to="/" replace state={{ from: location, legacyAuthRequired: true }} />;
  }

  return <Outlet />;
};

export default ProtectedRoute;
