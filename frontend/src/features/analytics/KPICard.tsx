import React, { useState } from 'react';
import {
  Check,
  ChevronDown,
  ChevronUp,
  Code2,
  Copy,
  HelpCircle,
  PlusCircle,
  Sparkles,
  Tag
} from 'lucide-react';
import type { RecommendedKPI } from '../../lib/api';
import { useDashboard } from '../../store/dashboardStore';

interface KPICardProps {
  kpi: RecommendedKPI;
  onAddToDashboard?: (kpiName: string) => void;
}

export const KPICard: React.FC<KPICardProps> = ({ kpi, onAddToDashboard }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const { addItem, removeItem, isInDashboard } = useDashboard();

  const itemId = `kpi_${kpi.kpi_name}`;
  const inDashboard = isInDashboard(itemId);

  const handleCopyDAX = async () => {
    try {
      await navigator.clipboard.writeText(kpi.dax);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy DAX:', err);
    }
  };

  const handleToggleDashboard = () => {
    if (inDashboard) {
      removeItem(itemId);
    } else {
      addItem({
        id: itemId,
        type: 'kpi',
        kpiData: kpi,
      });
      if (onAddToDashboard) {
        onAddToDashboard(kpi.kpi_name);
      }
    }
  };

  const formatDisplayValue = (val: number | string | null, name: string) => {
    if (val === null || val === undefined) return 'N/A';
    if (typeof val === 'string') return val;

    const lowerName = name.toLowerCase();

    // Percentage / Ratio formatting
    if (lowerName.includes('margin') || lowerName.includes('ratio') || lowerName.includes('rate')) {
      if (val <= 1.0 && val >= -1.0) {
        return `${(val * 100).toFixed(1)}%`;
      }
      return `${val.toFixed(2)}%`;
    }

    // Currency formatting
    const currencyKeywords = [
      'amount', 'price', 'value', 'revenue', 'sales',
      'cost', 'profit', 'fine', 'loss', 'salary', 'income', 'expense'
    ];
    if (currencyKeywords.some((kw) => lowerName.includes(kw))) {
      return `$${val.toLocaleString(undefined, {
        minimumFractionDigits: val % 1 === 0 ? 0 : 2,
        maximumFractionDigits: 2,
      })}`;
    }

    // Number formatting
    if (Number.isInteger(val)) {
      return val.toLocaleString();
    }
    return val.toLocaleString(undefined, { maximumFractionDigits: 2 });
  };

  return (
    <div className="flex flex-col justify-between p-6 rounded-2xl border border-hairline bg-surface-card shadow-xs hover:shadow-md transition-all duration-200 space-y-4">
      {/* Top Header & Tags */}
      <div>
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary-light text-primary flex items-center justify-center font-bold shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            <h3 className="text-title-sm text-ink font-bold leading-tight">
              {kpi.kpi_name}
            </h3>
          </div>
        </div>

        {/* Formatted Prominent Value */}
        <div className="mt-3 mb-2">
          <div className="text-display-md font-extrabold text-ink tracking-tight">
            {formatDisplayValue(kpi.value, kpi.kpi_name)}
          </div>
        </div>

        {/* Required Columns Badges */}
        {kpi.required_columns.length > 0 ? (
          <div className="flex flex-wrap items-center gap-1.5 mt-2">
            <span className="text-caption text-muted flex items-center gap-1">
              <Tag className="w-3 h-3 text-muted-soft" />
              Columns:
            </span>
            {kpi.required_columns.map((col) => (
              <span
                key={col}
                className="px-2 py-0.5 rounded-md text-xs font-mono bg-canvas text-ink border border-hairline font-medium"
              >
                {col}
              </span>
            ))}
          </div>
        ) : (
          <div className="text-caption text-muted mt-2">
            Applies to whole dataset
          </div>
        )}
      </div>

      {/* Expandable Explanation Panel (Definition & Why this KPI) */}
      {isExpanded && (
        <div className="p-4 rounded-xl bg-canvas border border-hairline space-y-3 text-xs animate-in fade-in duration-200">
          <div>
            <span className="text-caption-uppercase text-muted font-bold block mb-0.5">
              Definition
            </span>
            <p className="text-ink font-medium leading-relaxed">{kpi.definition}</p>
          </div>
          <div>
            <span className="text-caption-uppercase text-primary font-bold block mb-0.5">
              Why this KPI?
            </span>
            <p className="text-muted leading-relaxed font-medium">{kpi.reason}</p>
          </div>
          <div>
            <span className="text-caption-uppercase text-muted font-bold block mb-0.5">
              Calculation Logic
            </span>
            <p className="text-ink font-mono text-xs">{kpi.calculation_logic}</p>
          </div>
        </div>
      )}

      {/* DAX Code Block */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-caption text-muted">
          <span className="flex items-center gap-1 font-semibold text-xs text-muted">
            <Code2 className="w-3.5 h-3.5 text-primary" />
            DAX Expression
          </span>
        </div>
        <div className="p-3 rounded-xl bg-slate-950 text-slate-100 font-mono text-xs overflow-x-auto border border-slate-800 shadow-inner">
          <code>{kpi.dax}</code>
        </div>
      </div>

      {/* Action Footer Buttons */}
      <div className="pt-3 border-t border-hairline flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {/* Copy DAX Button */}
          <button
            onClick={handleCopyDAX}
            className="btn-ghost py-1.5 px-2.5 text-xs gap-1.5 text-muted hover:text-ink transition-colors"
            title="Copy DAX to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-500" />
                <span className="text-emerald-500 font-semibold">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy DAX</span>
              </>
            )}
          </button>

          {/* Explain Toggle Button */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="btn-ghost py-1.5 px-2.5 text-xs gap-1.5 text-muted hover:text-ink transition-colors"
          >
            <HelpCircle className="w-3.5 h-3.5 text-primary" />
            <span>Explain</span>
            {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>

        {/* Add to Dashboard Button */}
        <button
          onClick={handleToggleDashboard}
          className={`py-1.5 px-3 text-xs gap-1.5 shrink-0 rounded-lg font-semibold border transition-all ${
            inDashboard
              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
              : 'btn-secondary'
          }`}
        >
          {inDashboard ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-500" />
              <span>In Dashboard</span>
            </>
          ) : (
            <>
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Add to Dashboard</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
