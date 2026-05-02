import { AlertTriangle, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white border border-red-200 rounded-2xl p-8 shadow-sm">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="bg-red-50 p-4 rounded-full">
            <AlertTriangle className="w-8 h-8 text-red-500" />
          </div>
          
          <div>
            <h3 className="text-lg font-semibold text-slate-900">
              Processing Failed
            </h3>
            <p className="text-sm text-slate-500 mt-2 max-w-md">
              {message}
            </p>
          </div>

          <div className="bg-slate-50 rounded-lg p-4 text-left text-sm text-slate-600 max-w-md">
            <p className="font-medium mb-2">Common solutions:</p>
            <ul className="space-y-1 list-disc list-inside">
              <li>Ensure the file is a clear PDF or image</li>
              <li>Check that the report is readable (not blurry)</li>
              <li>Verify your internet connection</li>
              <li>Try with a smaller file or fewer pages</li>
            </ul>
          </div>

          <Button
            onClick={onRetry}
            variant="outline"
            className="flex items-center gap-2"
          >
            <RotateCcw className="w-4 h-4" />
            Try Again
          </Button>
        </div>
      </div>
    </div>
  );
}
