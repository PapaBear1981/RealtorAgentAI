export function connectAgentWS(token: string): WebSocket {
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  const url = origin.replace(/^http/, 'ws') + '/ws/agent';
  return new WebSocket(url, token);
}
