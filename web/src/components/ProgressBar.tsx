interface ProgressBarProps {
  currentStep: number;
  totalSteps: number;
}

export function ProgressBar({ currentStep, totalSteps }: ProgressBarProps) {
  if (totalSteps === 0) {
    return null;
  }

  // Show at least a small amount of progress when started (currentStep=0)
  const percentage = currentStep === 0 ? 5 : Math.min((currentStep / totalSteps) * 100, 100);
  const isComplete = currentStep >= totalSteps;

  return (
    <div
      className="w-full rounded-xl border p-4"
      style={{
        background: 'var(--bg-secondary)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span
            className="text-sm font-medium"
            style={{ color: 'var(--text-primary)' }}
          >
            Research Progress
          </span>
          <span
            className="text-xs font-mono px-2 py-1 rounded"
            style={{
              background: 'var(--bg-tertiary)',
              color: 'var(--text-secondary)',
            }}
          >
            {currentStep} / {totalSteps}
          </span>
        </div>
        <div
          className="w-full h-2 rounded-full overflow-hidden"
          style={{ background: 'var(--bg-tertiary)' }}
        >
          <div
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{
              width: `${percentage}%`,
              background: isComplete
                ? 'var(--accent-success)'
                : 'linear-gradient(90deg, var(--accent-primary) 0%, #8b5cf6 100%)',
            }}
          />
        </div>
        <div className="flex justify-between items-center">
          <span
            className="text-xs"
            style={{ color: 'var(--text-muted)' }}
          >
            {isComplete ? 'Complete' : 'In progress...'}
          </span>
          <span
            className="text-xs font-medium"
            style={{ color: isComplete ? 'var(--accent-success)' : 'var(--accent-primary)' }}
          >
            {Math.round(percentage)}%
          </span>
        </div>
      </div>
    </div>
  );
}
