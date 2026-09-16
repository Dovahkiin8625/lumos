# MCP接入

MCP（Model Context Protocol）是Anthropic的开放标准，让LLM连接任意工具源。

## 三种传输

### stdio（本地子进程）

```yaml
mcp_servers:
  - name: filesystem
    transport: stdio
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    env: { NODE_ENV: production }
```

### SSE（远程事件流）

```yaml
- name: remote
  transport: sse
  url: https://mcp.example.com/sse
  headers:
    Authorization: Bearer ${MCP_TOKEN}
```

### Streamable HTTP（MCP 2025协议）

```yaml
- name: github
  transport: streamable_http
  url: https://api.githubcopilot.com/mcp
  headers:
    Authorization: Bearer ${GH_TOKEN}
```

## 命名空间

所有MCP工具自动加前缀 `{server}__{tool}` 避免冲突。