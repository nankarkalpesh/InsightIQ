import React, { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Sidebar } from './Sidebar';
import type { NavItemKey } from './Sidebar';
import { TopBar } from './TopBar';
import { UploadScreen } from '../../features/upload/UploadScreen';
import { OverviewScreen } from '../../features/overview/OverviewScreen';
import { AnalyticsWorkspace } from '../../features/analytics/AnalyticsWorkspace';
import { DataScienceWorkspace } from '../../features/datascience/DataScienceWorkspace';
import { DataChatWorkspace } from '../../features/datachat/DataChatWorkspace';
import { SettingsWorkspace } from '../../features/settings/SettingsWorkspace';
import { LoginScreen } from '../../features/auth/LoginScreen';
import { SignupScreen } from '../../features/auth/SignupScreen';
import { MyDatasets } from '../../features/auth/MyDatasets';
import { useDataset } from '../../store/datasetStore';
import { useAuth } from '../../store/authStore';
import { BrandLogo } from '../icons/BrandLogo';

interface AppLayoutProps {
  children?: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [activeNav, setActiveNavState] = useState<NavItemKey>(() => {
    try {
      const saved = localStorage.getItem('insightiq_active_nav');
      return (saved as NavItemKey) || 'Overview';
    } catch {
      return 'Overview';
    }
  });
  const [isMobileOpen, setIsMobileOpen] = useState<boolean>(false);
  const { dataset, isRestoringSession } = useDataset();
  const { isLoading: isAuthLoading } = useAuth();

  const setActiveNav = (nav: NavItemKey) => {
    setActiveNavState(nav);
    try {
      localStorage.setItem('insightiq_active_nav', nav);
    } catch (e) {
      console.error('Failed to save active nav to localStorage:', e);
    }
  };

  if (isRestoringSession || isAuthLoading) {
    return (
      <div className="min-h-screen bg-canvas text-ink flex items-center justify-center font-sans">
        <div className="flex flex-col items-center gap-3 p-8 rounded-2xl bg-surface-card border border-hairline shadow-xs text-center">
          <div className="relative">
            <BrandLogo size={44} />
            <Loader2 className="w-5 h-5 text-primary animate-spin absolute -bottom-1 -right-1 bg-surface-card rounded-full p-0.5 border border-hairline" />
          </div>
          <p className="text-body-sm font-semibold text-ink mt-1">Initializing InsightIQ...</p>
        </div>
      </div>
    );
  }

  const renderContent = () => {
    if (children) return children;

    if (activeNav === 'Login') {
      return (
        <LoginScreen
          onSwitchToSignup={() => setActiveNav('Signup')}
          onSuccessNavigate={() => setActiveNav('Overview')}
          onContinueAsGuest={() => setActiveNav('Overview')}
        />
      );
    }

    if (activeNav === 'Signup') {
      return (
        <SignupScreen
          onSwitchToLogin={() => setActiveNav('Login')}
          onSuccessNavigate={() => setActiveNav('Overview')}
          onContinueAsGuest={() => setActiveNav('Overview')}
        />
      );
    }

    if (activeNav === 'My Datasets') {
      return (
        <MyDatasets
          onNavigateToOverview={() => setActiveNav('Overview')}
          onNavigateToUpload={() => setActiveNav('Overview')}
        />
      );
    }

    if (activeNav === 'Overview') {
      if (!dataset) {
        return <UploadScreen />;
      }
      return <OverviewScreen />;
    }

    if (activeNav === 'Analytics') {
      return <AnalyticsWorkspace onNavigateToUpload={() => setActiveNav('Overview')} />;
    }

    if (activeNav === 'Data Science') {
      if (!dataset) {
        return <UploadScreen />;
      }
      return <DataScienceWorkspace />;
    }

    if (activeNav === 'Data Chat') {
      if (!dataset) {
        return <UploadScreen />;
      }
      return <DataChatWorkspace />;
    }

    if (activeNav === 'Settings') {
      return <SettingsWorkspace onNavigateToNav={setActiveNav} />;
    }

    return <OverviewScreen />;
  };

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col md:flex-row overflow-hidden font-sans theme-transition">
      {/* Sidebar navigation */}
      <Sidebar
        activeItem={activeNav}
        onSelectNavItem={(item) => setActiveNav(item)}
        isMobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
      />

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen bg-canvas theme-transition">
        {/* Top bar header */}
        <TopBar
          onOpenMobileMenu={() => setIsMobileOpen(true)}
          onSelectNavItem={(item) => setActiveNav(item)}
        />

        {/* Scrollable content view */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          {renderContent()}
        </main>
      </div>
    </div>
  );
};
