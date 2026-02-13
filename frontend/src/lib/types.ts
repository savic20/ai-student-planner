/**
 * TypeScript Types
 * -----------------
 * Type definitions matching backend models.
 */

// =============================================================================
// USER TYPES
// =============================================================================

export interface User {
  id: number;
  email: string;
  full_name: string;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

// =============================================================================
// SYLLABUS TYPES
// =============================================================================

export interface Assignment {
  name: string;
  due_date: string | null;
  weight: number | null;
  type: string | null;
  description: string | null;
}

export interface Exam {
  name: string;
  date: string | null;
  weight: number | null;
  type: string | null;
  topics: string[];
}

export interface ImportantDate {
  date: string;
  event: string;
  type: string | null;
}

export interface ParsedSyllabusData {
  course_name: string | null;
  course_code: string | null;
  instructor: string | null;
  semester: string | null;
  assignments: Assignment[];
  exams: Exam[];
  important_dates: ImportantDate[];
  office_hours: string | null;
  textbook: string | null;
  grading_policy: string | null;
}

export interface Syllabus {
  syllabus_id: number;
  filename: string;
  is_processed: boolean;
  parsed_data: ParsedSyllabusData | null;
  raw_text: string | null;
  processing_error: string | null;
  created_at: string;
}

// =============================================================================
// PLAN TYPES
// =============================================================================

export type TaskType = 
  | 'reading' 
  | 'homework' 
  | 'study' 
  | 'exam_prep' 
  | 'project' 
  | 'review' 
  | 'break';

export type TaskStatus = 
  | 'pending' 
  | 'in_progress' 
  | 'completed' 
  | 'skipped';

export interface Task {
  id: string;
  title: string;
  description: string | null;
  date: string;
  duration_minutes: number;
  type: TaskType;
  status: TaskStatus;
  priority: number | null;
  related_assignment_id: number | null;
  actual_duration_minutes?: number;
  difficulty?: string;
  notes?: string;
}

export interface WeekPlan {
  week_number: number;
  start_date: string;
  end_date: string;
  tasks: Task[];
  notes: string | null;
}

export interface StudyPlan {
  title: string;
  description: string | null;
  weeks: WeekPlan[];
  total_study_hours: number | null;
  preferences: Record<string, any>;
  metadata: Record<string, any>;
}

export interface Plan {
  plan_id: number;
  title: string;
  description: string | null;
  status: string;
  plan_data: StudyPlan;
  created_at: string;
  updated_at: string | null;
  version_number: number;
}

export interface PlanProgress {
  total_tasks: number;
  completed_tasks: number;
  pending_tasks: number;
  progress_percentage: number;
  total_hours_planned: number;
  total_hours_actual: number;
}

// =============================================================================
// FEEDBACK TYPES
// =============================================================================

export type DifficultyLevel = 
  | 'very_easy' 
  | 'easy' 
  | 'moderate' 
  | 'hard' 
  | 'very_hard';

export interface FeedbackSubmission {
  plan_id: number;
  week_number: number;
  difficulty: DifficultyLevel;
  tasks_completed: number;
  tasks_total: number;
  challenges?: string;
  what_worked?: string;
  suggested_changes?: string;
  extra_notes?: string;
}

export interface ReflectionInsight {
  observation: string;
  recommendation: string;
  adjustment_type: string;
  confidence: number;
}

export interface ReflectionAnalysis {
  summary: string;
  insights: ReflectionInsight[];
  overall_adjustment: string;
  adjustments: Record<string, any>;
  patterns: string[];
}

export interface Feedback {
  feedback_id: number;
  plan_id: number;
  week_number: number;
  difficulty: DifficultyLevel;
  analysis: ReflectionAnalysis | null;
  created_at: string;
  message: string;
}

export interface FeedbackStats {
  total_weeks: number;
  avg_completion_rate: number;
  avg_difficulty: string | null;
  improvement_trend: string | null;
}

// =============================================================================
// FORM TYPES
// =============================================================================

export interface LoginForm {
  email: string;
  password: string;
}

export interface SignupForm {
  email: string;
  password: string;
  full_name: string;
}

export interface PlanGenerationForm {
  syllabus_id: number;
  study_hours_per_day: number;
  study_days: string[];
}

export interface TaskUpdateForm {
  status?: TaskStatus;
  actual_duration_minutes?: number;
  difficulty?: DifficultyLevel;
  notes?: string;
}
