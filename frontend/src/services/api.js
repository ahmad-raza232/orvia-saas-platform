// frontend/src/services/api.js
import axios from 'axios';

import { API_URL } from '../config/api';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Contact service
export const contactService = {
  submitContactForm: async (formData) => {
    const response = await api.post('/contact', formData);
    return response.data;
  },
};

// ==================== PLAN SERVICES ====================
export const planService = {
  getAllPlans: async (activeOnly = true) => {
    const response = await api.get('/plans', { 
      params: { active_only: activeOnly } 
    });
    return response.data;
  },

  getPlanById: async (id) => {
    const response = await api.get(`/plans/${id}`);
    return response.data;
  },

  createPlan: async (planData) => {
    const response = await api.post('/plans', planData);
    return response.data;
  },

  updatePlan: async (id, planData) => {
    const response = await api.put(`/plans/${id}`, planData);
    return response.data;
  },

  deletePlan: async (id) => {
    const response = await api.delete(`/plans/${id}`);
    return response.data;
  },

  calculatePrice: async (priceData) => {
    const response = await api.post('/plans/calculate-price', priceData);
    return response.data;
  }
};



