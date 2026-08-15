import React, { useState, useRef, useEffect } from 'react';
import {
  LayoutDashboard,
  BarChart3,
  FlaskConical,
  MessageSquareCode,
  FolderClock,
  Settings,
  X,
  User,
  ShieldCheck,
  ChevronUp,
  LogOut,
  LogIn,
  UserPlus
} from 'lucide-react';
import { BrandLogo } from '../icons/BrandLogo';
import { useAuth } from '../../store/authStore';

export type NavItemKey =
  | 'Overview'
  | 'Analytics'
  | 'Data Science'
  | 'Data Chat'
  | 'My Datasets'
  | 'Settings'
  | 'Login'
  | 'Signup';

export interface NavItem {
  key: NavItemKey;
  label: string;
  icon: React.ElementType;
}

const BASE_NAV_ITEMS: NavItem[] = [
  { key: 'Overview', label: 'Overview', icon: LayoutDashboard },
  { key: 'Analytics', label: 'Analytics', icon: BarChart3 },
  { key: 'Data Science', label: 'Data Science', icon: FlaskConical },
  { key: 'Data Chat', label: 'Data Chat', icon: MessageSquareCode },
];

interface SidebarProps {
  activeItem: NavItemKey;
  onSelectNavItem: (item: NavItemKey) => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeItem,
  onSelectNavItem,
  isMobileOpen,
  onCloseMobile,
}) => {
  const { user, isAuthenticated, logout } = useAuth();
  const [showGuestPopover, setShowGuestPopover] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Close popover on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setShowGuestPopover(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const navItems: NavItem[] = [
    ...BASE_NAV_ITEMS,
    ...(isAuthenticated ? [{ key: 'My Datasets' as NavItemKey, label: 'My Datasets', icon: FolderClock }] : []),
    { key: 'Settings', label: 'Settings', icon: Settings },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-ink/30 z-40 md:hidden backdrop-blur-xs transition-opacity"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar Drawer / Fixed sidebar */}
      <aside
        className={`
          fixed md:static inset-y-0 left-0 z-50
          w-[240px] md:w-[240px] shrink-0
          bg-sidebar border-r border-sidebar-border text-sidebar-text
          flex flex-col justify-between
          transition-transform duration-300 ease-in-out
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        {/* Brand / Header */}
        <div className="h-16 px-6 flex items-center justify-between border-b border-sidebar-border shrink-0">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => onSelectNavItem('Overview')}>
            <BrandLogo size={32} />
            <span className="font-semibold text-xl tracking-tight text-sidebar-text">
              InsightIQ
            </span>
          </div>

          {/* Mobile Close Button */}
          <button
            onClick={onCloseMobile}
            className="md:hidden p-1.5 rounded-md text-sidebar-text hover:bg-sidebar-hover transition-colors"
            aria-label="Close Navigation"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeItem === item.key;
            return (
              <button
                key={item.key}
                onClick={() => {
                  onSelectNavItem(item.key);
                  onCloseMobile();
                }}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-body-sm font-medium
                  transition-all duration-150 cursor-pointer
                  ${isActive
                    ? 'bg-sidebar-active-bg text-sidebar-active-text shadow-xs font-semibold'
                    : 'hover:bg-sidebar-hover hover:text-sidebar-active-text text-sidebar-text/90'
                  }
                `}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-primary' : 'opacity-70'}`} />
                <span className="truncate">{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Profile Footer & Popover */}
        <div className="p-3 border-t border-sidebar-border shrink-0 relative" ref={popoverRef}>
          {/* Popover Card */}
          {showGuestPopover && (
            <div className="absolute bottom-16 left-3 right-3 p-3.5 rounded-xl border border-hairline bg-surface-card shadow-xl text-ink space-y-2.5 animate-in fade-in slide-in-from-bottom-2 duration-150 z-50">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-0.5 rounded-full bg-success/15 text-success border border-success/30">
                  <ShieldCheck className="w-3 h-3" />
                  <span>{isAuthenticated ? 'Authenticated' : 'Guest Mode'}</span>
                </span>
                <button
                  onClick={() => setShowGuestPopover(false)}
                  className="text-muted hover:text-ink text-xs p-1"
                >
                  ✕
                </button>
              </div>

              <div>
                <p className="text-body-sm font-semibold text-ink truncate">
                  {isAuthenticated && user ? user.display_name || user.email : 'Guest Session'}
                </p>
                <p className="text-caption text-muted truncate">
                  {isAuthenticated && user ? user.email : 'Running locally — no account required.'}
                </p>
              </div>

              <div className="pt-2 border-t border-hairline space-y-1.5">
                {isAuthenticated ? (
                  <>
                    <button
                      onClick={() => {
                        setShowGuestPopover(false);
                        onSelectNavItem('My Datasets');
                      }}
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-caption font-semibold bg-primary-light/50 text-primary hover:bg-primary-light transition-colors flex items-center justify-between cursor-pointer"
                    >
                      <span>My Datasets</span>
                      <FolderClock className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => {
                        setShowGuestPopover(false);
                        logout();
                      }}
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-caption font-medium text-error hover:bg-error-bg/60 transition-colors flex items-center justify-between cursor-pointer"
                    >
                      <span>Log Out</span>
                      <LogOut className="w-3.5 h-3.5" />
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => {
                        setShowGuestPopover(false);
                        onSelectNavItem('Login');
                      }}
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-caption font-semibold bg-primary-light/50 text-primary hover:bg-primary-light transition-colors flex items-center justify-between cursor-pointer"
                    >
                      <span>Log In</span>
                      <LogIn className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => {
                        setShowGuestPopover(false);
                        onSelectNavItem('Signup');
                      }}
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-caption font-medium text-ink hover:bg-surface-soft transition-colors flex items-center justify-between cursor-pointer"
                    >
                      <span>Create Account</span>
                      <UserPlus className="w-3.5 h-3.5" />
                    </button>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Profile Trigger */}
          <button
            onClick={() => setShowGuestPopover((prev) => !prev)}
            className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-sidebar-hover transition-colors text-left group cursor-pointer"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-primary-light/80 border border-primary/30 text-primary font-semibold text-xs flex items-center justify-center shrink-0">
                {isAuthenticated && user ? (
                  user.display_name ? user.display_name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()
                ) : (
                  <User className="w-4 h-4 opacity-70" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-body-sm font-semibold text-sidebar-text truncate">
                  {isAuthenticated && user ? user.display_name || user.email.split('@')[0] : 'Guest User'}
                </p>
                <p className="text-caption text-sidebar-text/60 truncate">
                  {isAuthenticated ? 'Logged In' : 'Local Mode'}
                </p>
              </div>
            </div>
            <ChevronUp className={`w-4 h-4 text-sidebar-text/50 transition-transform duration-200 ${showGuestPopover ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </aside>
    </>
  );
};
