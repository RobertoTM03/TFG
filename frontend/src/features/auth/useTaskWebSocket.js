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
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch {
        console.warn("WebSocket: malformed message ignored", event.data);
        return;
      }
      try {
        if (msg.type === "connected") {
          ws.send(JSON.stringify({ type: "subscribe", task_id: taskId }));
        } else if (
          msg.type === "task_state" ||
          msg.type === "task_progress" ||
          msg.type === "task_completed" ||
          msg.type === "task_failed" ||
          msg.type === "task_requeued"
        ) {
          onUpdateRef.current(msg);
        }
      } catch (err) {
        console.error("WebSocket: error processing message", msg, err);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
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
