// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

"use client";

import { Component, ReactNode } from "react";

export interface ErrorBoundaryLabels {
  title: string;
  message: string;
  retry: string;
}

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  labels?: ErrorBoundaryLabels;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary] Uncaught error:", error, info.componentStack);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      const { labels } = this.props;
      return (
        <div className="flex flex-col items-center justify-center h-full gap-4 p-8 text-center">
          <h2 className="text-lg font-semibold text-red-400">
            {labels?.title ?? "Something went wrong"}
          </h2>
          <p className="text-sm text-gray-400 max-w-md">
            {this.state.error?.message ?? labels?.message ?? "An unexpected error occurred."}
          </p>
          <button
            onClick={this.handleReset}
            className="px-4 py-2 text-sm rounded bg-athena-accent text-white hover:opacity-90 transition-opacity"
          >
            {labels?.retry ?? "Try again"}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
