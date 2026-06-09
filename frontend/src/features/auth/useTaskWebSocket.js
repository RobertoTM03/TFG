import { useEffect, useRef, useCallback } from "react";
import { getToken } from "@/shared/lib/storage";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8080";

export function useTaskWebSocket(taskId, onUpdate) {
  const wsRef = useRef(null);
  const onUpdateRef = useRef(onUpdate);
  useEffect(() => {
    onUpdateRef.current = onUpdate;
  });

  const connect = useCallback(() => {
    if (!taskId) return;

    const token = getToken();
    const ws = new WebSocket(`${WS_URL}/ws/tasks`);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ token }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "connected") {
          ws.send(JSON.stringify({ type: "subscribe", task_id: taskId }));
        } else if (msg.type === "task_state") {
          onUpdateRef.current(msg);
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
    };
  }, [taskId]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);
}
