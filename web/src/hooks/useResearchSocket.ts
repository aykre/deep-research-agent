import { useState, useCallback, useRef, useEffect } from "react";
import type {
  ResearchEvent,
  ConnectionState,
  ResearchState,
  Stage,
  SearchAndFilterStartedData,
  SearchAndFilterCompletedData,
  SearchAndFilterFailed,
  ScrapeStartedData,
  ScrapeCompleteData,
  ExtractionStartedData,
  ExtractionCompleteData,
  RewriterStartedData,
  RewriterCompleteData,
  EarlyStopData,
  WritingStartedData,
  WritingCompleteData,
  StoppedData,
} from "../types";
import { USE_TURNSTILE } from "../config";

interface UseResearchSocketReturn {
  connectionState: ConnectionState;
  researchState: ResearchState;
  stages: Stage[];
  response: string | null;
  error: string | null;
  currentStep: number;
  totalSteps: number;
  stoppedWithData: boolean;
  turnstileToken: string;
  connect: () => void;
  disconnect: () => void;
  startResearch: (query: string) => void;
  stopResearch: () => void;
  setTurnstileToken: (token: string) => void;
}

export function useResearchSocket(options?: { onNeedTokenRefresh?: () => void }): UseResearchSocketReturn {
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [researchState, setResearchState] = useState<ResearchState>("idle");
  const [stages, setStages] = useState<Stage[]>([]);
  const [response, setResponse] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [totalSteps, setTotalSteps] = useState<number>(0);
  const [stoppedWithData, setStoppedWithData] = useState<boolean>(false);
  const [turnstileToken, setTurnstileToken] = useState<string>('');
  const turnstileTokenRef = useRef<string>('');
  const wsRef = useRef<WebSocket | null>(null);
  const researchStateRef = useRef<ResearchState>("idle");

  // Keep ref in sync with state
  useEffect(() => {
    researchStateRef.current = researchState;
  }, [researchState]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionState("connecting");
    setError(null);

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/research`;
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnectionState("connected");
    };

    ws.onclose = () => {
      console.log('WebSocket closed, USE_TURNSTILE:', USE_TURNSTILE, 'onNeedTokenRefresh:', options?.onNeedTokenRefresh);
      setConnectionState("disconnected");
      // Clear Turnstile token on connection loss
      setTurnstileToken("");
      turnstileTokenRef.current = "";
      // Use ref to get current value, not stale closure value
      if (researchStateRef.current === "researching") {
        setResearchState("error");
        setError("Lost connection to server");
        // Mark all in-progress stages as failed
        setStages((prev) =>
          prev.map((stage) =>
            stage.status === "in_progress"
              ? { ...stage, status: "failed" as const, error: "Connection lost" }
              : stage
          )
        );
      }
      // Reset Turnstile on disconnect to get fresh token on reconnect
      // Defer to avoid interfering with other state updates
      if (USE_TURNSTILE) {
        console.log('Calling onNeedTokenRefresh');
        setTimeout(() => {
          options?.onNeedTokenRefresh?.();
        }, 0);
      }
    };

    ws.onerror = () => {
      // Use ref to get current value, not stale closure value
      if (researchStateRef.current === "researching") {
        setError("Lost connection to server");
      } else {
        setError("WebSocket connection error");
      }
      setConnectionState("disconnected");
    };

    ws.onmessage = (event) => {
      try {
        const data: ResearchEvent = JSON.parse(event.data);

        // Handle specific event types
        switch (data.type) {
          case "guardrail_started": {
            const eventData = data.data as { stage_id: string };
            setStages((prev) => {
              // Complete the initializing stage and add the new stage
              const updatedStages = prev.map((stage) =>
                stage.id === "initializing"
                  ? { ...stage, status: "completed" as const, title: "Research started" }
                  : stage
              );
              return [
                ...updatedStages,
                {
                  id: eventData.stage_id,
                  type: "guardrail" as const,
                  status: "in_progress" as const,
                  title: "Checking query safety...",
                },
              ];
            });
            break;
          }
          case "guardrail_complete": {
            const eventData = data.data as {
              stage_id: string;
              is_acceptable: boolean;
              reason: string;
              confidence: number;
            };
            setStages((prev) =>
              prev.map((stage) =>
                stage.id === eventData.stage_id
                  ? {
                      ...stage,
                      status: "completed" as const,
                      title: eventData.is_acceptable
                        ? "Query approved"
                        : "Query rejected",
                    }
                  : stage
              )
            );
            break;
          }
          case "guardrail_rejected": {
            const eventData = data.data as { reason: string; confidence: number };
            setResearchState("error");
            setError(
              `This request cannot be completed: ${eventData.reason}`
            );
            break;
          }
          case "search_and_filter_started": {
            const eventData = data.data as unknown as SearchAndFilterStartedData;
            setStages((prev) => {
              // Complete the initializing stage and add the new stage
              const updatedStages = prev.map((stage) =>
                stage.id === "initializing"
                  ? { ...stage, status: "completed" as const, title: "Research started" }
                  : stage
              );
              return [
                ...updatedStages,
                {
                  id: eventData.stage_id,
                  type: "search_and_filter" as const,
                  status: "in_progress" as const,
                  title: `Search & Filter: ${eventData.query}`,
                },
              ];
            });
            break;
          }
          case "search_and_filter_completed": {
            const eventData = data.data as unknown as SearchAndFilterCompletedData;
            setStages((prev) =>
              prev.map((stage) =>
                stage.id === eventData.stage_id
                  ? { ...stage, status: "completed" as const }
                  : stage
              )
            );
            break;
          }
          case "search_and_filter_failed": {
            const eventData = data.data as unknown as SearchAndFilterFailed;
            setStages((prev) =>
              prev.map((stage) =>
                stage.id === eventData.stage_id
                  ? { ...stage, status: "failed" as const, error: eventData.error }
                  : stage
              )
            );
            break;
          }
          case "scrape_started": {
            const eventData = data.data as unknown as ScrapeStartedData;
            setStages((prev) => [
              ...prev,
              {
                id: eventData.stage_id,
                type: "scrape",
                status: "in_progress",
                title: `Scrape: ${eventData.title}`,
              },
            ]);
            break;
          }
          case "scrape_complete": {
            const eventData = data.data as unknown as ScrapeCompleteData;
            setStages((prev) =>
              prev.map((stage) =>
                stage.id === eventData.stage_id
                  ? {
                      ...stage,
                      status: eventData.success ? ("completed" as const) : ("failed" as const),
                      error: eventData.error,
                    }
                  : stage
              )
            );
            break;
          }
          case "extraction_started": {
            const eventData = data.data as unknown as ExtractionStartedData;
            setStages((prev) => [
              ...prev,
              {
                id: eventData.stage_id,
                type: "extraction",
                status: "in_progress",
                title: `Extract: ${eventData.url}`,
              },
            ]);
            break;
          }
          case "extraction_complete": {
            const eventData = data.data as unknown as ExtractionCompleteData;
            setStages((prev) =>
              prev.map((stage) =>
                stage.id === eventData.stage_id
                  ? {
                      ...stage,
                      status: eventData.error ? ("failed" as const) : ("completed" as const),
                      title: `Extract: ${eventData.title}`,
                      error: eventData.error,
                    }
                  : stage
              )
            );
            break;
          }
          case "rewriter_started": {
            const eventData = data.data as unknown as RewriterStartedData;
            setStages((prev) => [
              ...prev,
              {
                id: eventData.stage_id,
                type: "rewriter",
                status: "in_progress",
                title: "Generating follow-up queries...",
              },
            ]);
            break;
          }
          case "rewriter_complete": {
            const eventData = data.data as unknown as RewriterCompleteData;
            const title = eventData.action === "stop"
              ? "Research coverage complete"
              : `Generated ${eventData.queries_count} new ${eventData.queries_count === 1 ? 'query' : 'queries'}`;
            setStages((prev) =>
              prev.map((stage) =>
                stage.id === eventData.stage_id
                  ? { ...stage, status: "completed" as const, title }
                  : stage
              )
            );
            break;
          }
          case "writing_started": {
            const eventData = data.data as unknown as WritingStartedData;
            setStages((prev) => [
              ...prev,
              {
                id: eventData.stage_id,
                type: "writing",
                status: "in_progress",
                title: "Generating response...",
              },
            ]);
            break;
          }
          case "writing_complete": {
            const eventData = data.data as unknown as WritingCompleteData;
            setStages((prev) =>
              prev.map((stage) =>
                stage.id === eventData.stage_id
                  ? { ...stage, status: "completed" as const, title: "Response generated" }
                  : stage
              )
            );
            break;
          }
          case "early_stop": {
            const eventData = data.data as unknown as EarlyStopData;
            setStages((prev) => [
              ...prev,
              {
                id: eventData.stage_id,
                type: "early_stop",
                status: "completed",
                title: eventData.reason || "Sufficient coverage reached",
              },
            ]);
            break;
          }
          case "progress": {
            const progressData = data.data as { current_step: number; total_steps: number };
            console.log("Progress update:", progressData);
            setCurrentStep(progressData.current_step);
            setTotalSteps(progressData.total_steps);
            break;
          }
          case "complete":
            setResearchState("complete");
            setResponse((data.data as { response: string }).response);
            break;
          case "research_started":
            // Research successfully started - token was accepted
            // We don't need to do anything here, just acknowledge it
            break;
          case "stopped": {
            const stoppedData = data.data as unknown as StoppedData;
            setResearchState("stopped");
            setStoppedWithData(stoppedData.has_data);
            // Mark all in-progress stages as failed when stopped
            setStages((prev) =>
              prev.map((stage) =>
                stage.status === "in_progress"
                  ? { ...stage, status: "failed" as const, error: "Research stopped" }
                  : stage
              )
            );
            break;
          }
          case "error":
            setResearchState("error");
            setError((data.data as { message: string }).message);
            break;
        }
      } catch {
        console.error("Failed to parse WebSocket message");
      }
    };

    wsRef.current = ws;
  }, [options]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionState("disconnected");
  }, []);

  const startResearch = useCallback(
    (query: string) => {
      // Reset error state when starting new research
      setError(null);

      // Auto-connect if not connected
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
        // Reset research state before connecting
        setResearchState("idle");
        connect();

        // Wait for connection to open before starting research
        // eslint-disable-next-line prefer-const
        let connectionTimeout: ReturnType<typeof setTimeout>;
        const checkConnection = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            clearInterval(checkConnection);
            clearTimeout(connectionTimeout);

            // Reset state for new research
            setStages([
              {
                id: "initializing",
                type: "initializing",
                status: "in_progress",
                title: "Starting research...",
              },
            ]);
            setResponse(null);
            setError(null);
            setCurrentStep(0);
            setTotalSteps(0);
            setStoppedWithData(false);
            setResearchState("researching");
            const startObj: {
              action: string;
              query: string;
              turnstileToken?: string;
            } = {
                action: "start",
                query,
            };
            if (USE_TURNSTILE) {
                startObj.turnstileToken = turnstileTokenRef.current;
            }
            wsRef.current.send(
              JSON.stringify(startObj)
            );
          }
        }, 100);

        // Timeout after 5 seconds
        connectionTimeout = setTimeout(() => {
          clearInterval(checkConnection);
          if (wsRef.current?.readyState !== WebSocket.OPEN) {
            setError("Failed to connect to server");
            setResearchState("error");
          }
        }, 5000);
        return;
      }

      // Reset state for new research
      setStages([
        {
          id: "initializing",
          type: "initializing",
          status: "in_progress",
          title: "Starting research...",
        },
      ]);
      setResponse(null);
      setError(null);
      setCurrentStep(0);
      setTotalSteps(0);
      setStoppedWithData(false);
      setResearchState("researching");

      const startObj: {
        action: string;
        query: string;
        turnstileToken?: string;
      } = {
        action: "start",
        query,
      };
      if (USE_TURNSTILE) {
        startObj.turnstileToken = turnstileTokenRef.current;
      }
      wsRef.current.send(JSON.stringify(startObj));
    },
    [connect]
  );

  const stopResearch = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      return;
    }

    wsRef.current.send(JSON.stringify({ action: "stop" }));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Custom setter that updates both state and ref synchronously
  const setTurnstileTokenBoth = useCallback((token: string) => {
    setTurnstileToken(token);
    turnstileTokenRef.current = token;
  }, []);

  return {
    connectionState,
    researchState,
    stages,
    response,
    error,
    currentStep,
    totalSteps,
    stoppedWithData,
    turnstileToken,
    connect,
    disconnect,
    startResearch,
    stopResearch,
    setTurnstileToken: setTurnstileTokenBoth,
  };
}
