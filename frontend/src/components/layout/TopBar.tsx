import React, { useState, useRef, useEffect } from 'react';
import { Menu, Database, User, Sun, Moon, LogOut, LogIn, UserPlus, FolderClock, Settings, ChevronDown, Bookmark, CheckCircle2, RefreshCw } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';
import { useDataset } from '../../store/datasetStore';
import { useAuth } from '../../store/authStore';
import { saveActivityApi } from '../../lib/api';
import { BrandLogo } from '../icons/BrandLogo';

interface TopBarProps {
  onOpenMobileMenu: () => void;
  onSelectNavItem?: (item: any) => void;
}

const SaveActivityButton: React.FC<{ datasetId: string }> = ({ datasetId }) => {
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  const handleSave = async () => {
    if (saveStatus === 'saving') return;
    setSaveStatus('saving');
    try {
      // Gather local storage dashboard items if available
      let dashItems: any[] | undefined = undefined;
      try {
        const keys = Object.keys(localStorage);
        const dashKey = keys.find((k) => k.includes('_dashboard_') && k.includes(datasetId));
        if (dashKey) {
          dashItems = JSON.parse(localStorage.getItem(dashKey) || '[]');
        }
      } catch (e) {}

      await saveActivityApi(datasetId, undefined, dashItems);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 4000);
    } catch (err: any) {
      console.error('Failed to save activity:', err);
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  };

  return (
    <button
      onClick={handleSave}
      disabled={saveStatus === 'saving'}
      className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all duration-150 flex items-center gap-1.5 cursor-pointer shrink-0 shadow-2xs ${
        saveStatus === 'saved'
          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
          : saveStatus === 'error'
          ? 'bg-red-500/10 text-red-600 border-red-500/30'
          : 'bg-primary text-on-primary border-primary hover:bg-primary-active'
      }`}
      title="Explicitly save dataset analysis, dashboard, and chat history"
    >
      {saveStatus === 'saving' ? (
        <>
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          <span className="hidden sm:inline">Saving...</span>
        </>
      ) : saveStatus === 'saved' ? (
        <>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          <span>Saved ✓</span>
        </>
      ) : saveStatus === 'error' ? (
        <span>Save Failed</span>
      ) : (
        <>
          <Bookmark className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Save Activity</span>
        </>
      )}
    </button>
  );
};

export const TopBar: React.FC<TopBarProps> = ({
  onOpenMobileMenu,
  onSelectNavItem
}) => {
  const { theme, toggleTheme } = useTheme();
  const { dataset } = useDataset();
  const { user, isAuthenticated, logout } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const datasetDisplayText = dataset
    ? `${dataset.filename} · ${dataset.row_count !== null && dataset.row_count !== undefined ? dataset.row_count.toLocaleString() : 0} rows`
    : 'No dataset loaded';

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleNavClick = (navKey: string) => {
    setShowDropdown(false);
    if (onSelectNavItem) {
      onSelectNavItem(navKey);
    }
  };

  return (
    <header className="h-16 bg-header border-b border-header-border px-4 md:px-6 flex items-center justify-between sticky top-0 z-30 shrink-0">
      {/* Left side: Mobile Toggle + App Name */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="md:hidden p-2 rounded-md text-ink hover:bg-surface-soft transition-colors"
          aria-label="Open Navigation Menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5">
          <BrandLogo size={28} />
          <span className="font-semibold text-lg md:text-xl tracking-tight text-ink">
            InsightIQ
          </span>
        </div>
      </div>

      {/* Middle: Active Dataset Badge + Save Activity Action */}
      <div className="flex-1 max-w-lg mx-4 flex items-center gap-2">
        <div className="flex-1 flex items-center gap-2.5 px-3 py-1.5 bg-surface-card text-ink text-sm font-medium rounded-xl border border-hairline shadow-2xs min-w-0">
          <Database className={`w-4 h-4 shrink-0 ${dataset ? 'text-primary' : 'text-muted'}`} />
          <span className={`truncate text-xs sm:text-sm ${dataset ? 'text-ink font-semibold' : 'text-muted'}`}>
            {datasetDisplayText}
          </span>
          {dataset && (
            <span className="ml-auto w-2 h-2 rounded-full bg-emerald-500 shrink-0 animate-pulse" title="Active in Session" />
          )}
        </div>

        {/* Save Activity Action Button for Logged-In Users */}
        {dataset && isAuthenticated && (
          <SaveActivityButton datasetId={dataset.file_id} />
        )}
      </div>

      {/* Right side: Theme Toggle + Profile Dropdown */}
      <div className="flex items-center gap-2 md:gap-3 relative" ref={dropdownRef}>
        <button
          onClick={toggleTheme}
          className="p-2 rounded-md border border-hairline bg-surface-card text-muted hover:text-ink hover:border-ink transition-colors cursor-pointer"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-slate-700" />
          )}
        </button>

        {/* Profile Button */}
        <button
          onClick={() => setShowDropdown((prev) => !prev)}
          className="flex items-center gap-2 p-1.5 rounded-md hover:bg-surface-soft transition-colors cursor-pointer group"
        >
          <div className="w-8 h-8 rounded-full bg-primary-light/80 border border-primary/30 text-primary font-semibold text-xs flex items-center justify-center shadow-xs">
            {isAuthenticated && user ? (
              user.display_name ? user.display_name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()
            ) : (
              <User className="w-4 h-4 text-muted" />
            )}
          </div>

          <div className="hidden sm:flex items-center gap-1 text-left">
            <span className="text-xs font-semibold text-ink group-hover:text-primary">
              {isAuthenticated && user ? user.display_name || user.email.split('@')[0] : 'Guest User'}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-muted" />
          </div>
        </button>

        {/* Dropdown Menu */}
        {showDropdown && (
          <div className="absolute right-0 top-12 w-56 rounded-xl border border-hairline bg-surface-card shadow-lg p-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
            {/* Header info */}
            <div className="px-3 py-2 border-b border-hairline mb-1">
              <p className="text-caption font-semibold text-ink truncate">
                {isAuthenticated && user ? user.display_name || user.email : 'Guest Session'}
              </p>
              <p className="text-[11px] text-muted truncate">
                {isAuthenticated && user ? user.email : 'Running locally'}
              </p>
            </div>

            {/* Menu Items */}
            {isAuthenticated ? (
              <>
                <button
                  onClick={() => handleNavClick('My Datasets')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-body-sm text-ink hover:bg-primary-light/50 hover:text-primary transition-colors text-left cursor-pointer"
                >
                  <FolderClock className="w-4 h-4" />
                  <span>My Datasets</span>
                </button>

                <button
                  onClick={() => handleNavClick('Settings')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-body-sm text-ink hover:bg-primary-light/50 hover:text-primary transition-colors text-left cursor-pointer"
                >
                  <Settings className="w-4 h-4" />
                  <span>Settings</span>
                </button>

                <div className="my-1 border-t border-hairline" />

                <button
                  onClick={() => {
                    setShowDropdown(false);
                    logout();
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-body-sm text-error hover:bg-error-bg/60 transition-colors text-left cursor-pointer"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Log Out</span>
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => handleNavClick('Login')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-body-sm text-ink hover:bg-primary-light/50 hover:text-primary transition-colors text-left cursor-pointer"
                >
                  <LogIn className="w-4 h-4 text-primary" />
                  <span>Log In</span>
                </button>

                <button
                  onClick={() => handleNavClick('Signup')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-body-sm text-ink hover:bg-primary-light/50 hover:text-primary transition-colors text-left cursor-pointer"
                >
                  <UserPlus className="w-4 h-4 text-primary" />
                  <span>Create Account</span>
                </button>

                <button
                  onClick={() => handleNavClick('Settings')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-body-sm text-ink hover:bg-primary-light/50 hover:text-primary transition-colors text-left cursor-pointer"
                >
                  <Settings className="w-4 h-4" />
                  <span>Settings</span>
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </header>
  );
};
