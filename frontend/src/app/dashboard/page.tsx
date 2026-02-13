'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore, usePlanStore } from '@/lib/store';
import { plansAPI, syllabusAPI } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Task } from '@/lib/types';
import { TaskModal } from '@/components/TaskModal';

// Task type colors (playful palette)
const TASK_COLORS = {
  reading: 'bg-purple-100 text-purple-700 border-purple-200',
  homework: 'bg-blue-100 text-blue-700 border-blue-200',
  study: 'bg-green-100 text-green-700 border-green-200',
  exam_prep: 'bg-red-100 text-red-700 border-red-200',
  project: 'bg-orange-100 text-orange-700 border-orange-200',
  review: 'bg-pink-100 text-pink-700 border-pink-200',
  break: 'bg-gray-100 text-gray-700 border-gray-200',
};

const TASK_EMOJIS = {
  reading: '📖',
  homework: '✏️',
  study: '🧠',
  exam_prep: '📝',
  project: '🚀',
  review: '🔄',
  break: '☕',
};

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, user, logout } = useAuthStore();
  const { currentPlan, setCurrentPlan, setPlans, setSyllabi, updateTask } = usePlanStore();
  
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState<any>(null);
  const [updatingTask, setUpdatingTask] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    
    if (!isAuthenticated && !token) {
      router.push('/login');
      return;
    }

    const fetchData = async () => {
      try {
        const [plansRes, syllabiRes] = await Promise.all([
          plansAPI.getAll(),
          syllabusAPI.getAll(),
        ]);
        
        setPlans(plansRes.plans || []);
        setSyllabi(syllabiRes.syllabi || []);
        
        if (plansRes.plans?.[0]) {
          setCurrentPlan(plansRes.plans[0]);
          const prog = await plansAPI.getProgress(plansRes.plans[0].plan_id);
          setProgress(prog);
        }
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [isAuthenticated]);

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleTaskSave = async (taskId: string, updates: any) => {
    if (!currentPlan) return;
    
    setUpdatingTask(taskId);
    
    try {
      // Optimistic update
      updateTask(taskId, updates);
      
      // API update
      await plansAPI.updateTask(currentPlan.plan_id, taskId, updates);
      
      // Refresh progress
      const prog = await plansAPI.getProgress(currentPlan.plan_id);
      setProgress(prog);
    } catch (error) {
      console.error('Failed to update task:', error);
      // Could revert on error
    } finally {
      setUpdatingTask(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-purple-200 border-t-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 font-medium">Loading your plans... ✨</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 backdrop-blur-sm bg-white/90">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
              AI Study Planner 🎓
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <Button 
              variant="outline" 
              onClick={() => router.push('/upload')}
              className="gap-2"
            >
              📤 Upload Syllabus
            </Button>
            <Button variant="outline" onClick={logout} size="sm">
              Logout
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900">
            Hey there, {user?.full_name}! 👋
          </h2>
          <p className="text-gray-600 mt-1">Ready to crush your study goals?</p>
        </div>

        {/* Stats Cards */}
        <div className="grid gap-6 md:grid-cols-3 mb-8">
          <Card className="border-2 border-purple-200 bg-gradient-to-br from-purple-50 to-white hover:shadow-lg transition-shadow">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">📚 Total Tasks</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-purple-600">{progress?.total_tasks || 0}</div>
            </CardContent>
          </Card>

          <Card className="border-2 border-green-200 bg-gradient-to-br from-green-50 to-white hover:shadow-lg transition-shadow">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">✅ Completed</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-green-600">{progress?.completed_tasks || 0}</div>
              <p className="text-xs text-gray-500 mt-1">
                {progress?.pending_tasks || 0} remaining
              </p>
            </CardContent>
          </Card>

          <Card className="border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-white hover:shadow-lg transition-shadow">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">🎯 Progress</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-blue-600">{Math.round(progress?.progress_percentage || 0)}%</div>
              <Progress 
                value={progress?.progress_percentage || 0} 
                className="mt-3 h-2"
              />
            </CardContent>
          </Card>
        </div>

        {/* Study Plan */}
        {currentPlan ? (
          <Card className="border-2 border-gray-200 shadow-xl">
            <CardHeader className="bg-gradient-to-r from-purple-100 to-blue-100 border-b">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xl">{currentPlan.title}</CardTitle>
                  <p className="text-sm text-gray-600 mt-1">{currentPlan.description}</p>
                </div>
                <Badge className="bg-purple-600 text-white px-4 py-2">
                  {currentPlan.plan_data.weeks.length} Weeks
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-8">
                {currentPlan.plan_data.weeks.slice(0, 4).map((week) => (
                  <div key={week.week_number}>
                    {/* Week Header */}
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold">
                        W{week.week_number}
                      </div>
                      <div>
                        <h3 className="font-bold text-lg">Week {week.week_number}</h3>
                        <p className="text-sm text-gray-500">
                          {new Date(week.start_date).toLocaleDateString()} - {new Date(week.end_date).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    {/* Tasks */}
                    <div className="space-y-3 ml-6 pl-6 border-l-4 border-gray-200">
                      {week.tasks.map((task) => {
                        const colorClass = TASK_COLORS[task.type] || TASK_COLORS.study;
                        const emoji = TASK_EMOJIS[task.type] || '📌';
                        const isCompleted = task.status === 'completed';
                        
                        return (
                          <div
                            key={task.id}
                            onClick={() => handleTaskClick(task)}
                            className={`
                              group p-4 rounded-xl border-2 cursor-pointer transition-all
                              ${isCompleted 
                                ? 'bg-gray-50 border-gray-300 opacity-75' 
                                : `${colorClass} hover:shadow-md hover:scale-[1.02]`
                              }
                              ${updatingTask === task.id ? 'animate-pulse' : ''}
                            `}
                          >
                            <div className="flex items-start gap-3">
                              {/* Checkbox */}
                              <div className={`
                                w-6 h-6 rounded-full border-2 flex items-center justify-center mt-0.5
                                ${isCompleted 
                                  ? 'bg-green-500 border-green-500' 
                                  : 'border-gray-400 group-hover:border-gray-600'
                                }
                              `}>
                                {isCompleted && (
                                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                  </svg>
                                )}
                              </div>

                              {/* Task Content */}
                              <div className="flex-1">
                                <div className="flex items-start justify-between gap-2">
                                  <div>
                                    <p className={`font-semibold ${isCompleted ? 'line-through text-gray-500' : ''}`}>
                                      {emoji} {task.title}
                                    </p>
                                    <div className="flex items-center gap-3 mt-2 text-sm">
                                      <span className="text-gray-600">
                                        🕐 {task.duration_minutes} min
                                      </span>
                                      <span className="text-gray-600">
                                        📅 {new Date(task.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                      </span>
                                      {task.priority && (
                                        <Badge variant="outline" className="text-xs">
                                          Priority {task.priority}
                                        </Badge>
                                      )}
                                    </div>
                                  </div>
                                  
                                  <Badge 
                                    variant={isCompleted ? "default" : "secondary"}
                                    className={isCompleted ? 'bg-green-500' : ''}
                                  >
                                    {task.status}
                                  </Badge>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="border-2 border-dashed border-gray-300 bg-white">
            <CardContent className="py-16 text-center">
              <div className="text-6xl mb-4">📚</div>
              <h3 className="text-2xl font-bold mb-2">No Study Plan Yet</h3>
              <p className="text-gray-600 mb-6">Upload your syllabus to get started with AI-powered planning!</p>
              <Button 
                size="lg"
                className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                onClick={() => router.push('/upload')}
              >
                📤 Upload Syllabus
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Task Details Modal */}
      <TaskModal
        task={selectedTask}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleTaskSave}
      />
    </div>
  );
}