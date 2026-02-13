'use client';

import { useState } from 'react';
import { Task, TaskStatus, DifficultyLevel } from '@/lib/types';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

interface TaskModalProps {
  task: Task | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (taskId: string, updates: any) => Promise<void>;
}

const TASK_TYPE_LABELS: Record<string, string> = {
  reading: '📖 Reading',
  homework: '✏️ Homework',
  study: '🧠 Study',
  exam_prep: '📝 Exam Prep',
  project: '🚀 Project',
  review: '🔄 Review',
  break: '☕ Break',
};

export function TaskModal({ task, isOpen, onClose, onSave }: TaskModalProps) {
  const [status, setStatus] = useState<TaskStatus>(task?.status || 'pending');
  const [actualDuration, setActualDuration] = useState(task?.actual_duration_minutes || 0);
  const [difficulty, setDifficulty] = useState<DifficultyLevel | undefined>(task?.difficulty as DifficultyLevel);
  const [notes, setNotes] = useState(task?.notes || '');
  const [saving, setSaving] = useState(false);

  if (!task) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(task.id, {
        status,
        actual_duration_minutes: actualDuration || undefined,
        difficulty: difficulty || undefined,
        notes: notes || undefined,
      });
      onClose();
    } catch (error) {
      console.error('Failed to save task:', error);
    } finally {
      setSaving(false);
    }
  };

  const isCompleted = status === 'completed';

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            {TASK_TYPE_LABELS[task.type] || '📌'} {task.title}
          </DialogTitle>
          <DialogDescription>
            {task.description || 'Update task details and mark your progress'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Task Info */}
          <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm text-gray-600">📅 Date</p>
              <p className="font-semibold">
                {new Date(task.date).toLocaleDateString('en-US', { 
                  month: 'short', 
                  day: 'numeric',
                  year: 'numeric'
                })}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">⏱️ Planned Duration</p>
              <p className="font-semibold">{task.duration_minutes} minutes</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">📊 Type</p>
              <Badge variant="outline" className="mt-1">
                {task.type}
              </Badge>
            </div>
            {task.priority && (
              <div>
                <p className="text-sm text-gray-600">⭐ Priority</p>
                <p className="font-semibold">Level {task.priority}</p>
              </div>
            )}
          </div>

          {/* Status */}
          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <Select value={status} onValueChange={(v) => setStatus(v as TaskStatus)}>
              <SelectTrigger id="status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pending">⏳ Pending</SelectItem>
                <SelectItem value="in_progress">🔄 In Progress</SelectItem>
                <SelectItem value="completed">✅ Completed</SelectItem>
                <SelectItem value="skipped">⏭️ Skipped</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Actual Duration (show if completed/in progress) */}
          {(status === 'completed' || status === 'in_progress') && (
            <div className="space-y-2">
              <Label htmlFor="duration">Actual Time Spent (minutes)</Label>
              <Input
                id="duration"
                type="number"
                value={actualDuration || ''}
                onChange={(e) => setActualDuration(parseInt(e.target.value) || 0)}
                placeholder={`Planned: ${task.duration_minutes} min`}
              />
            </div>
          )}

          {/* Difficulty (show if completed) */}
          {isCompleted && (
            <div className="space-y-2">
              <Label htmlFor="difficulty">How difficult was it?</Label>
              <Select 
                value={difficulty || ''} 
                onValueChange={(v) => setDifficulty(v as DifficultyLevel)}
              >
                <SelectTrigger id="difficulty">
                  <SelectValue placeholder="Select difficulty" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="very_easy">😊 Very Easy</SelectItem>
                  <SelectItem value="easy">🙂 Easy</SelectItem>
                  <SelectItem value="moderate">😐 Moderate</SelectItem>
                  <SelectItem value="hard">😓 Hard</SelectItem>
                  <SelectItem value="very_hard">😰 Very Hard</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes</Label>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any notes about this task..."
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}