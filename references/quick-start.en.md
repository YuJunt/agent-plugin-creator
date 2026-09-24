# Quick Start Guide (English)

> Create portable Agent Plugins with bundled Skills and MCP servers — no external dependencies required.

## What is Agent Plugin Creator?

A self-contained skill for creating [Agent Plugins 1.0.0](https://github.com/agentplugins/agent-plugins-spec) — portable packages that combine Agent Skills, MCP servers, and client extensions into a single directory that works across Claude Code, Cursor, GitHub Copilot, OpenAI Codex, and other compatible clients.

**Key features:**
- Create plugins from scratch with interactive wizard
- Generate runnable MCP server code (Python FastMCP / TypeScript SDK)
- Validate plugins against the official 1.0.0 spec
- Security audit (hardcoded secrets, code injection, path traversal)
- Cross-client adaptation (5 clients supported)
- Reverse-wrap plugins into plain Skills for platforms without Agent Plugin support
- Built-in official `skill-creator` and `mcp-builder` resources

## Installation

### Option 1: Manual install (any platform)

1. Download the skill zip package
2. Extract to your skills directory:
   - **Claude Code**: `~/.claude/skills/agent-plugin-creator/`
   - **Cursor**: `.cursor/skills/agent-plugin-creator/`
   - **Codex**: `.codex/skills/agent-plugin-creator/`
   - **Doubao**: `workspace/.user_skills/agent-plugin-creator/`
3. The skill is ready to use — no installation step needed

### Option 2: CLI install

```bash
npx skills add https://github.com/your-repo/agent-plugin-creator
```

## Quick Start: Create Your First Plugin

### Step 1: Use the interactive wizard

```bash
python3 scripts/wizard.py
```

Answer the prompts:
- Plugin name (lowercase, hyphens)
- Description
- Skills to include (name + description for each)
- MCP servers (language: python/typescript, transport: stdio/streamable-http)

### Step 2: Validate the plugin

```bash
python3 scripts/validate_plugin.py ./my-plugin
```

Expected output: `结论: 插件符合 Agent Plugins 1.0.0 规范`

### Step 3: Security audit

```bash
python3 scripts/audit_plugin.py ./my-plugin
```

### Step 4: Generate documentation

```bash
python3 scripts/generate_docs.py ./my-plugin --output README.md
```

### Step 5: Package for distribution

```bash
python3 scripts/package_plugin.py ./my-plugin --output dist
```

## Core Workflows

### Workflow A: Skill-only plugin (simplest)

```bash
# 1. Create skill scaffold
python3 scripts/init_skill.py my-skill --path ./my-plugin/skills

# 2. Edit SKILL.md (description, workflow, gotchas)

# 3. Create plugin.json
# 4. Validate
python3 scripts/validate_plugin.py ./my-plugin
```

### Workflow B: Skill + local MCP server

```bash
# 1. Generate MCP server
echo '{"tools":[{"name":"search","description":"Search docs","parameters":{"query":{"type":"string"}}}]}' > def.json
python3 scripts/create_mcp_server.py generate \
  --language python --transport stdio \
  --name doc-search --definition def.json \
  --output ./my-plugin/servers/doc-search

# 2. Implement tool logic in server.py

# 3. Test handshake
python3 scripts/test_mcp_handshake.py --command "python3 ./my-plugin/servers/doc-search/server.py"

# 4. Create mcp.json + plugin.json
# 5. Validate + audit
```

### Workflow C: Reverse-wrap to plain Skill

For platforms that don't support Agent Plugins:

```bash
python3 scripts/plugin_to_skill.py ./my-plugin --output ./my-skill-wrapped
```

This generates:
- Wrapper SKILL.md with routing table
- Original skills preserved
- `scripts/start_mcp.py` for MCP server management
- Official `quick_validate.py` verification

## Directory Structure

```
my-plugin/
├── plugin.json          # Required: plugin manifest
├── mcp.json             # Optional: MCP server config
├── skills/              # Agent Skills
│   └── my-skill/
│       ├── SKILL.md
│       ├── scripts/
│       ├── references/
│       └── assets/
├── servers/             # MCP server code (stdio)
│   └── my-server/
│       ├── server.py
│       └── pyproject.toml
└── com.<client>/        # Optional: client-specific extensions
```

## Validation & Quality Gates

| Check | Command | Purpose |
|-------|---------|---------|
| Spec validation | `validate_plugin.py` | Agent Plugins 1.0.0 compliance |
| Skill validation | `validate_skill.py` | Agent Skills spec compliance |
| Security audit | `audit_plugin.py` | Secrets, code injection, path safety |
| Quality report | `quality_report.py` | 8 quality gates |
| Release audit | `release_audit.py` | Pre-release checklist |
| Official validate | `official/skill-creator/scripts/quick_validate.py` | Anthropic official spec |

## Supported Clients

| Client | Adaptation | Status |
|--------|-----------|--------|
| Claude Code | `.claude-plugin/` + marketplace.json | ✅ |
| OpenAI Codex | `.codex-plugin/` | ✅ |
| GitHub Copilot | `com.github.copilot/hooks/` | ✅ |
| Cursor | `.cursor/rules/*.mdc` | ✅ |
| Google Gemini | `.gemini/` | ✅ |

```bash
# Check compatibility
python3 scripts/client_adapter.py ./my-plugin --check

# Generate all client extensions
python3 scripts/client_adapter.py ./my-plugin --generate --clients claude,codex,copilot,cursor,gemini
```

## Gotchas

1. **Skill names**: lowercase + hyphens only, no dots or uppercase
2. **MCP stdio servers**: never print to stdout (use stderr), it breaks JSON-RPC
3. **mcp.json command**: must be a single executable token, args go in `args` array
4. **Version consistency**: plugin.json and mcp.json `$schema` must match
5. **Path safety**: all plugin-relative paths start with `./`, no `..` traversal
6. **Secrets**: never hardcode API keys in code or config, use environment variables
7. **Reverse-wrap**: wrapper-version follows the skill version, sub-skills keep original version
8. **Progressive disclosure**: keep SKILL.md under 500 lines, move details to references/

## Getting Help

- Full documentation: `references/cheatsheet.md`
- Version management: `references/versioning.md`
- Quality gates: `references/quality-gates.md`
- Permission matrix: `references/permission-matrix.md`
- Examples: `examples/` directory (5 plugins from simple to complex)

## License

MIT License — see LICENSE.txt
