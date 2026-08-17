import { Component } from 'react';
import { useLocation } from 'react-router-dom';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Softorica render error:', error, errorInfo);
  }

  componentDidUpdate(prevProps) {
    if (this.props.resetKey !== prevProps.resetKey && this.state.hasError) {
      this.setState({ hasError: false, error: null });
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    const isDev = import.meta.env.DEV;
    const message = this.state.error?.message || 'Unknown error';

    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F7F1E9] px-4">
        <div className="w-full max-w-md rounded-xl border border-[#E6DDD2] bg-white p-8 text-center shadow-sm">
          <h1 className="text-2xl font-semibold text-[#1C1917]">Something went wrong</h1>
          <p className="mt-2 text-sm text-[#57534E]">Try refreshing the page.</p>
          {isDev && (
            <pre className="mt-4 max-h-40 overflow-auto rounded-md bg-[#F3EBE1] p-3 text-left text-xs text-[#B42318]">
              {message}
            </pre>
          )}
          <div className="mt-6 flex flex-col gap-2">
            <button
              type="button"
              onClick={this.handleRetry}
              className="rounded-md bg-[#556B2F] px-4 py-2.5 text-sm font-semibold text-[#FFDAB9]"
            >
              Try again
            </button>
            <button
              type="button"
              onClick={() => {
                window.location.href = '/';
              }}
              className="rounded-md border border-[#E6DDD2] px-4 py-2.5 text-sm font-semibold text-[#1C1917]"
            >
              Go home
            </button>
          </div>
        </div>
      </div>
    );
  }
}

export const AppErrorBoundary = ({ children }) => {
  const location = useLocation();
  return <ErrorBoundary resetKey={location.key}>{children}</ErrorBoundary>;
};

export default ErrorBoundary;
