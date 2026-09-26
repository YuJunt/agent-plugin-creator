# TypeScript MCP 服务器真实握手测试指南

> 本文档说明如何对 `create_mcp_server.py` 生成的 TypeScript MCP 服务器进行真实握手测试和工具调用验证。

## 为什么需要单独说明

Python MCP 服务器（fastmcp）可以直接用 `python3 server.py` 启动，但 TypeScript MCP 服务器需要：
1. 安装 npm 依赖（`@modelcontextprotocol/sdk`、`zod`、`typescript`、`tsx`）
2. 编译 TypeScript（或用 `tsx` 直接运行）
3. 正确设置启动命令

## 环境准备

### 1. 安装 Node.js（>= 18）

```bash
# 检查版本
node --version  # 需要 >= 18.0.0
npm --version

# Ubuntu/Debian 安装
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS
brew install node
```

### 2. 安装 TypeScript 和 tsx（全局或本地）

```bash
# 全局安装（推荐）
npm install -g typescript tsx

# 验证
tsc --version
tsx --version
```

## 测试步骤

### 步骤 1：生成 TypeScript MCP 服务器

```bash
# 创建工具定义文件
cat > tools.json << 'EOF'
{
  "tools": [
    {
      "name": "add",
      "description": "两数相加",
      "parameters": {
        "type": "object",
        "properties": {
          "a": {"type": "integer"},
          "b": {"type": "integer"}
        },
        "required": ["a", "b"]
      }
    },
    {
      "name": "greet",
      "description": "问候用户",
      "parameters": {
        "type": "object",
        "properties": {
          "name": {"type": "string"}
        },
        "required": ["name"]
      }
    }
  ]
}
EOF

# 生成 TypeScript MCP 服务器
python3 scripts/create_mcp_server.py generate \
  --language typescript \
  --transport stdio \
  --name my-ts-server \
  --definition tools.json \
  --output ./my-ts-server
```

### 步骤 2：安装依赖

```bash
cd my-ts-server
npm install
```

这会安装 `package.json` 中声明的依赖，包括：
- `@modelcontextprotocol/sdk` — MCP 官方 SDK
- `zod` — 参数校验
- `typescript` — TypeScript 编译器
- `tsx` — TypeScript 直接运行器
- `@types/node` — Node.js 类型定义

### 步骤 3：编译（可选，用 tsx 可跳过）

```bash
# 编译为 JavaScript
npx tsc --noEmit  # 仅类型检查，不输出
npx tsc            # 编译到 dist/

# 如果编译报错，检查：
# - tsconfig.json 的 target 是否为 ES2022 或更高
# - 是否安装了 @types/node
```

### 步骤 4：运行握手测试

```bash
# 方式 A：用 tsx 直接运行（推荐，无需编译）
python3 scripts/test_mcp_handshake.py \
  --command "npx tsx src/server.ts" \
  --timeout 15

# 方式 B：先编译再运行
npx tsc
python3 scripts/test_mcp_handshake.py \
  --command "node dist/server.js" \
  --timeout 10
```

预期输出：
```
MCP 服务器握手测试报告
✅ 通过: initialize (初始化握手)
✅ 通过: tools/list (工具列表，发现 2 个工具)
结论: 握手测试全部通过 ✅
```

### 步骤 5：运行工具真实调用测试

```bash
# 方式 A：tsx 直接运行
python3 scripts/test_mcp_tools.py \
  --command npx \
  --args tsx src/server.ts \
  --timeout 15

# 方式 B：编译后运行
python3 scripts/test_mcp_tools.py \
  --command node \
  --args dist/server.js \
  --timeout 10
```

预期输出：
```
✅ 工具列表: 2 个工具

工具调用测试:
------------------------------------------------------------
  ✅ add (1.2ms)
  ✅ greet (1.0ms)

============================================================
汇总: 2/2 通过 (100.0%), 失败 0, 跳过 0
✅ 所有工具调用测试通过
============================================================
```

### 步骤 6：性能基准测试

```bash
python3 scripts/benchmark_mcp.py \
  --server src/server.ts \
  --command "npx tsx" \
  --tool add \
  --arguments '{"a":1,"b":2}' \
  --requests 10 \
  --concurrency 1 \
  --timeout 15 \
  --output benchmark.json
```

## 常见问题排查

### 问题 1：`npx tsx` 启动慢，握手超时

**症状**：`test_mcp_handshake.py` 报 "等待响应超时"

**原因**：`npx tsx` 首次运行需要下载和编译，启动慢

**解决**：
```bash
# 增加超时时间
python3 scripts/test_mcp_handshake.py --command "npx tsx src/server.ts" --timeout 30

# 或全局安装 tsx，避免 npx 开销
npm install -g tsx
python3 scripts/test_mcp_handshake.py --command "tsx src/server.ts" --timeout 15

# 或先编译再运行（启动更快）
npx tsc
python3 scripts/test_mcp_handshake.py --command "node dist/server.js" --timeout 10
```

### 问题 2：TypeScript 编译报错 `Cannot find module '@modelcontextprotocol/sdk'`

**原因**：依赖未安装或安装失败

**解决**：
```bash
rm -rf node_modules package-lock.json
npm install
npm ls @modelcontextprotocol/sdk  # 确认已安装
```

### 问题 3：握手失败，报 "Invalid JSON-RPC response"

**原因**：服务器在 stdout 打印了调试信息，破坏了 JSON-RPC 协议

**解决**：
- 所有 `console.log()` 改为 `console.error()`
- stdout 是 JSON-RPC 专用通道，任何额外输出都会破坏协议
- 检查生成的 `src/server.ts`，确保没有 `console.log`

### 问题 4：`tsc` 报 `Cannot find name 'process'`

**原因**：缺少 `@types/node`

**解决**：
```bash
npm install --save-dev @types/node
# 确保 tsconfig.json 中有 "types": ["node"]
```

### 问题 5：工具调用返回空结果

**原因**：工具函数没有正确返回值，或返回值格式不对

**解决**：
- 检查工具函数是否有 `return` 语句
- MCP 工具返回值应为字符串，或包含 `content` 数组的对象
- 参考生成的模板代码中的返回格式

## streamable-http 传输类型测试

如果生成的是 streamable-http 类型的服务器：

```bash
# 1. 启动服务器（监听端口）
npx tsx src/server.ts --port 3000 &

# 2. 用 probe_remote_mcp.py 探测
python3 scripts/probe_remote_mcp.py \
  --url "http://localhost:3000/mcp" \
  --output probe.json

# 3. 验证结果
cat probe.json
```

注意：streamable-http 类型的服务器需要自己实现 HTTP 监听，生成的模板可能需要补充启动代码。

## 快速验证清单

发布 TypeScript MCP 服务器前，确保以下全部通过：

- [ ] `npm install` 无错误
- [ ] `npx tsc --noEmit` 类型检查通过
- [ ] `test_mcp_handshake.py` 握手通过
- [ ] `test_mcp_tools.py` 所有工具调用通过
- [ ] stdout 无调试输出（全部用 stderr）
- [ ] `validate_plugin.py` 插件结构验证通过
- [ ] `audit_plugin.py` 无 high/critical 安全问题
