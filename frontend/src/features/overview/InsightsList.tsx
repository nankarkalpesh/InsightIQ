import React from 'react';
import { Sparkles, CheckCircle2, AlertTriangle, Layers, Key, FileText } from 'lucide-react';

interface InsightsListProps {
  insights: string[];
}

export const InsightsList: React.FC<InsightsListProps> = ({ insights }) => {
  const getInsightIcon = (text: string) => {
    const lower = text.toLowerCase();
    if (lower.includes('quality score')) return <Sparkles className="w-4 h-4 text-primary shrink-0" />;
    if (lower.includes('missing') || lower.includes('null')) return <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />;
    if (lower.includes('duplicate')) return <Layers className="w-4 h-4 text-orange-500 shrink-0" />;
    if (lower.includes('identifier') || lower.includes('id')) return <Key className="w-4 h-4 text-blue-500 shrink-0" />;
    if (lower.includes('no missing') || lower.includes('no duplicate')) return <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />;
    return <FileText className="w-4 h-4 text-muted shrink-0" />;
  };

  return (
    <div className="p-6 rounded-2xl border border-hairline bg-surface-card shadow-xs space-y-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary-light text-primary flex items-center justify-center">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-title-md text-ink font-bold">Automated Data Insights</h3>
          <p className="text-caption text-muted">
            Deterministic findings computed from dataset structure & distribution
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {insights.map((text, idx) => (
          <div
            key={idx}
            className="flex items-start gap-3 p-3.5 rounded-xl border border-hairline bg-canvas hover:border-primary/30 transition-colors"
          >
            <div className="mt-0.5">{getInsightIcon(text)}</div>
            <p className="text-body-sm text-ink leading-relaxed font-medium">
              {text}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
