import { useEffect, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  ClipboardList,
  Download,
  Info,
  Printer,
  Sparkles,
  Stethoscope,
  Trash2,
  RotateCcw,
  Send,
  ChevronDown,
  ChevronUp,
  Activity,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { getReportFileUrl, getReportPagePreviewUrl, submitFeedback } from '../services/api';
import type { FeedbackPayload, ProcessResponse, TestResult, VisualOverlayPage } from '../services/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface ReportViewerProps {
  result: ProcessResponse;
  onReset: () => void;
  onDeleteReport?: (reportId: string) => Promise<void> | void;
  onReprocessReport?: (reportId: string) => Promise<void> | void;
}

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function buildHighlightedText(result: ProcessResponse): string {
  const rawText = result.raw_text || '';
  const entities = result.structured_data?.entities || [];
  const abnormalNames = new Set(
    (result.simplified_output?.abnormal_tests || []).map(test => test.test_name.toLowerCase()),
  );

  if (!rawText || entities.length === 0) {
    return escapeHtml(rawText);
  }

  const spans = entities
    .filter(entity => entity.start < entity.end && entity.end <= rawText.length)
    .sort((left, right) => left.start - right.start);

  const fragments: string[] = [];
  let cursor = 0;

  for (const entity of spans) {
    if (entity.start < cursor) {
      continue;
    }
    fragments.push(escapeHtml(rawText.slice(cursor, entity.start)));
    const labelClass = abnormalNames.has(entity.text.toLowerCase())
      ? 'bg-red-100 text-red-900 ring-red-200'
      : 'bg-blue-100 text-blue-900 ring-blue-200';
    fragments.push(
      `<mark class="rounded px-1 py-0.5 ring-1 ${labelClass}" title="${escapeHtml(entity.label)}">${escapeHtml(rawText.slice(entity.start, entity.end))}</mark>`,
    );
    cursor = entity.end;
  }

  fragments.push(escapeHtml(rawText.slice(cursor)));
  return fragments.join('');
}

function detectPreviewKind(result: ProcessResponse, reportId: string): 'pdf' | 'image' | 'none' {
  if (!reportId) {
    return 'none';
  }

  const sourceName =
    result.report_metadata?.original_filename ||
    result.file_path ||
    '';
  const normalized = sourceName.toLowerCase();

  if (normalized.endsWith('.pdf')) {
    return 'pdf';
  }
  if (/\.(png|jpg|jpeg|webp)$/i.test(normalized)) {
    return 'image';
  }
  return 'none';
}

function formatDocumentType(documentType?: string) {
  if (!documentType) return 'Medical Report';
  return documentType.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
}

function getStatusBadge(status: string) {
  const statusLower = status.toLowerCase();
  if (statusLower === 'normal') {
    return <Badge variant="default" className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100">Normal</Badge>;
  }
  if (statusLower.includes('borderline')) {
    return <Badge variant="default" className="bg-amber-100 text-amber-800 hover:bg-amber-100">Borderline</Badge>;
  }
  if (statusLower.includes('low') || statusLower.includes('high')) {
    return <Badge variant="default" className="bg-red-100 text-red-800 hover:bg-red-100">{status}</Badge>;
  }
  return <Badge variant="secondary">{status}</Badge>;
}

function getStatusIcon(status: string) {
  const statusLower = status.toLowerCase();
  if (statusLower === 'normal') {
    return <CheckCircle2 className="w-5 h-5 text-emerald-500" />;
  }
  if (statusLower.includes('borderline')) {
    return <AlertCircle className="w-5 h-5 text-amber-500" />;
  }
  if (statusLower.includes('low') || statusLower.includes('high')) {
    return <AlertCircle className="w-5 h-5 text-red-500" />;
  }
  return <Info className="w-5 h-5 text-slate-400" />;
}

