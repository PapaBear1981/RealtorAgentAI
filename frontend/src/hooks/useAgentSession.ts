import { useEffect, useRef, useState } from 'react';
import { connectAgentWS } from '../lib/wsClient';

const ACK_INTERVAL = 50;

export function useAgentSession(token: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [lastSeq, setLastSeq] = useState(0);
  const [output, setOutput] = useState('');
  const [status, setStatus] = useState('');

  const send = (msg: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  };

  const connect = () => {
    if (!token) return;
    const ws = connectAgentWS(token);
    ws.onopen = () => {
      setConnected(true);
      if (sessionId) {
        send({ jsonrpc: '2.0', id: 'resume', method: 'session.resume', params: { sessionId, lastSeq } });
      }
    };
    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      // attempt single reconnect
      if (sessionId) {
        setTimeout(connect, 500);
      }
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.result?.sessionId) {
          setSessionId(msg.result.sessionId);
        }
        if (msg.event) {
          const evn = msg.event;
          if (typeof evn.seq === 'number') {
            setLastSeq(evn.seq);
            if (evn.seq % ACK_INTERVAL === 0) {
              send({ jsonrpc: '2.0', method: 'ack', params: { lastSeq: evn.seq } });
            }
          }
          if (evn.type === 'token' && evn.text) {
            setOutput((o) => o + evn.text);
          }
          if (evn.type === 'status' && evn.phase) {
            setStatus(evn.phase);
          }
        }
      } catch (err) {
        // ignore
      }
    };
    wsRef.current = ws;
  };

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const run = (prompt: string) => {
    setOutput('');
    send({ jsonrpc: '2.0', id: 'run', method: 'agent.run', params: { prompt, sessionId } });
  };

  const cancel = (jobId: string) => {
    send({ jsonrpc: '2.0', id: 'cancel', method: 'agent.cancel', params: { jobId } });
  };

  return { connected, sessionId, lastSeq, run, cancel, output, status };
}
