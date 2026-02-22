"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { PipelineProgress } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useSSE(jobId: number | null) {
  const [progress, setProgress] = useState<PipelineProgress | null>(null);
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (!jobId) return;

    const es = new EventSource(`${API_BASE}/api/jobs/${jobId}/stream`);
    eventSourceRef.current = es;

    es.onopen = () => setConnected(true);

    es.onmessage = (event) => {
      try {
        const data: PipelineProgress = JSON.parse(event.data);
        setProgress(data);

        if (data.status === "completed" || data.status === "failed") {
          es.close();
          setConnected(false);
        }
      } catch {
        // ignore invalid JSON (keepalive pings)
      }
    };

    es.onerror = () => {
      es.close();
      setConnected(false);
    };
  }, [jobId]);

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
      setConnected(false);
    };
  }, [connect]);

  return { progress, connected };
}
