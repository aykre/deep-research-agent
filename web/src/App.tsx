import { useEffect, useRef, useCallback, useState } from "react";
import Turnstile, { type BoundTurnstileObject } from "react-turnstile";
import { USE_TURNSTILE, TURNSTILE_SITE_KEY } from './config';
import { useResearchSocket } from "./hooks/useResearchSocket";
import { ResearchInput } from "./components/ResearchInput";
import { ResearchResult } from "./components/ResearchResult";
import { ProgressBar } from "./components/ProgressBar";
import { StageIndicator } from "./components/StageIndicator";

function App() {
  const turnstileRef = useRef<BoundTurnstileObject>(null);
  const stagesRef = useRef<HTMLDivElement>(null);
  const [isTurnstileVerified, setIsTurnstileVerified] = useState(false);

  const handleTokenRefresh = useCallback(() => {
    console.log('handleTokenRefresh called, turnstileRef.current:', turnstileRef.current);
    setIsTurnstileVerified(false); // Show Turnstile again when resetting
    if (turnstileRef.current?.reset) {
      console.log('Calling turnstile reset');
      turnstileRef.current.reset();
    } else {
      console.warn('Turnstile ref not available or no reset method');
    }
  }, []);

  const {
    connectionState,
    researchState,
    stages,
    response,
    error,
    currentStep,
    totalSteps,
    stoppedWithData,
    startResearch,
    stopResearch,
    setTurnstileToken,
  } = useResearchSocket({ onNeedTokenRefresh: handleTokenRefresh });

  useEffect(() => {
    const container = stagesRef.current;
    if (!container) return;

    container.scrollTop = container.scrollHeight;
  }, [stages]);

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-primary)' }}>
      {/* Subtle gradient overlay */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at 50% 0%, rgba(99, 102, 241, 0.08) 0%, transparent 50%)',
        }}
      />

      <div className="relative z-10 container mx-auto px-4 py-12 max-w-3xl">
        {/* Header */}
        <header className="text-center mb-12">
          {/* GitHub Icon */}
          <div className="absolute top-4 right-4">
            <a
              href="https://github.com/aykre/deep-research-agent"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center w-10 h-10 rounded-lg transition-all duration-200 hover:scale-110"
              aria-label="View on GitHub"
            >
              <svg className="w-6 h-6" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 98 96" aria-labelledby="github">
                <title id="github">Github</title>
                <path clipRule="evenodd" d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.59 2.934-16.42-5.867-16.42-5.867-2.184-5.704-5.42-7.17-5.42-7.17-4.448-3.015.324-3.015.324-3.015 4.934.326 7.523 5.052 7.523 5.052 4.367 7.496 11.404 5.378 14.235 4.074.404-3.178 1.699-5.378 3.074-6.6-10.839-1.141-22.243-5.378-22.243-24.283 0-5.378 1.94-9.778 5.014-13.2-.485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1 12.214-1.63c4.125 0 8.33.571 12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2.67 6.763.97 11.816.485 13.038 3.155 3.422 5.015 7.822 5.015 13.2 0 18.905-11.404 23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526 0 1.304.89 2.853 3.316 2.364 19.412-6.52 33.405-24.935 33.405-46.691C97.707 22 75.788 0 48.854 0z" fill="currentColor" />
              </svg>
            </a>
          </div>

          <div className="inline-flex items-center gap-3 mb-4">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, var(--accent-primary) 0%, #8b5cf6 100%)' }}
            >
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h1
              className="text-3xl font-bold tracking-tight"
              style={{ color: 'var(--text-primary)' }}
            >
              Deep Research
            </h1>
          </div>
          <p style={{ color: 'var(--text-secondary)' }} className="text-sm">
            AI-powered research assistant
          </p>
        </header>

        {/* Main Content */}
        <main className="space-y-6">
          <ResearchInput
            connectionState={connectionState}
            researchState={researchState}
            onStartResearch={startResearch}
            onStopResearch={stopResearch}
          />

          {USE_TURNSTILE && (
            <div className={`flex justify-center ${isTurnstileVerified ? 'hidden' : ''}`}>
              <Turnstile
                sitekey={TURNSTILE_SITE_KEY}
                onVerify={(token) => {
                  setTurnstileToken(token);
                  setIsTurnstileVerified(true); // Hide Turnstile after successful verification
                }}
                onLoad={(_widgetId, boundTurnstile) => {
                  console.log('Turnstile onLoad, boundTurnstile:', boundTurnstile);
                  turnstileRef.current = boundTurnstile;
                }}
                theme="dark"
              />
            </div>
          )}

          {error && (
            <div
              className="rounded-xl p-4 border"
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                borderColor: 'rgba(239, 68, 68, 0.3)'
              }}
            >
              <div className="flex items-start gap-3">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: 'rgba(239, 68, 68, 0.2)' }}
                >
                  <svg className="w-4 h-4" style={{ color: 'var(--accent-error)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm mb-1" style={{ color: '#fca5a5' }}>
                    Error
                  </div>
                  <div className="text-sm" style={{ color: '#fecaca' }}>
                    {error}
                  </div>
                </div>
              </div>
            </div>
          )}

          {(researchState === "researching" || researchState === "complete") && totalSteps > 0 && (
            <ProgressBar currentStep={currentStep} totalSteps={totalSteps} />
          )}

          {stages.length > 0 && (
            <div
              className="rounded-xl border p-5"
              style={{
                background: 'var(--bg-secondary)',
                borderColor: 'var(--border-subtle)'
              }}
            >
              <h3
                className="text-sm font-semibold uppercase tracking-wider mb-4"
                style={{ color: 'var(--text-secondary)' }}
              >
                Research Stages
              </h3>
              <div
                ref={stagesRef}
                className="space-y-2 max-h-80 overflow-y-auto pr-2"
              >
                {stages.map((stage) => (
                  <StageIndicator key={stage.id} stage={stage} />
                ))}
              </div>
            </div>
          )}

          {response && <ResearchResult response={response} />}

          {researchState === "stopped" && !response && stoppedWithData && (
            <div
              className="rounded-xl p-4 border"
              style={{
                background: 'rgba(245, 158, 11, 0.1)',
                borderColor: 'rgba(245, 158, 11, 0.3)'
              }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: 'rgba(245, 158, 11, 0.2)' }}
                >
                  <svg className="w-4 h-4 animate-spin" style={{ color: 'var(--accent-warning)' }} fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
                <span className="text-sm" style={{ color: '#fcd34d' }}>
                  Research stopped early. Generating response with available data...
                </span>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
