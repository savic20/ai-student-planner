/**
 * API Client
 * -----------
 * Axios instance configured for backend communication.
 * 
 * FEATURES:
 * - Automatic token injection
 * - Request/response interceptors
 * - Error handling
 * - Token refresh logic
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

// Base URL - change this if backend is deployed
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token to every request
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Get token from localStorage
    const token = localStorage.getItem('access_token');
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle errors globally
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    
    // If 401 and we haven't retried yet, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem('refresh_token');
      
      if (refreshToken) {
        try {
          // Try to refresh the access token
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          const { access_token } = response.data;
          localStorage.setItem('access_token', access_token);
          
          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
          }
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed - logout user
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }
    
    return Promise.reject(error);
  }
);

// =============================================================================
// AUTH API
// =============================================================================

export const authAPI = {
  /**
   * Sign up a new user
   */
  signup: async (email: string, password: string, full_name: string) => {
    const response = await api.post('/auth/signup', {
      email,
      password,
      full_name,
    });
    return response.data;
  },

  /**
   * Login user
   */
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', {
      email,
      password,
    });
    
    // Store tokens
    const { access_token, refresh_token } = response.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    
    return response.data;
  },

  /**
   * Logout user
   */
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  /**
   * Get current user
   */
  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

// =============================================================================
// SYLLABUS API
// =============================================================================

export const syllabusAPI = {
  /**
   * Upload and parse syllabus
   */
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/syllabus/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Get all syllabi
   */
  getAll: async () => {
    const response = await api.get('/syllabus/');
    return response.data;
  },

  /**
   * Get specific syllabus
   */
  getById: async (id: number) => {
    const response = await api.get(`/syllabus/${id}`);
    return response.data;
  },

  /**
   * Delete syllabus
   */
  delete: async (id: number) => {
    const response = await api.delete(`/syllabus/${id}`);
    return response.data;
  },
};

// =============================================================================
// PLANS API
// =============================================================================

export const plansAPI = {
  /**
   * Generate new plan
   */
  generate: async (syllabusId: number, preferences: any) => {
    const response = await api.post('/plans/generate', {
      syllabus_id: syllabusId,
      ...preferences,
    });
    return response.data;
  },

  /**
   * Get all plans
   */
  getAll: async () => {
    const response = await api.get('/plans/');
    return response.data;
  },

  /**
   * Get specific plan
   */
  getById: async (id: number) => {
    const response = await api.get(`/plans/${id}`);
    return response.data;
  },

  /**
   * Get plan progress
   */
  getProgress: async (id: number) => {
    const response = await api.get(`/plans/${id}/progress`);
    return response.data;
  },

  /**
   * Update task status
   */
  updateTask: async (planId: number, taskId: string, data: any) => {
    const response = await api.put(`/plans/${planId}/tasks/${taskId}`, data);
    return response.data;
  },

  /**
   * Delete plan
   */
  delete: async (id: number) => {
    const response = await api.delete(`/plans/${id}`);
    return response.data;
  },
};

// =============================================================================
// FEEDBACK API
// =============================================================================

export const feedbackAPI = {
  /**
   * Submit feedback
   */
  submit: async (data: any) => {
    const response = await api.post('/feedback/submit', data);
    return response.data;
  },

  /**
   * Get plan feedback
   */
  getByPlan: async (planId: number) => {
    const response = await api.get(`/feedback/plan/${planId}`);
    return response.data;
  },

  /**
   * Get statistics
   */
  getStats: async (planId: number) => {
    const response = await api.get(`/feedback/plan/${planId}/stats`);
    return response.data;
  },
};

export default api;