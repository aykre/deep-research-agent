import { useState } from "react";
import Markdown from "react-markdown";

interface ResearchResultProps {
  response: string;
}

export function ResearchResult({ response }: ResearchResultProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(response);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.error("Failed to copy to clipboard");
    }
  };

  return (
    <div
      className="w-full rounded-xl border overflow-hidden"
      style={{
        background: 'var(--bg-secondary)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-3 border-b"
        style={{ borderColor: 'var(--border-subtle)' }}
      >
        <div className="flex items-center gap-2">
          <div
            className="w-6 h-6 rounded-md flex items-center justify-center"
            style={{ background: 'rgba(34, 197, 94, 0.15)' }}
          >
            <svg
              className="w-3.5 h-3.5"
              style={{ color: 'var(--accent-success)' }}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3
            className="text-sm font-semibold"
            style={{ color: 'var(--text-primary)' }}
          >
            Research Result
          </h3>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200"
          style={{
            background: copied ? 'rgba(34, 197, 94, 0.15)' : 'var(--bg-tertiary)',
            color: copied ? '#4ade80' : 'var(--text-secondary)',
            border: `1px solid ${copied ? 'rgba(34, 197, 94, 0.3)' : 'var(--border-subtle)'}`,
          }}
        >
          {copied ? (
            <>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Copied
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Copy
            </>
          )}
        </button>
      </div>

      {/* Content */}
      <div
        className="p-5 prose prose-sm max-w-none prose-custom"
        style={{ color: 'var(--text-primary)' }}
      >
        <Markdown
          components={{
            a: ({ ...props }) => (
              <a
                {...props}
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors duration-200"
                style={{
                  color: '#818cf8',
                  textDecoration: 'none',
                }}
                onMouseEnter={(e) => {
                  (e.target as HTMLElement).style.textDecoration = 'underline';
                }}
                onMouseLeave={(e) => {
                  (e.target as HTMLElement).style.textDecoration = 'none';
                }}
              />
            ),
            h1: ({ ...props }) => (
              <h1
                {...props}
                className="text-xl font-bold mt-6 mb-3 pb-2 border-b"
                style={{
                  color: 'var(--text-primary)',
                  borderColor: 'var(--border-subtle)',
                }}
              />
            ),
            h2: ({ ...props }) => (
              <h2
                {...props}
                className="text-lg font-semibold mt-5 mb-2"
                style={{ color: 'var(--text-primary)' }}
              />
            ),
            h3: ({ ...props }) => (
              <h3
                {...props}
                className="text-base font-semibold mt-4 mb-2"
                style={{ color: 'var(--text-primary)' }}
              />
            ),
            p: ({ ...props }) => (
              <p
                {...props}
                className="my-3 leading-relaxed"
                style={{ color: 'var(--text-secondary)' }}
              />
            ),
            ul: ({ ...props }) => (
              <ul
                {...props}
                className="my-3 pl-5 space-y-1"
                style={{ color: 'var(--text-secondary)' }}
              />
            ),
            ol: ({ ...props }) => (
              <ol
                {...props}
                className="my-3 pl-5 space-y-1"
                style={{ color: 'var(--text-secondary)' }}
              />
            ),
            li: ({ ...props }) => (
              <li
                {...props}
                className="leading-relaxed"
                style={{ color: 'var(--text-secondary)' }}
              />
            ),
            code: ({ className, children, ...props }) => {
              const isInline = !className;
              if (isInline) {
                return (
                  <code
                    {...props}
                    className="px-1.5 py-0.5 rounded text-sm font-mono"
                    style={{
                      background: 'var(--bg-tertiary)',
                      color: '#c4b5fd',
                    }}
                  >
                    {children}
                  </code>
                );
              }
              return (
                <code {...props} className={className}>
                  {children}
                </code>
              );
            },
            pre: ({ ...props }) => (
              <pre
                {...props}
                className="my-4 p-4 rounded-lg overflow-x-auto text-sm"
                style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-subtle)',
                }}
              />
            ),
            blockquote: ({ ...props }) => (
              <blockquote
                {...props}
                className="my-4 pl-4 border-l-2 italic"
                style={{
                  borderColor: 'var(--accent-primary)',
                  color: 'var(--text-muted)',
                }}
              />
            ),
            strong: ({ ...props }) => (
              <strong
                {...props}
                className="font-semibold"
                style={{ color: 'var(--text-primary)' }}
              />
            ),
            hr: ({ ...props }) => (
              <hr
                {...props}
                className="my-6"
                style={{ borderColor: 'var(--border-subtle)' }}
              />
            ),
          }}
        >
          {response}
        </Markdown>
      </div>
    </div>
  );
}
