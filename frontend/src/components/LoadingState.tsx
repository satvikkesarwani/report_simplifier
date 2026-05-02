import { FileSearch, Brain, CheckCircle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface LoadingStateProps {
  progress: number;
  fileName: string;
}

const stages = [
  { icon: FileSearch, label: 'Extracting text from document...', threshold: 30 },
  { icon: FileSearch, label: 'Recognizing medical entities...', threshold: 50 },
  { icon: Brain, label: 'Retrieving medical knowledge...', threshold: 70 },
  { icon: Brain, label: 'Generating patient-friendly explanations...', threshold: 90 },
  { icon: CheckCircle, label: 'Finalizing your report...', threshold: 100 },
];

export function LoadingState({ progress, fileName }: LoadingStateProps) {
  const currentStage =
    [...stages].reverse().find((stage) => progress >= stage.threshold) || stages[0];
  const Icon = currentStage.icon;

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
        <div className="flex flex-col items-center gap-6">
          <div className="relative">
            <div className="bg-blue-50 p-4 rounded-full">
              <Icon className="w-8 h-8 text-blue-600 animate-pulse" />
            </div>
          </div>
          
          <div className="text-center space-y-2">
            <p className="text-lg font-medium text-slate-900">
              {currentStage.label}
            </p>
            <p className="text-sm text-slate-500">
              Processing: {fileName}
            </p>
          </div>

          <div className="w-full space-y-2">
            <Progress value={progress} className="h-2" />
            <div className="flex justify-between text-xs text-slate-400">
              <span>OCR</span>
              <span>NLP</span>
              <span>RAG</span>
              <span>LLM</span>
              <span>Done</span>
            </div>
          </div>

          <div className="flex gap-2">
            {stages.map((stage, idx) => {
              const StageIcon = stage.icon;
              const isActive = progress >= stage.threshold;
              const isPast = progress > stage.threshold + 15;
              
              return (
                <div
                  key={idx}
                  className={`flex flex-col items-center gap-1 transition-all duration-300 ${
                    isActive ? 'opacity-100' : 'opacity-30'
                  }`}
                >
                  <StageIcon className={`w-4 h-4 ${isPast ? 'text-emerald-500' : isActive ? 'text-blue-500' : 'text-slate-300'}`} />
                  <div className={`w-1 h-1 rounded-full ${isActive ? 'bg-blue-500' : 'bg-slate-200'}`} />
                </div>
              );
            })}
          </div>

          <p className="text-xs text-slate-400 text-center max-w-md">
            This may take 30-60 seconds depending on report length and complexity.
            Please do not close this window.
          </p>
        </div>
      </div>
    </div>
  );
}
