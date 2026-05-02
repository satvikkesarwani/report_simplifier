import { useEffect, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  ClipboardList,
  Download,
  FileText,
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

function TestCard({ test, isAbnormal }: { test: TestResult; isAbnormal: boolean }) {
  const [isExpanded, setIsExpanded] = useState(isAbnormal);

  return (
    <Card className={`border ${isAbnormal ? 'border-red-200 bg-red-50/30' : 'border-slate-200'}`}>
      <CardHeader className="pb-3">
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

      {isExpanded && (
        <CardContent className="pt-0">
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

      <Card className="border-blue-200 bg-blue-50/50">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="shrink-0 rounded-full bg-blue-100 p-3">
              <FileText className="w-6 h-6 text-blue-600" />
            </div>
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-semibold text-slate-900">Patient-Friendly Summary</h3>
                <Badge variant="secondary">{formatDocumentType(result.document_type)}</Badge>
                {result.report_metadata?.status && <Badge variant="outline">{result.report_metadata.status}</Badge>}
              </div>
              <p className="text-sm leading-relaxed text-slate-700">{summary}</p>
              <div className="flex flex-wrap gap-4 pt-1 text-sm">
                <div>
                  <span className="font-medium text-slate-900">{total_tests}</span>
                  <span className="ml-1 text-slate-500">tests found</span>
                </div>
                <div>
                  <span className={`font-medium ${abnormal_count > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                    {abnormal_count}
                  </span>
                  <span className="ml-1 text-slate-500">abnormal values</span>
                </div>
                {readability && (
                  <div>
                    <span className="font-medium text-slate-900">{readability.flesch_reading_ease}</span>
                    <span className="ml-1 text-slate-500">Flesch score</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

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
