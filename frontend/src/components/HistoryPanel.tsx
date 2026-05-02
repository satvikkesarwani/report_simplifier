import { BarChart3, Clock3, FileStack, FlaskConical, RefreshCcw, Trash2 } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ReportRecord } from '../services/api';

interface HistoryPanelProps {
  reports: ReportRecord[];
  onOpenReport: (reportId: string) => void;
  onRefresh: () => void;
  onDeleteReport?: (reportId: string) => void;
}

function formatDocumentType(documentType?: string | null) {
  if (!documentType) return 'Unknown';
  return documentType
    .replace(/_/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase());
}

function formatDate(value?: string | null) {
  if (!value) return 'Not processed';
  return new Date(value).toLocaleString();
}

export function HistoryPanel({ reports, onOpenReport, onRefresh, onDeleteReport }: HistoryPanelProps) {
  const processedReports = reports.filter(report => report.status === 'completed');
  const trendData = processedReports
    .slice(0, 6)
    .reverse()
    .map(report => ({
      name: new Date(report.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      abnormalCount: report.abnormal_count ?? 0,
    }));

  const totalReports = reports.length;
  const abnormalReports = processedReports.filter(report => (report.abnormal_count ?? 0) > 0).length;
  const averageReadability =
    processedReports.length > 0
      ? (
          processedReports.reduce((sum, report) => sum + (report.readability_score ?? 0), 0) /
          processedReports.length
        ).toFixed(1)
      : '0.0';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-slate-900">Report Dashboard</h3>
          <p className="text-sm text-slate-500">
            Review recent uploads, prior results, and abnormality trends.
          </p>
        </div>
        <Button variant="outline" onClick={onRefresh} className="gap-2">
          <RefreshCcw className="w-4 h-4" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-slate-200">
          <CardContent className="p-5">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-blue-100 p-3">
                <FileStack className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Total Reports</p>
                <p className="text-2xl font-semibold text-slate-900">{totalReports}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardContent className="p-5">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-red-100 p-3">
                <FlaskConical className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Reports With Abnormalities</p>
                <p className="text-2xl font-semibold text-slate-900">{abnormalReports}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardContent className="p-5">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-emerald-100 p-3">
                <BarChart3 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Avg. Readability Score</p>
                <p className="text-2xl font-semibold text-slate-900">{averageReadability}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr,1fr]">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-base">Historical Trend</CardTitle>
          </CardHeader>
          <CardContent className="h-[280px]">
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="abnormalCount" fill="#2563eb" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">
                Process a few reports to see historical abnormality trends.
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-base">Recent Reports</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {reports.length > 0 ? (
              reports.slice(0, 6).map(report => (
                <div
                  key={report.id}
                  className="w-full rounded-xl border border-slate-200 p-4 text-left transition hover:border-blue-300 hover:bg-slate-50"
                >
                  <div className="flex items-start justify-between gap-3">
                    <button type="button" onClick={() => onOpenReport(report.id)} className="flex-1 text-left">
                      <p className="font-medium text-slate-900">{report.original_filename}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Badge variant="secondary">{formatDocumentType(report.document_type)}</Badge>
                        <Badge variant={report.status === 'completed' ? 'default' : 'outline'}>
                          {report.status}
                        </Badge>
                        <Badge variant="outline">
                          {report.abnormal_count ?? 0} abnormal
                        </Badge>
                      </div>
                    </button>
                    <div className="flex items-center gap-1 text-xs text-slate-400">
                      <Clock3 className="w-3.5 h-3.5" />
                      <span>{formatDate(report.created_at)}</span>
                    </div>
                  </div>
                  {onDeleteReport && (
                    <div className="mt-3 flex justify-end">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="gap-2 text-red-600"
                        onClick={() => onDeleteReport(report.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </Button>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="rounded-xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
                Your uploaded reports will appear here once you start processing them. Sign in to keep this history private to your account.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