function stripMarkdown(value: string) {
  return value
    .replace(/\*\*/g, '')
    .replace(/#{1,6}\s/g, '')
    .replace(/^\s*[-*]\s+/gm, '')
    .trim();
}

function firstSentences(value: string, count = 2) {
  const clean = stripMarkdown(value);
  if (!clean || clean.toLowerCase().includes('llm service temporarily unavailable')) {
    return clean || 'Explanation unavailable.';
  }
  return clean
    .split(/(?<=[.!?])\s+/)
    .filter(Boolean)
    .slice(0, count)
    .join(' ');
}

function statusTone(status: string) {
  const normalized = status.toLowerCase();
  if (normalized === 'normal') return 'text-emerald-700 bg-emerald-50 border-emerald-200';
  if (normalized.includes('low')) return 'text-sky-700 bg-sky-50 border-sky-200';
  if (normalized.includes('high')) return 'text-red-700 bg-red-50 border-red-200';
  if (normalized.includes('borderline')) return 'text-amber-700 bg-amber-50 border-amber-200';
  return 'text-slate-700 bg-slate-50 border-slate-200';
}

function TestCard({ test, isAbnormal }: { test: TestResult; isAbnormal: boolean }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <Card className={`border ${isAbnormal ? 'border-red-200 bg-red-50/30' : 'border-slate-200'} py-4`}>
      <CardHeader className="px-4 pb-2">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            {getStatusIcon(test.status)}
            <div>
              <CardTitle className="text-base font-semibold">{test.test_name}</CardTitle>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <span
                  className={`font-bold ${
                    test.status === 'NORMAL'
                      ? 'text-emerald-700'
                      : test.status.includes('BORDERLINE')
                        ? 'text-amber-700'
                        : 'text-red-700'
                  }`}
                >
                  {test.value} {test.unit}
                </span>
                {test.normal_range && (
                  <span className="text-xs text-slate-500">
                    (Normal: {test.normal_range.min} - {test.normal_range.max} {test.normal_range.unit || test.unit})
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {getStatusBadge(test.status)}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 h-auto"
            >
              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="px-4 pt-0">
        <p className="line-clamp-2 text-sm leading-relaxed text-slate-600">
          {firstSentences(test.explanation)}
        </p>
      </CardContent>

      {isExpanded && (
        <CardContent className="px-4 pt-0">
          <div className="space-y-4">
            <div className="rounded-lg border border-slate-100 bg-white p-4">
              <h4 className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-900">
                <Stethoscope className="w-4 h-4 text-blue-500" />
                What This Means
              </h4>
              <div className="whitespace-pre-line text-sm leading-relaxed text-slate-700">
                {test.explanation || 'No explanation available.'}
              </div>
            </div>

            {test.retrieved_sources && test.retrieved_sources.length > 0 && (
              <div className="flex items-center gap-1 text-xs text-slate-400">
                <BookOpen className="w-3 h-3" />
                Sources: {test.retrieved_sources.join(', ')}
              </div>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

function MetricTile({
  label,
  value,
  sublabel,
  className,
}: {
  label: string;
  value: string | number;
  sublabel?: string;
  className: string;
}) {
  return (
    <div className={`min-h-[96px] rounded border p-4 ${className}`}>
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-slate-950">{value}</p>
      {sublabel && <p className="mt-1 text-xs text-slate-500">{sublabel}</p>}
    </div>
  );
}

function ReportDashboard({
  result,
  tests,
  abnormalTests,
  totalTests,
  abnormalCount,
}: {
  result: ProcessResponse;
  tests: TestResult[];
  abnormalTests: TestResult[];
  totalTests: number;
  abnormalCount: number;
}) {
  const readability = result.evaluation?.readability;
  const normalCount = Math.max(totalTests - abnormalCount, 0);
  const statusData = [
    { name: 'Normal', value: normalCount, color: '#10b981' },
    { name: 'High', value: tests.filter(test => test.status.toLowerCase().includes('high')).length, color: '#ef4444' },
    { name: 'Low', value: tests.filter(test => test.status.toLowerCase().includes('low')).length, color: '#0284c7' },
    { name: 'Other', value: tests.filter(test => !/(normal|high|low)/i.test(test.status)).length, color: '#94a3b8' },
  ].filter(item => item.value > 0);

  const topFindings = abnormalTests.slice(0, 8).map(test => ({
    name: test.test_name.length > 12 ? `${test.test_name.slice(0, 11)}...` : test.test_name,
    value: Number.parseFloat(test.value) || 1,
    status: test.status,
    unit: test.unit,
  }));

  return (
    <div className="space-y-4 rounded border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-slate-950">Simplified Report Dashboard</h2>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">
            A visual summary of extracted findings, abnormal values, and patient-friendly next steps.
          </p>
        </div>
        <Badge variant="outline" className="px-3 py-1">
          {formatDocumentType(result.document_type)}
        </Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <MetricTile label="Tests Found" value={totalTests} sublabel="from OCR extraction" className="border-blue-200 bg-blue-50" />
        <MetricTile label="Abnormal" value={abnormalCount} sublabel="needs doctor review" className="border-red-200 bg-red-50" />
        <MetricTile label="Readability" value={readability?.flesch_reading_ease ?? 'N/A'} sublabel="higher is easier" className="border-emerald-200 bg-emerald-50" />
        <MetricTile label="Grade Level" value={readability?.flesch_kincaid_grade?.toFixed?.(1) ?? 'N/A'} sublabel="estimated text grade" className="border-amber-200 bg-amber-50" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.9fr,1.1fr]">
        <div className="rounded border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-900">Result Mix</h3>
          <div className="mt-3 h-56">
            {statusData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={statusData} dataKey="value" nameKey="name" innerRadius={48} outerRadius={82} paddingAngle={2}>
                    {statusData.map(entry => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">No test status data.</div>
            )}
          </div>
          <div className="flex flex-wrap justify-center gap-3 text-xs">
            {statusData.map(item => (
              <span key={item.name} className="inline-flex items-center gap-1 text-slate-600">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                {item.name}: {item.value}
              </span>
            ))}
          </div>
        </div>

        <div className="rounded border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-900">Top Abnormal Findings</h3>
          <div className="mt-3 h-56">
            {topFindings.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topFindings}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis hide />
                  <Tooltip formatter={(value, _name, item) => [`${value} ${item.payload.unit}`, item.payload.status]} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]} fill="#2563eb" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">No abnormal values detected.</div>
            )}
          </div>
        </div>
      </div>

      {abnormalTests.length > 0 && (
        <div className="overflow-hidden rounded border border-slate-200">
          <div className="grid grid-cols-[1.1fr,0.8fr,0.8fr,1.5fr] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase text-slate-500">
            <span>Finding</span>
            <span>Value</span>
            <span>Status</span>
            <span>Plain-English Note</span>
          </div>
          {abnormalTests.slice(0, 6).map((test, index) => (
            <div key={`${test.test_name}-${index}`} className="grid grid-cols-[1.1fr,0.8fr,0.8fr,1.5fr] gap-3 border-t border-slate-100 px-3 py-3 text-sm">
              <span className="font-medium text-slate-900">{test.test_name}</span>
              <span className="text-slate-700">{test.value} {test.unit}</span>
              <span>
                <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusTone(test.status)}`}>
                  {test.status}
                </span>
              </span>
              <span className="line-clamp-2 text-slate-600">{firstSentences(test.explanation, 1)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ReportViewer({ result, onReset, onDeleteReport, onReprocessReport }: ReportViewerProps) {
  const output = result.simplified_output;
  const structuredData = result.structured_data;
  const readability = result.evaluation?.readability;
  const reportId = result.report_id || result.report_metadata?.id || '';
  const previewKind = detectPreviewKind(result, reportId);
  const previewUrl = reportId ? getReportFileUrl(reportId) : '';
  const visualOverlays = structuredData?.visual_overlays ?? [];
  const highlightedRawText = buildHighlightedText(result);
  const [feedback, setFeedback] = useState<FeedbackPayload>({
    comprehension_score: 5,
    usefulness_score: 5,
    highlighting_score: 5,
    recommendation_score: 5,
    comments: '',
  });
  const [feedbackStatus, setFeedbackStatus] = useState<string | null>(null);
  const [selectedOverlayPage, setSelectedOverlayPage] = useState(visualOverlays[0]?.page_number ?? 1);

  const entityPreview = structuredData?.entities?.slice(0, 18) ?? [];

  useEffect(() => {
    setSelectedOverlayPage(visualOverlays[0]?.page_number ?? 1);
  }, [result.report_id, result.report_metadata?.id, visualOverlays]);

  if (!output) return null;

  const {
    summary,
    tests,
    abnormal_tests,
    abnormal_count,
    total_tests,
    glossary,
    report_explanation,
    follow_up_questions,
  } = output;

  const activeOverlayPage = visualOverlays.find(page => page.page_number === selectedOverlayPage) ?? visualOverlays[0];

  const handleDownload = () => {
    const payload = [
      `Summary: ${summary}`,
      report_explanation ? `\nSimplified Interpretation:\n${report_explanation}` : '',
      tests.length
        ? `\nTests:\n${tests
            .map(test => `${test.test_name}: ${test.value} ${test.unit} (${test.status})`)
            .join('\n')}`
        : '',
      follow_up_questions.length
        ? `\nQuestions To Ask Your Doctor:\n${follow_up_questions.map((question, index) => `${index + 1}. ${question}`).join('\n')}`
        : '',
    ]
      .filter(Boolean)
      .join('\n');

    const blob = new Blob([payload], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${(result.report_metadata?.original_filename || 'medical-report').replace(/\.[^.]+$/, '')}-simplified.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    window.print();
  };

  const handleFeedbackSubmit = async () => {
    if (!reportId) {
      setFeedbackStatus('Unable to submit feedback because this report ID is missing.');
      return;
    }
    try {
      await submitFeedback(reportId, feedback);
      setFeedbackStatus('Thanks, your feedback has been saved.');
    } catch (error: any) {
      setFeedbackStatus(error?.response?.data?.detail || error.message || 'Failed to save feedback.');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <Button
          variant="ghost"
          onClick={onReset}
          className="flex items-center gap-2 text-slate-600"
        >
          <ArrowLeft className="w-4 h-4" />
          Upload Another Report
        </Button>
        <div className="flex gap-2">
          {reportId && onReprocessReport && (
            <Button
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
              onClick={() => onReprocessReport(reportId)}
            >
              <RotateCcw className="w-4 h-4" />
              Reprocess
            </Button>
          )}
          {reportId && onDeleteReport && (
            <Button
              variant="outline"
              size="sm"
              className="flex items-center gap-2 text-red-600"
              onClick={() => onDeleteReport(reportId)}
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </Button>
          )}
          <Button variant="outline" size="sm" className="flex items-center gap-2" onClick={handleDownload}>
            <Download className="w-4 h-4" />
            Download
          </Button>
          <Button variant="outline" size="sm" className="flex items-center gap-2" onClick={handlePrint}>
            <Printer className="w-4 h-4" />
            Print
          </Button>
        </div>
      </div>

      <ReportDashboard
        result={result}
        tests={tests}
        abnormalTests={abnormal_tests}
        totalTests={total_tests}
        abnormalCount={abnormal_count}
      />

      {abnormal_count > 0 && (
        <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4">
          <AlertCircle className="w-5 h-5 shrink-0 text-red-500" />
          <div>
            <p className="text-sm font-medium text-red-800">
              {abnormal_count} abnormal value{abnormal_count > 1 ? 's' : ''} detected
            </p>
            <p className="mt-0.5 text-xs text-red-600">
              These values are outside normal ranges. Please discuss them with your doctor.
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ClipboardList className="w-5 h-5 text-slate-500" />
              Original Report
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {previewKind !== 'none' && (
              <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                {previewKind === 'pdf' ? (
                  <iframe
                    title="Original medical report preview"
                    src={previewUrl}
                    className="h-[320px] w-full"
                  />
                ) : (
                  <img
                    src={previewUrl}
                    alt="Original medical report preview"
                    className="max-h-[320px] w-full object-contain bg-slate-50"
                  />
                )}
              </div>
            )}

            {reportId && activeOverlayPage?.preview_available && (
              <VisualOverlayPanel
                reportId={reportId}
                overlayPages={visualOverlays}
                activePage={activeOverlayPage}
                onPageChange={setSelectedOverlayPage}
              />
            )}

            <ScrollArea className="h-[320px] rounded-lg border border-slate-100 bg-slate-50 p-4">
              {result.raw_text ? (
                <div
                  className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700"
                  dangerouslySetInnerHTML={{ __html: highlightedRawText }}
                />
              ) : (
                <pre className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                  Original extracted text is not available.
                </pre>
              )}
            </ScrollArea>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
              {previewKind !== 'none' && (
                <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700">Original document preview</span>
              )}
              <span className="rounded-full bg-blue-100 px-2 py-1 text-blue-900">Detected entity</span>
              <span className="rounded-full bg-red-100 px-2 py-1 text-red-900">Abnormal-related entity</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Sparkles className="w-5 h-5 text-blue-500" />
              Simplified Interpretation
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border border-blue-100 bg-blue-50/60 p-4">
              <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700">
                {report_explanation || summary}
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-500">Readability</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">
                  {readability?.flesch_reading_ease ?? 'N/A'}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-500">Entities</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">
                  {result.evaluation?.extraction.entities_found ?? 0}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-500">Grade Level</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">
                  {readability?.flesch_kincaid_grade ?? 'N/A'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue={abnormal_count > 0 ? 'abnormal' : 'all'} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="all">All Tests ({total_tests})</TabsTrigger>
          <TabsTrigger value="abnormal" className={abnormal_count > 0 ? 'text-red-600' : ''}>
            Abnormal ({abnormal_count})
          </TabsTrigger>
          <TabsTrigger value="entities">
            Entities ({structuredData?.entities?.length ?? 0})
          </TabsTrigger>
          <TabsTrigger value="glossary">
            Glossary ({Object.keys(glossary || {}).length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="mt-4">
          {tests.length > 0 ? (
            <ScrollArea className="h-[600px]">
              <div className="space-y-3 pr-4">
                {tests.map((test, idx) => (
                  <TestCard
                    key={idx}
                    test={test}
                    isAbnormal={test.status !== 'NORMAL' && test.status !== 'UNKNOWN'}
                  />
                ))}
              </div>
            </ScrollArea>
          ) : (
            <Card>
              <CardContent className="p-6 text-sm text-slate-600">
                This report did not contain a structured lab table, so the system generated a narrative simplification instead.
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="abnormal" className="mt-4">
          {abnormal_tests.length > 0 ? (
            <ScrollArea className="h-[600px]">
              <div className="space-y-3 pr-4">
                {abnormal_tests.map((test, idx) => (
                  <TestCard key={idx} test={test} isAbnormal={true} />
                ))}
              </div>
            </ScrollArea>
          ) : (
            <div className="rounded-xl border border-emerald-100 bg-emerald-50 py-12 text-center">
              <CheckCircle2 className="mx-auto mb-3 h-12 w-12 text-emerald-500" />
              <p className="text-lg font-medium text-emerald-800">No abnormal values detected</p>
              <p className="mt-1 text-sm text-emerald-600">
                Either all extracted tests were normal or this report was narrative rather than tabular.
              </p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="entities" className="mt-4">
          <div className="grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Detected Medical Entities</CardTitle>
              </CardHeader>
              <CardContent>
                {entityPreview.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {entityPreview.map((entity, index) => (
                      <Badge key={`${entity.text}-${index}`} variant="outline" className="px-3 py-1">
                        {entity.text}
                        <span className="ml-2 text-slate-400">{entity.label}</span>
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No entities were extracted from this report.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Activity className="w-5 h-5 text-blue-500" />
                  Questions To Ask Your Doctor
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {follow_up_questions.length > 0 ? (
                  follow_up_questions.map(question => (
                    <div key={question} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                      {question}
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-500">No follow-up questions generated.</p>
                )}
              </CardContent>
            </Card>
          </div>

          {structuredData?.narrative_findings && structuredData.narrative_findings.length > 0 && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle className="text-base">Narrative Findings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {structuredData.narrative_findings.map((finding, index) => (
                  <div key={`${finding.section}-${index}`} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{finding.section}</p>
                    <p className="mt-1 text-sm text-slate-700">{finding.text}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="glossary" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BookOpen className="w-5 h-5 text-blue-500" />
                Medical Terms Glossary
              </CardTitle>
            </CardHeader>
            <CardContent>
              {glossary && Object.keys(glossary).length > 0 ? (
                <div className="space-y-4">
                  {Object.entries(glossary).map(([term, definition]) => (
                    <div key={term} className="border-b border-slate-100 pb-3 last:border-0">
                      <h4 className="font-medium text-slate-900">{term}</h4>
                      <p className="mt-1 text-sm text-slate-600">{definition as string}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No glossary terms available for this report.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <Info className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" />
        <div>
          <p className="text-sm font-medium text-amber-800">Important Disclaimer</p>
          <p className="mt-1 text-xs leading-relaxed text-amber-700">
            This simplified explanation is generated by AI for educational purposes only.
            It does not constitute medical advice or diagnosis. Always consult a qualified
            healthcare professional for interpretation of your medical reports and
            before making any health decisions.
          </p>
        </div>
      </div>

      {reportId && (
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Send className="w-5 h-5 text-blue-500" />
              Share Your Feedback
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {[
                ['comprehension_score', 'Comprehension'],
                ['usefulness_score', 'Usefulness'],
                ['highlighting_score', 'Highlighting'],
                ['recommendation_score', 'Recommendation'],
              ].map(([key, label]) => (
                <label key={key} className="space-y-2 text-sm text-slate-700">
                  <span className="font-medium">{label}</span>
                  <select
                    className="w-full rounded-lg border border-slate-300 px-3 py-2"
                    value={(feedback as Record<string, any>)[key] ?? 5}
                    onChange={event =>
                      setFeedback(current => ({
                        ...current,
                        [key]: Number(event.target.value),
                      }))
                    }
                  >
                    {[1, 2, 3, 4, 5].map(value => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>

            <label className="space-y-2 text-sm text-slate-700">
              <span className="font-medium">Comments</span>
              <textarea
                className="min-h-[100px] w-full rounded-lg border border-slate-300 px-3 py-2"
                value={feedback.comments ?? ''}
                onChange={event =>
                  setFeedback(current => ({
                    ...current,
                    comments: event.target.value,
                  }))
                }
                placeholder="Tell us what was clear, confusing, or missing."
              />
            </label>

            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-slate-500">
                This feedback helps evaluate readability, usefulness, and clarity of abnormal-value communication.
              </p>
              <Button onClick={handleFeedbackSubmit} className="gap-2">
                <Send className="w-4 h-4" />
                Submit Feedback
              </Button>
            </div>

            {feedbackStatus && <p className="text-sm text-slate-600">{feedbackStatus}</p>}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function VisualOverlayPanel({
  reportId,
  overlayPages,
  activePage,
  onPageChange,
}: {
  reportId: string;
  overlayPages: VisualOverlayPage[];
  activePage: VisualOverlayPage;
  onPageChange: (pageNumber: number) => void;
}) {
  const previewUrl = getReportPagePreviewUrl(reportId, activePage.page_number);

  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-900">Visual Entity Overlay</p>
          <p className="text-xs text-slate-500">
            Highlight boxes are projected back onto the report page using OCR and text extraction coordinates.
          </p>
        </div>
        {overlayPages.length > 1 && (
          <div className="flex flex-wrap gap-2">
            {overlayPages.map(page => (
              <Button
                key={page.page_number}
                type="button"
                variant={page.page_number === activePage.page_number ? 'default' : 'outline'}
                size="sm"
                onClick={() => onPageChange(page.page_number)}
              >
                Page {page.page_number}
              </Button>
            ))}
          </div>
        )}
      </div>

      <div className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
        <img
          src={previewUrl}
          alt={`Report page ${activePage.page_number}`}
          className="w-full object-contain"
        />
        <div className="pointer-events-none absolute inset-0">
          {activePage.highlights.map((highlight, index) => (
            <div
              key={`${highlight.text}-${index}`}
              className={`absolute rounded border-2 ${
                highlight.style === 'abnormal'
                  ? 'border-red-500 bg-red-400/15'
                  : 'border-blue-500 bg-blue-400/10'
              }`}
              style={{
                left: `${(highlight.x / activePage.width) * 100}%`,
                top: `${(highlight.y / activePage.height) * 100}%`,
                width: `${(highlight.width / activePage.width) * 100}%`,
                height: `${(highlight.height / activePage.height) * 100}%`,
              }}
              title={`${highlight.text} (${highlight.label})`}
            />
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 text-xs text-slate-500">
        <span className="rounded-full bg-blue-100 px-2 py-1 text-blue-900">Entity overlay</span>
        <span className="rounded-full bg-red-100 px-2 py-1 text-red-900">Abnormal test overlay</span>
        <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700">
          {activePage.highlight_count} highlight{activePage.highlight_count === 1 ? '' : 's'}
        </span>
      </div>
    </div>
  );
}
