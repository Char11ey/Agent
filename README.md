# HomeFlow Agent

一个用自然语言控制智能家居设备的 Agent 演示项目。

## 当前进度

- **M1（已完成）**：单 Agent + 2 个工具 + 流式 UI
  - 对话「把客厅灯打开」→ LLM 通过 tool use 调用 mock IoT 服务
  - UI 流式呈现工具调用过程
- M2（计划中）：RAG + 上下文工程
- M3（计划中）：LangGraph + 评估
- M4（计划中）：产品化 + 部署

## 快速启动

### 前置要求

- Python 3.11+ 与 [uv](https://docs.astral.sh/uv/)
- Node 20+ 与 pnpm
- DeepSeek API key（在 https://platform.deepseek.com 申请）

### 启动后端

```bash
cd apps/api
cp ../../.env.example .env   # 填入 DEEPSEEK_API_KEY
uv sync --all-groups
uv run uvicorn app.main:app --port 8000 --reload
```

### 启动前端

```bash
cd apps/web
pnpm install
pnpm dev
```

打开 http://localhost:3000，试试「把客厅灯打开」「把卧室温度调到 22 度」。

### Docker Compose（可选）

```bash
export DEEPSEEK_API_KEY=sk-...
docker compose -f infra/docker-compose.yml up
```

### 运行测试

```bash
cd apps/api
uv run pytest -v
```

## 架构

（见 `docs/superpowers/specs/2026-10-08-homeflow-agent-design.md` §3）

## 为什么用 mock IoT？

真实 IoT 协议（MQTT / 米家私有协议）不是 Agent 工程的核心挑战。Mock 层把设备接口和协议解耦，方便：

1. 单元测试（不依赖真实设备）
2. 演示（不联网也能跑）
3. 未来接真实协议时只需替换 `MockIoTService`

## 关键技术决策

见 `docs/adr/`（后续补充）。
