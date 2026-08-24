import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled render error caught by ErrorBoundary:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="p-8 my-6 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-ink space-y-4 max-w-2xl mx-auto shadow-xs">
          <div className="flex items-center gap-3 text-amber-600 dark:text-amber-400 font-bold text-lg">
            <AlertTriangle className="w-6 h-6 shrink-0 text-amber-500" />
            <span>Something went wrong while displaying this section</span>
          </div>

          <p className="text-body-sm text-muted">
            {this.state.error?.message || 'An unexpected rendering error occurred.'}
          </p>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={this.handleReset}
              className="px-4 py-2 rounded-xl bg-primary text-white font-semibold text-sm hover:bg-primary/90 transition-colors flex items-center gap-2 cursor-pointer shadow-xs"
            >
              <RefreshCw className="w-4 h-4" />
              Try Displaying Again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-xl bg-surface-card border border-hairline text-ink font-semibold text-sm hover:bg-surface-hover transition-colors cursor-pointer"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
