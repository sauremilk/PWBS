"use client";

import { Component, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-red-400" />
          <h3 className="mb-1 text-sm font-semibold text-red-900">
            Unerwarteter Fehler
          </h3>
          <p className="text-sm text-red-700">
            {this.state.error?.message ?? "Etwas ist schiefgelaufen."}
          </p>
          <button
            onClick={this.handleRetry}
            className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
          >
            <RefreshCw className="h-4 w-4" />
            Erneut versuchen
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
