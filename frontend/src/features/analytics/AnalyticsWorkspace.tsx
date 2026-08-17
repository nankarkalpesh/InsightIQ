import React, { useState } from 'react';
import { BarChart3, Gauge, LayoutDashboard } from 'lucide-react';
import { KPIStudio } from './KPIStudio';
import { VisualizationStudio } from './VisualizationStudio';
import { DashboardBuilder } from './DashboardBuilder';
import { useDashboard } from '../../store/dashboardStore';

type AnalyticsSubTab = 'KPIs' | 'Visualizations' | 'Dashboard';

export interface AnalyticsWorkspaceProps {
  onNavigateToUpload?: () => void;
}

const AnalyticsWorkspaceContent: React.FC<AnalyticsWorkspaceProps> = ({ onNavigateToUpload }) => {
  const [activeTab, setActiveTabState] = useState<AnalyticsSubTab>(() => {
    try {
      const saved = localStorage.getItem('insightiq_analytics_subtab');
      return (saved as AnalyticsSubTab) || 'KPIs';
    } catch {
      return 'KPIs';
    }
  });
  const { items } = useDashboard();

  const setActiveTab = (tab: AnalyticsSubTab) => {
    setActiveTabState(tab);
    try {
      localStorage.setItem('insightiq_analytics_subtab', tab);
    } catch (e) {
      console.error('Failed to save analytics subtab to localStorage:', e);
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* Sub-Tab Navigation Header */}
      <div className="flex items-center justify-between pb-2 border-b border-hairline max-w-6xl mx-auto">
        <div className="flex items-center gap-1 p-1 bg-surface-soft/60 border border-hairline rounded-xl">
          <button
            onClick={() => setActiveTab('KPIs')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-150 select-none ${
              activeTab === 'KPIs'
                ? 'bg-surface-card text-ink shadow-xs border border-hairline'
                : 'text-muted hover:text-ink'
            }`}
          >
            <Gauge className="w-4 h-4 text-primary" />
            <span>KPI Studio</span>
          </button>

          <button
            onClick={() => setActiveTab('Visualizations')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-150 select-none ${
              activeTab === 'Visualizations'
                ? 'bg-surface-card text-ink shadow-xs border border-hairline'
                : 'text-muted hover:text-ink'
            }`}
          >
            <BarChart3 className="w-4 h-4 text-emerald-500" />
            <span>Visualization Studio</span>
          </button>

          <button
            onClick={() => setActiveTab('Dashboard')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-150 select-none relative ${
              activeTab === 'Dashboard'
                ? 'bg-surface-card text-ink shadow-xs border border-hairline'
                : 'text-muted hover:text-ink'
            }`}
          >
            <LayoutDashboard className="w-4 h-4 text-purple-500" />
            <span>Dashboard</span>
            {items.length > 0 && (
              <span className="ml-1 px-1.5 py-0.2 text-[10px] font-bold bg-primary text-white rounded-full">
                {items.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Render Active Sub-Tab View */}
      {activeTab === 'KPIs' && <KPIStudio onNavigateToUpload={onNavigateToUpload} />}
      {activeTab === 'Visualizations' && <VisualizationStudio onNavigateToUpload={onNavigateToUpload} />}
      {activeTab === 'Dashboard' && (
        <DashboardBuilder onNavigateTab={(tab) => setActiveTab(tab)} onNavigateToUpload={onNavigateToUpload} />
      )}
    </div>
  );
};

export const AnalyticsWorkspace: React.FC<AnalyticsWorkspaceProps> = ({ onNavigateToUpload }) => {
  return <AnalyticsWorkspaceContent onNavigateToUpload={onNavigateToUpload} />;
};
