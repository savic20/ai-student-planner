/**
 * Global State Store
 * ------------------
 * Zustand store for app-wide state management.
 * 
 * STORES:
 * - Auth state (user, tokens)
 * - Current plan
 * - UI state (loading, errors)
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, Plan, Syllabus } from './types';

// =============================================================================
// AUTH STORE
// =============================================================================

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      
      setUser: (user) => set({ 
        user, 
        isAuthenticated: !!user 
      }),
      
      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({ user: null, isAuthenticated: false });
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);

// =============================================================================
// PLAN STORE
// =============================================================================

interface PlanState {
  currentPlan: Plan | null;
  plans: Plan[];
  syllabi: Syllabus[];
  
  setCurrentPlan: (plan: Plan | null) => void;
  setPlans: (plans: Plan[]) => void;
  setSyllabi: (syllabi: Syllabus[]) => void;
  
  // Add plan to list
  addPlan: (plan: Plan) => void;
  
  // Update task in current plan
  updateTask: (taskId: string, updates: any) => void;
}

export const usePlanStore = create<PlanState>((set) => ({
  currentPlan: null,
  plans: [],
  syllabi: [],
  
  setCurrentPlan: (plan) => set({ currentPlan: plan }),
  
  setPlans: (plans) => set({ plans }),
  
  setSyllabi: (syllabi) => set({ syllabi }),
  
  addPlan: (plan) => set((state) => ({
    plans: [plan, ...state.plans],
  })),
  
  updateTask: (taskId, updates) => set((state) => {
    if (!state.currentPlan) return state;
    
    const updatedPlan = { ...state.currentPlan };
    const planData = { ...updatedPlan.plan_data };
    
    // Find and update task
    planData.weeks = planData.weeks.map((week) => ({
      ...week,
      tasks: week.tasks.map((task) =>
        task.id === taskId ? { ...task, ...updates } : task
      ),
    }));
    
    updatedPlan.plan_data = planData;
    
    return { currentPlan: updatedPlan };
  }),
}));

// =============================================================================
// UI STORE
// =============================================================================

interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'light',
      
      toggleSidebar: () => set((state) => ({ 
        sidebarOpen: !state.sidebarOpen 
      })),
      
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'ui-storage',
    }
  )
);