import React from 'react';
import {
  AlertTriangle,
  Copy,
  Fingerprint,
  Info,
  ShieldCheck
} from 'lucide-react';
import type { HealthOverview } from '../../lib/api';

interface DatasetHealthCardProps {
  health: HealthOverview;
}

export const DatasetHealthCard: React.FC<DatasetHealthCardProps> = ({ health }) => {
  const getQualityBadgeColor = (score: number) => {
    if (score >= 90) return 'bg-success-bg text-success border-success/30';
    if (score >= 70) return 'bg-warning-bg text-warning border-warning/30';
    return 'bg-error-bg text-error border-error/30';
  };

  const getQualityStatusText = (score: number) => {
    if (score >= 90) return 'Excellent Health';
    if (score >= 70) return 'Moderate Quality';
    return 'Action Needed';
  };

  return (
    <div className="p-6 rounded-2xl border border-hairline bg-surface-card shadow-xs space-y-6">
      {/* Header with Score */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-hairline">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary-light text-primary flex items-center justify-center">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-title-md text-ink font-bold">Dataset Health & Quality</h3>
            <p className="text-caption text-muted">
              Automated data integrity audit based on missingness, duplicates, & uniqueness
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 self-start sm:self-auto">
          <div className="text-right hidden sm:block">
            <div className="text-caption text-muted font-medium">Quality Score</div>
            <div className="text-xs font-semibold text-body">
              {getQualityStatusText(health.quality_score)}
            </div>
          </div>
          <div
            className={`px-4 py-2 rounded-xl font-mono text-xl font-bold border flex items-center gap-1.5 ${getQualityBadgeColor(
              health.quality_score
            )}`}
          >
            <span>{health.quality_score}</span>
            <span className="text-xs text-muted">/100</span>
          </div>
        </div>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Missing Cells */}
        <div className="p-4 rounded-xl bg-canvas border border-hairline">
          <div className="flex items-center justify-between text-caption text-muted mb-1">
            <span>Missing Cells</span>
            <AlertTriangle className={`w-3.5 h-3.5 ${health.missing_cells > 0 ? 'text-amber-500' : 'text-emerald-500'}`} />
          </div>
          <div className="text-title-lg font-bold text-ink">
            {health.missing_percentage}%
          </div>
          <div className="text-xs text-muted mt-0.5">
            {health.missing_cells.toLocaleString()} empty values
          </div>
        </div>

        {/* Duplicate Rows */}
        <div className="p-4 rounded-xl bg-canvas border border-hairline">
          <div className="flex items-center justify-between text-caption text-muted mb-1">
            <span>Duplicate Rows</span>
            <Copy className={`w-3.5 h-3.5 ${health.duplicate_rows > 0 ? 'text-amber-500' : 'text-emerald-500'}`} />
          </div>
          <div className="text-title-lg font-bold text-ink">
            {health.duplicate_percentage}%
          </div>
          <div className="text-xs text-muted mt-0.5">
            {health.duplicate_rows.toLocaleString()} exact duplicates
          </div>
        </div>

        {/* Constant Columns */}
        <div className="p-4 rounded-xl bg-canvas border border-hairline">
          <div className="flex items-center justify-between text-caption text-muted mb-1">
            <span>Constant Columns</span>
            <Info className="w-3.5 h-3.5 text-primary" />
          </div>
          <div className="text-title-lg font-bold text-ink">
            {health.constant_columns.length}
          </div>
          <div className="text-xs text-muted mt-0.5">
            Single value across all rows
          </div>
        </div>

        {/* Identifier Columns */}
        <div className="p-4 rounded-xl bg-canvas border border-hairline">
          <div className="flex items-center justify-between text-caption text-muted mb-1">
            <span>Likely ID Columns</span>
            <Fingerprint className="w-3.5 h-3.5 text-primary" />
          </div>
          <div className="text-title-lg font-bold text-ink">
            {health.likely_id_columns.length}
          </div>
          <div className="text-xs text-muted mt-0.5">
            High cardinality unique keys
          </div>
        </div>
      </div>

      {/* Special Column Tags (Constant & ID Columns) */}
      {(health.constant_columns.length > 0 || health.likely_id_columns.length > 0) && (
        <div className="flex flex-col sm:flex-row gap-4 pt-2 border-t border-hairline">
          {health.constant_columns.length > 0 && (
            <div className="flex-1">
              <span className="text-caption-uppercase text-muted font-semibold mb-2 block">
                Constant Columns ({health.constant_columns.length})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {health.constant_columns.map((col) => (
                  <span
                    key={col}
                    className="px-2.5 py-1 rounded-md text-xs font-mono bg-warning-bg/40 text-warning border border-warning/30 font-medium"
                  >
                    {col}
                  </span>
                ))}
              </div>
            </div>
          )}

          {health.likely_id_columns.length > 0 && (
            <div className="flex-1">
              <span className="text-caption-uppercase text-muted font-semibold mb-2 block">
                Detected ID / Key Columns ({health.likely_id_columns.length})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {health.likely_id_columns.map((col) => (
                  <span
                    key={col}
                    className="px-2.5 py-1 rounded-md text-xs font-mono bg-primary-light/60 text-primary border border-primary/20 font-medium"
                  >
                    {col}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
