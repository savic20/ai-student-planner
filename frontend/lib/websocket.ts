// WebSocket client utilities
export function createWebSocket(url: string): WebSocket {
  return new WebSocket(url)
}
