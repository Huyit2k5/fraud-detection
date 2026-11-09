"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { openStream, type StreamMessage, type StreamStats, type StreamTx } from "@/lib/api";

const MAX_ROWS = 40;
const MAX_ALERTS = 200; // danh sách lọc "chỉ nghi gian lận" giữ lâu hơn luồng chung
const RECONNECT_MS = 2000;
const EMPTY_STATS: StreamStats = { checked: 0, caught: 0, false_alarms: 0, missed: 0, blocked_amount: 0 };

type Cmd =
  | { cmd: "pause" }
  | { cmd: "resume" }
  | { cmd: "restart" }
  | { cmd: "step" }
  | { cmd: "speed"; value: number };

/** Kết nối WebSocket phát lại luồng giao dịch của tập test (backend/app.py). Tự kết nối lại sau 2 giây nếu
 *  kết nối bị đóng ngoài ý muốn; mỗi kết nối mới, backend phát lại từ đầu tập test.
 *  `onStep` được gọi với giao dịch vừa phát ở chế độ từng giao dịch (lệnh step). */
export function useStream(enabled: boolean, onStep?: (tx: StreamTx) => void) {
  const onStepRef = useRef(onStep);
  useEffect(() => {
    onStepRef.current = onStep;
  }, [onStep]);
  const [txs, setTxs] = useState<StreamTx[]>([]);
  const [alerts, setAlerts] = useState<StreamTx[]>([]);
  const [stats, setStats] = useState<StreamStats>(EMPTY_STATS);
  const [clock, setClock] = useState(0);
  const [speed, setSpeedState] = useState(100);
  const [paused, setPaused] = useState(false);
  const [ended, setEnded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let finished = false;

    const connect = () => {
      const ws = openStream();
      wsRef.current = ws;
      ws.onopen = () => {
        setConnected(true);
        setError(null);
        setTxs([]);
        setAlerts([]);
        setStats(EMPTY_STATS);
        setEnded(false);
      };
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data) as StreamMessage;
        if (msg.type === "error") {
          finished = true;
          setError(msg.detail);
        } else if (msg.type === "end") {
          finished = true;
          setStats(msg.stats);
          setEnded(true);
        } else {
          setStats(msg.stats);
          setClock(msg.clock);
          setSpeedState(msg.speed);
          setPaused(msg.paused);
          if (msg.txs.length) setTxs((prev) => [...msg.txs.slice().reverse(), ...prev].slice(0, MAX_ROWS));
          const flagged = msg.txs.filter((t) => t.alert);
          if (flagged.length) setAlerts((prev) => [...flagged.reverse(), ...prev].slice(0, MAX_ALERTS));
          if (msg.step && msg.txs.length) onStepRef.current?.(msg.txs[0]);
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (alive && !finished) timer = setTimeout(connect, RECONNECT_MS);
      };
    };
    connect();
    return () => {
      alive = false;
      clearTimeout(timer);
      wsRef.current?.close();
    };
  }, [enabled]);

  const send = useCallback((cmd: Cmd) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(cmd));
  }, []);

  return {
    txs, alerts, stats, clock, speed, paused, ended, error, connected,
    pause: () => send({ cmd: "pause" }),
    resume: () => send({ cmd: "resume" }),
    step: () => send({ cmd: "step" }),
    restart: () => {
      setTxs([]);
      setAlerts([]);
      setEnded(false);
      send({ cmd: "restart" });
    },
    setSpeed: (value: number) => send({ cmd: "speed", value }),
  };
}
