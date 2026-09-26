# 错误码系统参考手册

> 本文档列出 agent-plugin-creator 所有标准化错误码（共 31 个），按类别分组。
> 运行 `python3 scripts/errors.py --list` 获取最新列表，`python3 scripts/errors.py --lookup E1001` 查询单个错误码。

## 错误码命名规则

- 格式：`E` + 4位数字（如 `E1001`）
- 千位表示类别：
  - `1xxx`：输入/参数错误
  - `2xxx`：规范/验证错误
  - `3xxx`：安全错误
  - `4xxx`：MCP 错误
  - `5xxx`：构建/发布错误
  - `6xxx`：外部依赖/环境错误
  - `9xxx`：内部/未知错误

---

## 1xxx — 输入/参数错误（7 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E1001 | 无效参数 | 检查命令行参数是否正确，用 `--help` 查看用法 |
| E1002 | 缺少必需参数 | 查看 `--help` 获取完整参数列表，补充缺失参数 |
| E1003 | 路径无效 | 检查文件/目录路径是否存在且可访问 |
| E1004 | 文件不存在 | 确认文件路径正确，或先创建该文件 |
| E1005 | 目录不存在 | 确认目录路径正确，或先创建该目录 |
| E1006 | JSON 格式无效 | 检查 JSON 语法，使用 `python3 -m json.tool` 或 jsonlint 验证 |
| E1007 | 名称不符合规范 | 名称只能包含 Unicode 小写字母、数字、连字符（不允许点/大写/特殊字符） |

## 2xxx — 规范/验证错误（6 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E2001 | 验证失败 | 运行 `python3 scripts/validate_plugin.py <插件目录>` 查看详细错误 |
| E2002 | Schema 版本不匹配 | 确保 plugin.json 和 mcp.json 的 `$schema` 版本一致（都为 1.0.0 或都为 1.1.0） |
| E2003 | 缺少必需字段 | 检查规范文档，补充 plugin.json 的 `name`、`$schema` 等必需字段 |
| E2004 | 未知字段 | plugin.json 只允许规范定义的字段，自定义字段移到 `extensions` 下或客户端扩展目录 |
| E2005 | 名称与目录不一致 | plugin name 必须与插件目录名完全一致；skill name 必须与 skill 目录名一致 |
| E2006 | 路径不安全 | 插件内所有相对路径必须以 `./` 开头，不能包含 `../` 逃逸出插件根目录 |

## 3xxx — 安全错误（4 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E3001 | 安全审计失败 | 运行 `python3 scripts/audit_plugin.py <插件目录> --severity high` 查看详细问题 |
| E3002 | 检测到硬编码密钥 | 将 API key、密码、token 移到环境变量或客户端配置中，不要写在代码里 |
| E3003 | 检测到危险代码 | 移除 `eval()`、`exec()`、`shell=True`、`os.system()`、`pickle.loads()` 等危险调用 |
| E3004 | 路径穿越风险 | 检查文件操作路径，防止用户输入构造 `../` 逃逸出预期目录 |

## 4xxx — MCP 错误（4 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E4001 | MCP 握手失败 | 检查服务器启动命令和参数，确保 stdio 传输正确，调试信息打到 stderr 而非 stdout |
| E4002 | MCP 工具调用失败 | 检查工具名称和参数是否正确，用 `test_mcp_tools.py` 逐个验证工具 |
| E4003 | MCP 服务器不存在 | 检查 mcp.json 中的服务器配置，确认 command/args 路径正确 |
| E4004 | 无效的 MCP 传输类型 | 支持 `stdio`（本地子进程）和 `streamable-http`（远程 HTTP），不支持其他类型 |

## 5xxx — 构建/发布错误（4 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E5001 | 构建失败 | 检查构建日志，修复编译/类型错误后重试 |
| E5002 | 打包失败 | 检查插件结构，确保 plugin.json 等必需文件存在，用 `validate_plugin.py` 验证 |
| E5003 | 缺少依赖 | 运行 `python3 scripts/manage_deps.py <server_dir> --check` 检查并安装缺失依赖 |
| E5004 | 版本冲突 | 检查 plugin.json、CHANGELOG.md、provenance.json 的版本号是否一致 |

## 6xxx — 外部依赖/环境错误（4 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E6001 | 外部工具执行失败 | 检查外部工具（如 docker、npm、git）是否安装且可执行 |
| E6002 | Git 操作失败 | 检查 Git 状态、权限和远程仓库配置，确保有推送权限 |
| E6003 | 网络错误 | 检查网络连接和代理设置，确认目标地址可访问 |
| E6004 | 操作超时 | 增加 `--timeout` 参数，或检查目标服务是否响应 |

## 9xxx — 内部/未知错误（2 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E9001 | 内部错误 | 这可能是技能本身的 bug，请在 GitHub 提交 issue 并附上复现步骤 |
| E9999 | 未知错误 | 查看详细错误信息和堆栈跟踪，根据具体内容排查 |

---

## 使用示例

```bash
# 列出所有错误码
python3 scripts/errors.py --list

# 查询单个错误码
python3 scripts/errors.py --lookup E3002

# 按类别筛选
python3 scripts/errors.py --category security

# JSON 格式输出（便于脚本解析）
python3 scripts/errors.py --list --json
```

## 错误码与脚本对应关系

| 脚本 | 主要可能触发的错误码 |
|------|---------------------|
| `validate_plugin.py` | E2001-E2006, E1006 |
| `validate_skill.py` | E2001, E2005, E1007 |
| `audit_plugin.py` | E3001-E3004 |
| `test_mcp_handshake.py` | E4001, E4003, E6004 |
| `test_mcp_tools.py` | E4002, E4001 |
| `benchmark_mcp.py` | E4001, E4002, E6004 |
| `package_plugin.py` | E5002, E2001 |
| `build_release.py` | E5001, E5002 |
| `create_mcp_server.py` | E1001, E1006, E5003 |
| `wizard.py` | E1001-E1007, E2001 |
| `dockerize.py` | E6001, E5001 |
| `manage_deps.py` | E5003, E1003 |
