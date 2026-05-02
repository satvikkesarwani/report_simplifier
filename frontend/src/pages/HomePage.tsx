import { useEffect, useState } from 'react';
import { Activity, FileText, Heart, Shield } from 'lucide-react';

import { ErrorState } from '../components/ErrorState';
import { HistoryPanel } from '../components/HistoryPanel';
import { LoadingState } from '../components/LoadingState';
import { ReportViewer } from '../components/ReportViewer';
import { UploadZone } from '../components/UploadZone';
import {
  deleteReport,
  getJob,
  getReport,
  listReports,
  startProcessReportJob,
  uploadFile,
} from '../services/api';
import type { ProcessResponse, ReportRecord } from '../services/api';

export default function HomePage() {
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [fileName, setFileName] = useState('');
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [history, setHistory] = useState<ReportRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const loadHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const reports = await listReports();
      setHistory(reports);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load report history');
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const waitForProcessingJob = async (jobId: string) => {
    const startedAt = Date.now();
    const timeoutMs = 8 * 60 * 1000;

    while (Date.now() - startedAt < timeoutMs) {
      const job = await getJob(jobId);
      const progressValue = Number(job.progress || 0);
      setProgress(Math.max(40, Math.min(99, progressValue)));

      if (job.status === 'completed') {
        if (job.result) {
          setProgress(100);
          return job.result;
        }
        throw new Error('Processing finished, but no report result was returned.');
      }

      if (job.status === 'failed') {
        throw new Error(job.error || job.message || 'Report processing failed.');
      }

      await new Promise((resolve) => window.setTimeout(resolve, 1500));
    }

    throw new Error('Report processing is taking longer than expected. Please refresh the dashboard.');
  };

  const processReportWithJob = async (fileId: string) => {
    const job = await startProcessReportJob(fileId);
    setProgress(Math.max(40, Number(job.progress || 40)));
    return waitForProcessingJob(job.job_id);
  };

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    setError(null);
    setResult(null);
    setFileName(file.name);
    setProgress(10);

    try {
      const uploadRes = await uploadFile(file);
      setProgress(30);

      setIsUploading(false);
      setIsProcessing(true);
      setProgress(40);

      const processRes = await processReportWithJob(uploadRes.file_id);
      setProgress(100);
      setResult(processRes);
      await loadHistory();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Something went wrong');
    } finally {
      setIsUploading(false);
      setIsProcessing(false);
    }
  };

  const handleOpenReport = async (reportId: string) => {
    setError(null);
    try {
      const report = await getReport(reportId);
      if (report.processing_result) {
        setResult(report.processing_result);
        return;
      }
      setError('This report has been uploaded but not processed yet.');
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to open report');
    }
  };

  const handleDeleteReport = async (reportId: string) => {
    try {
      await deleteReport(reportId);
      if (result?.report_id === reportId || result?.report_metadata?.id === reportId) {
        setResult(null);
      }
      await loadHistory();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to delete report');
    }
  };

  const handleReprocessReport = async (reportId: string) => {
    setError(null);
    setIsProcessing(true);
    setProgress(40);
    try {
      const processRes = await processReportWithJob(reportId);
      setProgress(100);
      setResult(processRes);
      await loadHistory();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to reprocess report');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
    setFileName('');
    setProgress(0);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-600 p-2">
              <Heart className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900">MedSimplify</h1>
              <p className="text-xs text-slate-500">RAG-Based Medical Report Simplifier</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Shield className="h-4 w-4" />
            <span>Patient-safe explanation flow</span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-10 px-4 py-8 sm:px-6 lg:px-8">
        {!result && !error && (
          <>
            <div className="space-y-8">
              <div className="space-y-4 py-8 text-center">
                <h2 className="text-4xl font-bold text-slate-900">
                  Understand Your Medical Reports
                </h2>
                <p className="mx-auto max-w-3xl text-lg text-slate-600">
                  Upload pathology, radiology, discharge, or prescription-style reports and get
                  grounded, patient-friendly explanations powered by OCR, NLP, RAG, and LLMs.
                </p>
                <div className="flex justify-center gap-6 pt-4">
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <FileText className="h-4 w-4 text-blue-600" />
                    <span>PDF & Images</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <Activity className="h-4 w-4 text-blue-600" />
                    <span>Abnormality Detection</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <Shield className="h-4 w-4 text-blue-600" />
                    <span>History & Evaluation</span>
                  </div>
                </div>
              </div>

              <UploadZone onUpload={handleUpload} isUploading={isUploading || isProcessing} />

              {(isUploading || isProcessing) && (
                <LoadingState progress={progress} fileName={fileName} />
              )}
            </div>

            {!isUploading && !isProcessing && (
              <div>
                <HistoryPanel
                  reports={history}
                  onOpenReport={handleOpenReport}
                  onRefresh={loadHistory}
                  onDeleteReport={handleDeleteReport}
                />
              </div>
            )}

            {isLoadingHistory && (
              <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">
                Loading report history...
              </div>
            )}
          </>
        )}

        {error && <ErrorState message={error} onRetry={handleReset} />}

        {result && (
          <ReportViewer
            result={result}
            onReset={handleReset}
            onDeleteReport={handleDeleteReport}
            onReprocessReport={handleReprocessReport}
          />
        )}
      </main>

      <footer className="mt-16 border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-6 text-center text-sm text-slate-500 sm:px-6 lg:px-8">
          <p>MedSimplify is an educational tool. Always consult healthcare professionals for medical advice.</p>
          <p className="mt-1">Built with RAG + NVIDIA LLM • IIIT Pune BTP Project</p>
        </div>
      </footer>
    </div>
  );
}
