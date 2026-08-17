import React from 'react';
import { UploadCloud, ArrowRight, Database, type LucideIcon } from 'lucide-react';
import { BrandLogo } from '../icons/BrandLogo';

export interface DatasetEmptyStateProps {
  /** Feature or engine badge label (e.g. "Analytics Engine", "Data Science Workspace", "AI Assistant") */
  badgeText?: string;
  /** Main heading title, defaults to "No Dataset Loaded" */
  title?: string;
  /** Contextual explanation text */
  description: string;
  /** Primary hero icon component */
  icon?: LucideIcon;
  /** Optional feature capability pills */
  features?: string[];
  /** Primary button label, defaults to "Upload Dataset" */
  buttonText?: string;
  /** Navigation callback to open Overview dataset upload */
  onNavigateToUpload?: () => void;
}

export const DatasetEmptyState: React.FC<DatasetEmptyStateProps> = ({
  badgeText = 'Data Management',
  title = 'No Dataset Loaded',
  description,
  icon: Icon = Database,
  features,
  buttonText = 'Upload Dataset',
  onNavigateToUpload
}) => {
  return (
    <div className="w-full max-w-3xl mx-auto py-8 px-4 flex flex-col items-center justify-center min-h-[55vh] text-center">
      {/* Outer Card Container */}
      <div className="w-full rounded-2xl border border-hairline bg-surface-card p-8 md:p-12 shadow-xs flex flex-col items-center justify-center text-center transition-all duration-200">
        
        {/* Badge Pill */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-light/60 border border-primary/20 text-primary text-xs font-semibold mb-5 shadow-2xs">
          <BrandLogo size={14} />
          <span>{badgeText}</span>
        </div>

        {/* Hero Icon Container */}
        <div className="w-16 h-16 rounded-2xl bg-primary-light/80 border border-primary/30 text-primary flex items-center justify-center mb-5 shadow-xs shrink-0">
          <Icon className="w-8 h-8" />
        </div>

        {/* Main Title */}
        <h2 className="text-display-sm text-ink font-bold tracking-tight mb-2">
          {title}
        </h2>

        {/* Subtitle / Description */}
        <p className="text-body-md text-muted max-w-lg mx-auto leading-relaxed mb-6">
          {description}
        </p>

        {/* Optional Feature Pills */}
        {features && features.length > 0 && (
          <div className="flex flex-wrap items-center justify-center gap-2 mb-8">
            {features.map((feat) => (
              <span
                key={feat}
                className="px-3 py-1 rounded-lg text-xs font-semibold bg-surface-soft text-muted border border-hairline"
              >
                {feat}
              </span>
            ))}
          </div>
        )}

        {/* Primary CTA Button */}
        <button
          onClick={onNavigateToUpload}
          className="btn-primary gap-2.5 px-6 py-2.5 rounded-xl font-semibold shadow-xs cursor-pointer inline-flex items-center group transition-all duration-150"
        >
          <UploadCloud className="w-4 h-4 text-white group-hover:scale-110 transition-transform" />
          <span>{buttonText}</span>
          <ArrowRight className="w-4 h-4 text-white/80 group-hover:translate-x-0.5 transition-transform" />
        </button>
      </div>
    </div>
  );
};
