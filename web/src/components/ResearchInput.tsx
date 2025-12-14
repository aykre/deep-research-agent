import { useState } from "react";
import type { ConnectionState, ResearchState } from "../types";

interface ResearchInputProps {
  connectionState: ConnectionState;
  researchState: ResearchState;
  onStartResearch: (query: string) => void;
  onStopResearch: () => void;
}

export function ResearchInput({
  connectionState,
  researchState,
  onStartResearch,
  onStopResearch,
}: ResearchInputProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onStartResearch(query.trim());
    }
  };

  const isResearching = researchState === "researching";
  const isConnecting = connectionState === "connecting";

  return (
    <div className="w-full">
      <div className="mb-3 flex items-center justify-center">
        {connectionState === "connected" && (
          <span
            className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-full"
            style={{
              background: 'rgba(34, 197, 94, 0.1)',
              color: '#4ade80',
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: 'var(--accent-success)' }}
            />
            Connected
          </span>
        )}
        {connectionState === "connecting" && (
          <span
            className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-full"
            style={{
              background: 'rgba(245, 158, 11, 0.1)',
              color: '#fbbf24',
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full animate-pulse"
              style={{ background: 'var(--accent-warning)' }}
            />
            Connecting...
          </span>
        )}
        {connectionState === "disconnected" && (
          <span
            className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-full"
            style={{
              background: 'rgba(96, 96, 112, 0.1)',
              color: 'var(--text-muted)',
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: 'var(--text-muted)' }}
            />
            Disconnected
          </span>
        )}
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div
          className="rounded-xl border p-1.5 transition-all duration-200"
          style={{
            background: 'var(--bg-secondary)',
            borderColor: 'var(--border-subtle)',
          }}
        >
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter research query"
              className="flex-1 px-4 py-3 bg-transparent border-0 outline-none text-sm placeholder-opacity-50"
              style={{
                color: 'var(--text-primary)',
              }}
              disabled={isResearching}
            />

            {isResearching ? (
              <button
                type="button"
                onClick={onStopResearch}
                className="px-5 py-2.5 rounded-lg font-medium text-sm hover:opacity-75 transition-opacity transform transition-transform duration-150 active:scale-105 flex items-center gap-2"
                style={{
                  background: 'rgba(239, 68, 68, 0.15)',
                  color: '#f87171',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                }}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
                Stop
              </button>
            ) : (
              <button
                type="submit"
                className="px-5 py-2.5 rounded-lg font-medium text-sm hover:opacity-75 transition-opacity transform transition-transform duration-150 active:scale-105 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
                style={{
                  background: 'linear-gradient(135deg, var(--accent-primary) 0%, #8b5cf6 100%)',
                  color: 'white',
                }}
                disabled={!query.trim() || isConnecting}
              >
                {isConnecting ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Connecting
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    Research
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
