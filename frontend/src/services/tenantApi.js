import axios from 'axios';
import {
  TENANT_API_URL,
  TENANT_ORG_KEY,
  TENANT_TOKEN_KEY,
} from '../config/api';
import { getApiErrorMessage } from './errors';

const tenantApi = axios.create({
  baseURL: TENANT_API_URL,
  headers: { 'Content-Type': 'application/json' },
});

tenantApi.interceptors.request.use((config) => {
  const token = localStorage.getItem(TENANT_TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const orgId = localStorage.getItem(TENANT_ORG_KEY);
  if (orgId) {
    config.headers['X-Organization-Id'] = orgId;
  }
  if (import.meta.env.DEV) {
    const method = (config.method || 'get').toUpperCase();
    const full = `${config.baseURL || ''}${config.url || ''}`;
    console.info(`[Softorica tenantApi] ${method} ${full}`);
  }
  return config;
});

tenantApi.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      const path = window.location.pathname;
      if (path.startsWith('/app') || path === '/login' || path === '/register') {
        error.isUnauthorized = true;
      }
    }
    error.userMessage = getApiErrorMessage(error);
    return Promise.reject(error);
  }
);

export const authApi = {
  register: (payload) => tenantApi.post('/auth/register', payload),
  login: (payload) => tenantApi.post('/auth/login', payload),
  me: () => tenantApi.get('/auth/me'),
  organizations: () => tenantApi.get('/auth/organizations'),
  switchOrganization: (organization_id) =>
    tenantApi.post('/auth/switch-organization', { organization_id }),
  logout: () => tenantApi.post('/auth/logout'),
};

export const orgApi = {
  create: (payload) => tenantApi.post('/organizations', payload),
  me: () => tenantApi.get('/organizations/me'),
  updateMe: (payload) => tenantApi.patch('/organizations/me', payload),
  listMembers: (params) => tenantApi.get('/organizations/me/members', { params }),
  inviteMember: (payload) => tenantApi.post('/organizations/me/members', payload),
  updateMember: (membershipId, payload) =>
    tenantApi.patch(`/organizations/me/members/${membershipId}`, payload),
  removeMember: (membershipId) =>
    tenantApi.delete(`/organizations/me/members/${membershipId}`),
  listInvitations: (params) =>
    tenantApi.get('/organizations/me/invitations', { params }),
};

export const invitationApi = {
  accept: (token) => tenantApi.post('/invitations/accept', { token }),
};

export const shipmentApi = {
  list: (params) => tenantApi.get('/shipments', { params }),
  get: (id) => tenantApi.get(`/shipments/${id}`),
  create: (payload) => tenantApi.post('/shipments', payload),
  update: (id, payload) => tenantApi.patch(`/shipments/${id}`, payload),
  cancel: (id, payload = {}) => tenantApi.post(`/shipments/${id}/cancel`, payload),
  changeStatus: (id, payload) => tenantApi.post(`/shipments/${id}/status`, payload),
  history: (id) => tenantApi.get(`/shipments/${id}/history`),
  assignRider: (id, payload) => tenantApi.post(`/shipments/${id}/assign-rider`, payload),
  unassignRider: (id, payload = {}) =>
    tenantApi.post(`/shipments/${id}/unassign-rider`, payload),
  riderHistory: (id) => tenantApi.get(`/shipments/${id}/rider-history`),
  getPod: (id) => tenantApi.get(`/shipments/${id}/pod`),
  createPod: (id, payload) => tenantApi.post(`/shipments/${id}/pod`, payload),
};

export const customerApi = {
  list: (params) => tenantApi.get('/customers', { params }),
  get: (id) => tenantApi.get(`/customers/${id}`),
  create: (payload) => tenantApi.post('/customers', payload),
  update: (id, payload) => tenantApi.patch(`/customers/${id}`, payload),
  activate: (id) => tenantApi.post(`/customers/${id}/reactivate`),
  deactivate: (id) => tenantApi.post(`/customers/${id}/deactivate`),
  shipments: (id, params) => tenantApi.get(`/customers/${id}/shipments`, { params }),
};

export const riderApi = {
  list: (params) => tenantApi.get('/riders', { params }),
  get: (id) => tenantApi.get(`/riders/${id}`),
  create: (payload) => tenantApi.post('/riders', payload),
  update: (id, payload) => tenantApi.patch(`/riders/${id}`, payload),
  activate: (id) => tenantApi.post(`/riders/${id}/reactivate`),
  deactivate: (id) => tenantApi.post(`/riders/${id}/deactivate`),
  shipments: (id, params) => tenantApi.get(`/riders/${id}/shipments`, { params }),
};

export const podEvidenceApi = {
  list: (shipmentId) => tenantApi.get(`/shipments/${shipmentId}/pod/evidence`),
  requestUpload: (shipmentId, payload) =>
    tenantApi.post(`/shipments/${shipmentId}/pod/uploads`, payload),
  completeUpload: (shipmentId, uploadId) =>
    tenantApi.post(`/shipments/${shipmentId}/pod/uploads/${uploadId}/complete`),
  download: (shipmentId, evidenceId) =>
    tenantApi.get(`/shipments/${shipmentId}/pod/evidence/${evidenceId}/download`),
};

export const notificationApi = {
  list: (params) => tenantApi.get('/notifications', { params }),
  get: (id) => tenantApi.get(`/notifications/${id}`),
  getSettings: () => tenantApi.get('/notifications/settings'),
  updateSettings: (payload) => tenantApi.patch('/notifications/settings', payload),
};

export default tenantApi;
