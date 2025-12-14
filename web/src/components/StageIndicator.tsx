import type { Stage } from "../types";

interface StageIndicatorProps {
  stage: Stage;
}

export function StageIndicator({ stage }: StageIndicatorProps) {
  const getIcon = () => {
    switch (stage.status) {
      case "in_progress":
        return (
          <svg
            className="animate-spin h-4 w-4"
            style={{ color: 'var(--accent-primary)' }}
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        );
      case "completed":
        return (
          <svg
            className="h-4 w-4"
            style={{ color: 'var(--accent-success)' }}
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
        );
      case "failed":
        return (
          <svg
            className="h-4 w-4"
            style={{ color: 'var(--accent-error)' }}
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        );
      case "pending":
        return (
          <svg
            className="h-4 w-4"
            style={{ color: 'var(--text-muted)' }}
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <circle cx="10" cy="10" r="6" />
          </svg>
        );
    }
  };

  const getStyles = () => {
    switch (stage.status) {
      case "in_progress":
        return {
          background: 'rgba(99, 102, 241, 0.1)',
          borderColor: 'rgba(99, 102, 241, 0.3)',
          textColor: '#a5b4fc',
        };
      case "completed":
        return {
          background: 'rgba(34, 197, 94, 0.1)',
          borderColor: 'rgba(34, 197, 94, 0.2)',
          textColor: '#86efac',
        };
      case "failed":
        return {
          background: 'rgba(239, 68, 68, 0.1)',
          borderColor: 'rgba(239, 68, 68, 0.3)',
          textColor: '#fca5a5',
        };
      case "pending":
        return {
          background: 'var(--bg-tertiary)',
          borderColor: 'var(--border-subtle)',
          textColor: 'var(--text-muted)',
        };
    }
  };

  const styles = getStyles();

  return (
    <div
      className="flex items-center gap-3 text-sm px-3 py-2.5 rounded-lg border"
      style={{
        background: styles.background,
        borderColor: styles.borderColor,
      }}
    >
      <span className="flex-shrink-0">{getIcon()}</span>
      <span
        className="truncate flex-1"
        style={{ color: styles.textColor }}
      >
        {stage.title}
      </span>
      {stage.error && (
        <span
          className="ml-auto text-xs truncate max-w-[200px] px-2 py-0.5 rounded"
          style={{
            background: 'rgba(239, 68, 68, 0.15)',
            color: '#fca5a5',
          }}
        >
          {stage.error}
        </span>
      )}
    </div>
  );
}
