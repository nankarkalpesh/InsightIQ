import React, { useState } from 'react';
import { LogIn, Mail, Lock, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../../store/authStore';
import { BrandLogo } from '../../components/icons/BrandLogo';
import { ApiError } from '../../lib/api';

interface LoginScreenProps {
  onSwitchToSignup: () => void;
  onSuccessNavigate?: () => void;
  onContinueAsGuest?: () => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({
  onSwitchToSignup,
  onSuccessNavigate,
  onContinueAsGuest
}) => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setErrorMsg('Please enter both email and password.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      await login(email, password);
      if (onSuccessNavigate) {
        onSuccessNavigate();
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg(err?.message || 'Failed to log in. Please check your credentials.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto py-8 px-4">
      <div className="rounded-2xl border border-hairline bg-surface-card p-6 md:p-8 shadow-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex p-3 rounded-2xl bg-primary-light/60 border border-primary/20 mb-3">
            <BrandLogo size={40} />
          </div>
          <h1 className="text-display-xs font-bold text-ink tracking-tight mb-1">
            Welcome back to InsightIQ
          </h1>
          <p className="text-body-sm text-muted">
            Log in to access your saved datasets, AI charts, and ML runs.
          </p>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div className="mb-6 p-3.5 rounded-xl bg-error-bg/60 border border-error/30 text-error text-body-sm font-medium flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="flex-1">{errorMsg}</div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-caption font-semibold text-ink mb-1.5">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-muted absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                required
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-hairline bg-canvas text-ink text-body-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-caption font-semibold text-ink mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-muted absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-hairline bg-canvas text-ink text-body-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 btn-primary py-3 justify-center text-body-sm font-semibold gap-2 disabled:opacity-50 cursor-pointer"
          >
            {isSubmitting ? (
              <span>Logging in...</span>
            ) : (
              <>
                <LogIn className="w-4 h-4" />
                <span>Log In to Account</span>
              </>
            )}
          </button>
        </form>

        {/* Switcher & Guest Link */}
        <div className="mt-6 pt-6 border-t border-hairline text-center space-y-3">
          <p className="text-body-sm text-muted">
            Don't have an account yet?{' '}
            <button
              onClick={onSwitchToSignup}
              className="text-primary font-semibold hover:underline underline-offset-2 cursor-pointer"
            >
              Sign Up
            </button>
          </p>

          {onContinueAsGuest && (
            <button
              onClick={onContinueAsGuest}
              className="inline-flex items-center gap-1.5 text-caption font-medium text-muted hover:text-ink transition-colors cursor-pointer"
            >
              <span>Continue as Guest</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
