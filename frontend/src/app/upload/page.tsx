'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore, usePlanStore } from '@/lib/store';
import { syllabusAPI, plansAPI } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';

const DAYS_OF_WEEK = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

export default function UploadPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const { addPlan, setSyllabi } = usePlanStore();
  
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [syllabusId, setSyllabusId] = useState<number | null>(null);
  const [parsedData, setParsedData] = useState<any>(null);
  const [error, setError] = useState('');
  
  // Plan preferences
  const [studyHours, setStudyHours] = useState(3);
  const [selectedDays, setSelectedDays] = useState(['monday', 'tuesday', 'wednesday', 'thursday', 'friday']);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setUploading(true);
    setParsing(true);
    setError('');
    
    try {
      const response = await syllabusAPI.upload(file);
      setSyllabusId(response.syllabus_id);
      setParsedData(response.parsed_data);
      
      // Refresh syllabi list
      const syllabiRes = await syllabusAPI.getAll();
      setSyllabi(syllabiRes.syllabi || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
      setParsing(false);
    }
  };

  const handleGeneratePlan = async () => {
    if (!syllabusId) return;
    
    setGenerating(true);
    setError('');
    
    try {
      const plan = await plansAPI.generate(syllabusId, {
        study_hours_per_day: studyHours,
        study_days: selectedDays,
      });
      
      addPlan(plan);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Plan generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const toggleDay = (day: string) => {
    setSelectedDays(prev => 
      prev.includes(day) 
        ? prev.filter(d => d !== day)
        : [...prev, day]
    );
  };

  if (!isAuthenticated) {
    router.push('/login');
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <Button variant="ghost" onClick={() => router.push('/dashboard')}>
            ← Back to Dashboard
          </Button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
            Upload Your Syllabus 📚
          </h1>
          <p className="text-gray-600 mt-2">
            Let AI analyze your course and create a personalized study plan
          </p>
        </div>

        {/* Step 1: Upload */}
        <Card className="mb-6 border-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span className="w-8 h-8 rounded-full bg-purple-600 text-white flex items-center justify-center text-sm font-bold">1</span>
              Upload Syllabus
            </CardTitle>
            <CardDescription>Upload your course syllabus (PDF or DOCX)</CardDescription>
          </CardHeader>
          <CardContent>
            {!file ? (
              <div
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-purple-400 transition-colors"
              >
                <div className="text-6xl mb-4">📄</div>
                <p className="text-lg font-semibold mb-2">Drop your syllabus here</p>
                <p className="text-gray-500 mb-4">or click to browse</p>
                
                <input
                  type="file"
                  accept=".pdf,.docx"
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-upload"
                />
                
                <Button 
                  type="button"
                  onClick={() => document.getElementById('file-upload')?.click()}
                >
                  Choose File
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border-2 border-purple-200">
                  <div className="flex items-center gap-3">
                    <div className="text-3xl">📄</div>
                    <div>
                      <p className="font-semibold">{file.name}</p>
                      <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => setFile(null)}>
                    Remove
                  </Button>
                </div>
                
                <Button 
                  onClick={handleUpload} 
                  disabled={uploading}
                  className="w-full bg-gradient-to-r from-purple-600 to-blue-600"
                  size="lg"
                >
                  {uploading ? 'Uploading & Analyzing...' : 'Upload & Parse 🚀'}
                </Button>
                
                {parsing && (
                  <div className="text-center py-4">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto mb-2"></div>
                    <p className="text-sm text-gray-600">AI is reading your syllabus... 🤖</p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Step 2: Parsed Data Preview */}
        {parsedData && (
          <Card className="mb-6 border-2 border-green-200 bg-gradient-to-br from-green-50 to-white">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="w-8 h-8 rounded-full bg-green-600 text-white flex items-center justify-center text-sm font-bold">✓</span>
                Syllabus Analyzed!
              </CardTitle>
              <CardDescription>Here's what we found</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">📚 Course</p>
                  <p className="font-semibold">{parsedData.course_name || 'Unknown Course'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">👨‍🏫 Instructor</p>
                  <p className="font-semibold">{parsedData.instructor || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">✏️ Assignments</p>
                  <p className="font-semibold">{parsedData.assignments?.length || 0} found</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">📝 Exams</p>
                  <p className="font-semibold">{parsedData.exams?.length || 0} found</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Preferences */}
        {syllabusId && (
          <Card className="mb-6 border-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold">2</span>
                Set Your Preferences
              </CardTitle>
              <CardDescription>Customize your study schedule</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Study Hours */}
              <div className="space-y-3">
                <Label htmlFor="hours">Study Hours Per Day: {studyHours}h</Label>
                <Input
                  id="hours"
                  type="range"
                  min="1"
                  max="8"
                  value={studyHours}
                  onChange={(e) => setStudyHours(parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>1h (Light)</span>
                  <span>4h (Balanced)</span>
                  <span>8h (Intensive)</span>
                </div>
              </div>

              {/* Study Days */}
              <div className="space-y-3">
                <Label>Study Days</Label>
                <div className="grid grid-cols-4 md:grid-cols-7 gap-2">
                  {DAYS_OF_WEEK.map(day => (
                    <button
                      key={day}
                      onClick={() => toggleDay(day)}
                      className={`
                        p-3 rounded-lg border-2 font-semibold capitalize text-sm transition-all
                        ${selectedDays.includes(day)
                          ? 'bg-purple-600 text-white border-purple-600'
                          : 'bg-white text-gray-600 border-gray-300 hover:border-purple-300'
                        }
                      `}
                    >
                      {day.slice(0, 3)}
                    </button>
                  ))}
                </div>
                <p className="text-sm text-gray-500">
                  {selectedDays.length} days selected
                </p>
              </div>

              {/* Generate Button */}
              <Button
                onClick={handleGeneratePlan}
                disabled={generating || selectedDays.length === 0}
                className="w-full bg-gradient-to-r from-purple-600 to-blue-600"
                size="lg"
              >
                {generating ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    AI is creating your plan...
                  </>
                ) : (
                  '✨ Generate Study Plan'
                )}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Error Display */}
        {error && (
          <Card className="border-2 border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <p className="text-red-700">{error}</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}