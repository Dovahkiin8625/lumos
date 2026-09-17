import type { WsClientEvent, WsServerEvent } from '@/types/domain'

type Listener = (ev: WsServerEvent) => void
type UrlProvider = () => string | null

export class WsClient {
  private getUrl: UrlProvider
  private socket: WebSocket | null = null
  private listeners: Listener[] = []
  private closeListeners: Array<() => void> = []
  private retryDelay = 1000
  private manualClose = false

  /** ``getUrl`` 在每次重连时重新调用，以拿到最新 token（避免 token 过期后的无限重连循环）。 */
  constructor(getUrl: string | UrlProvider) {
    this.getUrl = typeof getUrl === 'function' ? getUrl : () => getUrl
  }

  onMessage(fn: Listener) {
    this.listeners.push(fn)
  }

  onClose(fn: () => void) {
    this.closeListeners.push(fn)
  }

  connect() {
    this.manualClose = false
    const url = this.getUrl()
    if (!url) {
      // 没有可用 token（用户登出等），不重连
      return
    }
    const sock = new WebSocket(url)
    this.socket = sock
    sock.onopen = () => {
      this.retryDelay = 1000
    }
    sock.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data) as WsServerEvent
        for (const l of this.listeners) l(ev)
      } catch {
        // 忽略非 JSON 帧
      }
    }
    sock.onclose = () => {
      this.socket = null
      for (const l of this.closeListeners) l()
      if (!this.manualClose) this.scheduleReconnect()
    }
    sock.onerror = () => {
      sock.close()
    }
  }

  private scheduleReconnect() {
    const delay = Math.min(this.retryDelay, 10_000)
    this.retryDelay = Math.min(this.retryDelay * 2, 10_000)
    setTimeout(() => this.connect(), delay)
  }

  send(msg: WsClientEvent) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return
    this.socket.send(JSON.stringify(msg))
  }

  close() {
    this.manualClose = true
    this.socket?.close()
    this.socket = null
  }
}