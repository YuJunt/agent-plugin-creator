# MCP Streamable HTTP 部署最佳实践

> 基于 MCP 2026-07-28 新规范 + AWS 最佳实践 + 无状态架构设计

## 概述

MCP 2026-07-28 规范将协议从有状态改为无状态，Streamable HTTP 传输模式取代了原来的 SSE（Server-Sent Events）模式。本文档提供生产环境部署的最佳实践。

---

## 一、无状态架构核心原则

### 为什么需要无状态？

| 维度 | 有状态（旧版） | 无状态（新版 2026-07-28） |
|------|--------------|------------------------|
| 会话管理 | 需要 sticky session | 每个请求自包含 |
| 水平扩展 | 困难（会话绑定） | 容易（无状态） |
| 故障恢复 | 会话丢失 | 无影响 |
| Serverless 兼容 | ❌ | ✅ |
| AWS Lambda | ❌ | ✅ |

### 关键设计原则

1. **每个请求自包含**：不依赖服务器端会话状态
2. **无粘性会话**：任何请求可以路由到任何服务器实例
3. **可水平扩展**：添加实例即可提升吞吐量
4. **可观测性**：每个请求都有完整的追踪 ID

---

## 二、AWS 部署架构

### 推荐架构：Serverless + API Gateway

```
客户端 → API Gateway → Lambda (MCP Server) → 后端服务
                          ↓
                     CloudWatch Logs
```

### 优势

- **无需管理服务器**：AWS 自动扩缩容
- **按调用付费**：空闲时零成本
- **高可用**：多 AZ 自动部署
- **安全**：IAM 认证 + WAF

### 注意事项

- **冷启动**：Lambda 首次调用可能有 1-2 秒延迟
- **执行时间限制**：默认 15 分钟（可配置到 15 分钟）
- **内存限制**：最大 10GB
- **临时存储**：/tmp 目录最多 10GB

---

## 三、生产环境 Checklist

### 安全

- [ ] 启用 HTTPS/TLS 1.3
- [ ] 配置 IAM 认证或 OAuth 2.1
- [ ] 启用 WAF（Web 应用防火墙）
- [ ] 配置 CORS 白名单
- [ ] 所有密钥存放到 Secrets Manager
- [ ] 启用请求大小限制（默认 10MB）

### 可靠性

- [ ] 配置超时（外部调用）
- [ ] 配置重试策略（指数退避）
- [ ] 启用熔断机制
- [ ] 配置健康检查端点
- [ ] 优雅关闭处理

### 可观测性

- [ ] CloudWatch 日志
- [ ] X-Ray 分布式追踪
- [ ] 错误率告警
- [ ] 延迟 P50/P95/P99 监控
- [ ] 请求量和错误率仪表盘

### 性能

- [ ] 连接池配置
- [ ] 缓存策略（静态资源）
- [ ] 数据库连接池
- [ ] 冷启动优化（Provisioned Concurrency）

---

## 四、Docker 部署

### Dockerfile 示例

```dockerfile
FROM node:20-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .

EXPOSE 3000
USER node

CMD ["node", "dist/server.js"]
```

### docker-compose.yml

```yaml
version: '3.8'
services:
  mcp-server:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - PORT=3000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

---

## 五、迁移检查清单

从旧版 SSE 迁移到新版 Streamable HTTP：

1. [ ] 移除所有会话状态依赖
2. [ ] 移除 `mcp-session-id` 头
3. [ ] 移除 `initialize` 握手
4. [ ] 每个请求自包含所有必要信息
5. [ ] 验证水平扩展（多实例无状态）
6. [ ] 测试 Serverless 部署（Lambda）
7. [ ] 更新客户端 SDK 到最新版本

---

## 六、参考资源

- [MCP 2026-07-28 规范](https://modelcontextprotocol.io/specification/2026-07-28/)
- [AWS 无状态 MCP 最佳实践](https://aws.amazon.com/blogs/architecture/mcp-went-stateless-is-your-aws-mcp-server-deployment-well-architected/)
- [Streamable HTTP 传输规范](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)
