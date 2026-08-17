import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import {
  API_URL,
  TENANT_ORG_KEY,
  TENANT_TOKEN_KEY,
  TENANT_USER_KEY,
  TOKEN_KEY,
  USER_KEY,
} from '../config/api';
import { getApiErrorMessage, getValidationDetails } from '../services/errors';
import { authApi, orgApi } from '../services/tenantApi';
import { permissionsForRole, roleFromMemberships } from '../utils/rbac';

const AuthContext = createContext(null);

function displayName(user) {
  if (!user) return '';
  if (user.name) return user.name;
  const parts = [user.first_name, user.last_name].filter(Boolean);
  return parts.join(' ') || user.email || '';
}

function persistTenantSession({ token, user, organizationId }) {
  if (token) localStorage.setItem(TENANT_TOKEN_KEY, token);
  if (user) localStorage.setItem(TENANT_USER_KEY, JSON.stringify(user));
  if (organizationId) localStorage.setItem(TENANT_ORG_KEY, organizationId);
  else if (organizationId === null) localStorage.removeItem(TENANT_ORG_KEY);
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [memberships, setMemberships] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [organization, setOrganization] = useState(null);
  const [currentOrganizationId, setCurrentOrganizationId] = useState(
    () => localStorage.getItem(TENANT_ORG_KEY)
  );
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    localStorage.removeItem(TENANT_TOKEN_KEY);
    localStorage.removeItem(TENANT_USER_KEY);
    localStorage.removeItem(TENANT_ORG_KEY);
    setUser(null);
    setMemberships([]);
    setOrganizations([]);
    setOrganization(null);
    setCurrentOrganizationId(null);
    setIsAuthenticated(false);
  }, []);

  const hydrateFromMe = useCallback(async (token) => {
    const meRes = await authApi.me();
    const me = meRes.data;
    const nextUser = {
      ...me.user,
      name: displayName(me.user),
    };
    let orgId = me.current_organization_id || localStorage.getItem(TENANT_ORG_KEY);
    const active = (me.memberships || []).filter((m) => m.status === 'ACTIVE');
    if (!orgId && active.length === 1) {
      orgId = active[0].organization_id;
    }
    if (orgId) localStorage.setItem(TENANT_ORG_KEY, String(orgId));
    persistTenantSession({ token, user: nextUser, organizationId: orgId || null });

    setUser(nextUser);
    setMemberships(me.memberships || []);
    setCurrentOrganizationId(orgId ? String(orgId) : null);
    setIsAuthenticated(true);

    try {
      const orgsRes = await authApi.organizations();
      setOrganizations(orgsRes.data || []);
    } catch (err) {
      if (err?.response?.status === 404) {
        console.warn(
          '[ORVIA] /auth/organizations returned 404. Restart the tenant API so Modules 1–11 routes are loaded.'
        );
      }
      setOrganizations([]);
    }

    if (orgId) {
      try {
        const orgRes = await orgApi.me();
        setOrganization(orgRes.data);
      } catch {
        setOrganization(null);
      }
    } else {
      setOrganization(null);
    }

    return { user: nextUser, organizationId: orgId, memberships: me.memberships || [] };
  }, []);

  useEffect(() => {
    const boot = async () => {
      try {
        const token = localStorage.getItem(TENANT_TOKEN_KEY);
        const storedUser = localStorage.getItem(TENANT_USER_KEY);
        if (!token) return;
        if (storedUser && storedUser !== 'undefined') {
          try {
            setUser(JSON.parse(storedUser));
            setIsAuthenticated(true);
          } catch {
            /* ignore corrupt cache */
          }
        }
        await hydrateFromMe(token);
      } catch (error) {
        if (error?.response?.status === 401 || error?.isUnauthorized) {
          clearSession();
        } else if (error?.message === 'Network Error' || error?.code === 'ERR_NETWORK') {
          // Keep cached Softorica identity for UX, but do not treat session as verified.
          setIsAuthenticated(Boolean(localStorage.getItem(TENANT_TOKEN_KEY)));
          console.warn('[ORVIA] Unable to connect to the ORVIA API during session restore.');
        } else if (error?.response?.status >= 500) {
          // Keep token; user can retry. Do not wipe org on transient API failure.
          console.warn('[ORVIA] Session restore failed:', getApiErrorMessage(error));
        } else if (!error?.response) {
          console.warn('[ORVIA] Session restore failed without response.');
        } else {
          // Unexpected client/auth payload failure — clear to avoid stale "signed in" UI.
          clearSession();
        }
      } finally {
        setLoading(false);
      }
    };
    boot();
  }, [clearSession, hydrateFromMe]);

  const register = async (userData) => {
    try {
      const name = String(userData.name || '').trim();
      const [first_name, ...rest] = name.split(/\s+/);
      const last_name = rest.join(' ') || first_name || 'User';
      await authApi.register({
        email: userData.email,
        password: userData.password,
        first_name: userData.first_name || first_name,
        last_name: userData.last_name || last_name,
        phone: userData.phone || null,
      });
      return login({ email: userData.email, password: userData.password });
    } catch (error) {
      const message = getApiErrorMessage(error, 'Registration failed');
      const fields = getValidationDetails(error);
      toast.error(message);
      return { success: false, message, fields };
    }
  };

  const login = async (credentials) => {
    try {
      const response = await authApi.login({
        email: credentials.email,
        password: credentials.password,
      });
      const token = response.data?.access_token;
      if (!token) throw new Error('Incomplete login response');
      persistTenantSession({ token, user: null, organizationId: undefined });
      const session = await hydrateFromMe(token);
      toast.success('Signed in successfully');
      return { success: true, user: session.user, organizationId: session.organizationId };
    } catch (error) {
      const status = error?.response?.status;
      let message = getApiErrorMessage(error, 'Login failed');
      if (status === 429) {
        const retryAfter = error?.response?.headers?.['retry-after'];
        message = retryAfter
          ? `Too many login attempts. Please try again in ${retryAfter} seconds.`
          : 'Too many login attempts. Please try again later.';
      }
      toast.error(message);
      return { success: false, message, status, retryAfter: error?.response?.headers?.['retry-after'] };
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      /* logout is stateless on the server */
    }
    clearSession();
    toast.info('Signed out');
  };

  const createOrganization = async ({ name, slug }) => {
    const response = await orgApi.create({ name, slug });
    const org = response.data;
    localStorage.setItem(TENANT_ORG_KEY, String(org.id));
    setCurrentOrganizationId(String(org.id));

    try {
      const switched = await authApi.switchOrganization(org.id);
      const token = switched.data?.access_token;
      if (token) {
        persistTenantSession({ token, user, organizationId: org.id });
        await hydrateFromMe(token);
      } else {
        await hydrateFromMe(localStorage.getItem(TENANT_TOKEN_KEY));
      }
    } catch (err) {
      // Org create succeeded; single-membership tenants can continue without a new JWT claim.
      console.warn('[Softorica] switch-organization failed after create; hydrating membership.', err?.userMessage);
      await hydrateFromMe(localStorage.getItem(TENANT_TOKEN_KEY));
    }
    toast.success('Organization created');
    return org;
  };

  const switchOrganization = async (organizationId) => {
    const switched = await authApi.switchOrganization(organizationId);
    const token = switched.data?.access_token;
    if (!token) throw new Error('Switch failed');
    persistTenantSession({ token, user, organizationId });
    await hydrateFromMe(token);
    toast.success('Organization switched');
  };

  const refreshSession = async () => {
    const token = localStorage.getItem(TENANT_TOKEN_KEY);
    if (!token) return;
    await hydrateFromMe(token);
  };

  /** Legacy goburq.com profile update — uses goburq_* keys only. */
  const updateProfile = async (updatedData) => {
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      if (!token) {
        toast.error('Please sign in again');
        return;
      }
      const response = await axios.put(`${API_URL}/auth/profile`, updatedData, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const updatedUser = response.data?.data?.user || response.data?.user;
      if (!updatedUser) {
        toast.error('Profile update failed');
        return;
      }
      localStorage.setItem(USER_KEY, JSON.stringify(updatedUser));
      toast.success('Profile updated successfully!');
    } catch (error) {
      toast.error(error.response?.data?.message || 'Profile update failed');
    }
  };

  const updateUser = (updatedUser) => {
    if (!updatedUser) return;
    setUser(updatedUser);
    localStorage.setItem(TENANT_USER_KEY, JSON.stringify(updatedUser));
  };

  const role = roleFromMemberships(memberships, currentOrganizationId);
  const permissions = useMemo(() => permissionsForRole(role), [role]);

  const value = {
    user,
    memberships,
    organizations,
    organization,
    currentOrganizationId,
    role,
    permissions,
    isAuthenticated,
    loading,
    register,
    login,
    logout,
    createOrganization,
    switchOrganization,
    refreshSession,
    updateUser,
    updateProfile,
    clearSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

export default AuthContext;
