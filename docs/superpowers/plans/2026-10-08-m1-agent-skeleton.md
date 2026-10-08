# M1: Agent 骨架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付 HomeFlow Agent 第一个可演示 checkpoint —— 对话「把客厅灯打开」，LLM 通过 tool use 调用 mock IoT 服务把灯打开，Next.js UI 流式呈现工具调用过程。

**Architecture:** FastAPI 后端承载一个**手写 agent loop**（不用 LangGraph，M3 再引入，先理解原理）。LLM 通过 Provider 抽象层接入 DeepSeek（OpenAI 兼容）。工具层注册 2 个工具（`turn_on_light`、`set_temperature`）操作内存 Mock IoT 服务。前端 Next.js 通过 SSE 接收 `tool_call` / `tool_result` / `text_delta` / `done` 事件流，渲染对话与工具调用卡片。

**Tech Stack:** Python 3.11+ / uv / FastAPI / openai-sdk / pytest · Node 20+ / pnpm / Next.js 15 (App Router) / TypeScript strict · Docker Compose

**Spec:** `docs/superpowers/specs/2026-10-08-homeflow-agent-design.md`（§3 技术架构、§4 M1 阶段）

---

## Global Constraints

- Python ≥ 3.11，用 `uv` 管理虚拟环境（不用 poetry / conda）
- Node ≥ 20，用 `pnpm` 作为 JS 包管理器
- TypeScript 开启 `strict: true`
- M1 只做**文本对话**，不做语音输入输出
- M1 只做**单用户**，不做鉴权（JWT 属 M4）
- M1 使用 **Mock IoT 层**，禁止对接真实 IoT 协议（MQTT / 米家私有协议）
- M1 用**手写 agent loop**，不引入 LangGraph / LangChain（M3 再用）
- 所有 Python 代码都必须有对应 pytest 测试；前端 UI 用手动验证（逻辑薄，M4 加 Playwright）
- Commit message 遵循 Conventional Commits：`feat:` / `test:` / `docs:` / `chore:` / `fix:`

---

## Review Focus

以下是 spec 隐含但常规 happy-path 测试覆盖不到、最容易咬人的输入类/失败模式。每个都在对应 task 的测试里钉住：

1. **LLM 返回非法 tool_call JSON 或未知工具名** → agent 报错给用户，不 crash 也不断循环（Task 5 测试）
2. **工具执行抛异常**（如设备不存在）→ 错误回传给 LLM 继续推理，不让 agent loop 崩溃（Task 5 测试）
3. **LLM 陷入 tool-call 死循环**（永远发工具调用、永不给最终答案）→ `max_iterations` 强制终止并返回诊断消息（Task 5 测试）
4. **SSE 客户端中途断开**（用户关浏览器）→ FastAPI `StreamingResponse` 生成器退出、无泄漏（Task 6 手动 + try/finally 覆盖）
5. **`DEEPSEEK_API_KEY` 未设置** → 启动 Provider 时立即抛清晰错误，而非运行时 obscure crash（Task 3 测试）

---

## File Structure

M1 结束时会创建/修改的文件：

```
homeflow-agent/
├── README.md                                    # Task 8 更新（运行说明）
├── .gitignore                                   # Task 1
├── .env.example                                 # Task 1（DeepSeek key占位）
├── infra/
│   └── docker-compose.yml                       # Task 1（api + web 服务）
├── apps/
│   ├── api/
│   │   ├── pyproject.toml                       # Task 1（uv 依赖）
│   │   ├── .env                                 # Task 1（用户本地，gitignored）
│   │   ├── Dockerfile                           # Task 1
│   │   ├── app/
│   │   │   ├── __init__.py                      # Task 1
│   │   │   ├── main.py                          # Task 1（FastAPI app + /healthz）→ Task 6 挂 chat router
│   │   │   ├── config.py                        # Task 1（Settings，读取 env）
│   │   │   ├── state.py                         # Task 6（可变全局状态：agent / iot）
│   │   │   ├── iot/
│   │   │   │   ├── __init__.py                  # Task 2
│   │   │   │   ├── models.py                    # Task 2（Device / DeviceType / DeviceState）
│   │   │   │   └── service.py                   # Task 2（MockIoTService）
│   │   │   ├── llm/
│   │   │   │   ├── __init__.py                  # Task 3
│   │   │   │   ├── base.py                      # Task 3（ToolCall / LLMResponse / LLMProvider 协议）
│   │   │   │   ├── fake.py                      # Task 3（FakeProvider，测试用）
│   │   │   │   └── deepseek.py                  # Task 3（DeepSeekProvider，OpenAI 兼容）
│   │   │   ├── agent/
│   │   │   │   ├── __init__.py                  # Task 4
│   │   │   │   ├── tools.py                     # Task 4（Tool / ToolRegistry / make_iot_tools）
│   │   │   │   └── loop.py                      # Task 5（AgentEvent / AgentLoop）
│   │   │   └── routers/
│   │   │       ├── __init__.py                  # Task 6
│   │   │       └── chat.py                      # Task 6（POST /api/chat SSE）
│   │   └── tests/
│   │       ├── conftest.py                      # Task 2（iot service fixture）
│   │       ├── test_config.py                   # Task 1 / 3
│   │       ├── test_iot_service.py              # Task 2
│   │       ├── test_llm_provider.py             # Task 3
│   │       ├── test_tools.py                    # Task 4
│   │       ├── test_agent_loop.py               # Task 5
│   │       └── test_chat_endpoint.py            # Task 6
│   └── web/
│       ├── package.json                         # Task 7
│       ├── tsconfig.json                        # Task 7
│       ├── next.config.ts                       # Task 7
│       ├── app/
│       │   ├── layout.tsx                       # Task 7
│       │   ├── page.tsx                         # Task 7（Chat 容器）
│       │   └── globals.css                      # Task 7
│       ├── components/
│       │   ├── Chat.tsx                         # Task 7（对话状态管理 + SSE 接入）
│       │   ├── MessageList.tsx                  # Task 7
│       │   ├── MessageInput.tsx                 # Task 7
│       │   └── ToolCallCard.tsx                 # Task 7（工具调用可视化卡片）
│       └── lib/
│           ├── api.ts                           # Task 7（SSE 客户端）
│           └── types.ts                         # Task 7（AgentEvent TS 类型）
└── docs/
    ├── learning/
    │   └── m1-notes.md                          # Task 8（用户学习笔记占位）
    └── superpowers/
        ├── specs/2026-10-08-homeflow-agent-design.md
        └── plans/2026-10-08-m1-agent-skeleton.md  # 本文件
```

---

## Task 1: 项目骨架（Monorepo + FastAPI + Next.js 空壳）

**Files:**
- Create: `.gitignore`, `.env.example`, `infra/docker-compose.yml`
- Create: `apps/api/pyproject.toml`, `apps/api/Dockerfile`, `apps/api/.env`
- Create: `apps/api/app/__init__.py`, `apps/api/app/config.py`, `apps/api/app/main.py`
- Create: `apps/api/tests/test_config.py`
- Create: `apps/web/`（用 `create-next-app` 脚手架，不手写所有文件）

**Interfaces:**
- Consumes: 无（首个任务）
- Produces:
  - `apps/api/app/config.py::Settings`：`Settings.from_env()` 读取 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`LLM_MODEL`（后续 Task 3 用）
  - `apps/api/app/main.py::app`：FastAPI 实例，`GET /healthz` 返回 `{"status": "ok"}`

- [ ] **Step 1: 建立仓库骨架与 .gitignore**

在 `homeflow-agent/` 根目录创建 `.gitignore`：

```gitignore
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Node
node_modules/
.next/
out/
.turbo/
*.tsbuildinfo

# Env
.env
.env.local
.env.*.local

# IDE
.idea/
.vscode/
.DS_Store

# Logs
*.log
```

创建 `.env.example`：

```bash
# LLM Provider（Task 3 会用到）
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

- [ ] **Step 2: 创建 Python 后端骨架（uv + FastAPI）**

创建 `apps/api/pyproject.toml`：

```toml
[project]
name = "homeflow-api"
version = "0.1.0"
description = "HomeFlow Agent backend"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "openai>=1.55.0",
    "python-dotenv>=1.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

创建 `apps/api/app/__init__.py`（空文件）和 `apps/api/app/config.py`：

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """读取环境变量；.env 里的值会被 os.environ 覆盖。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls()
```

创建 `apps/api/app/main.py`：

```python
from fastapi import FastAPI

from app.config import Settings

app = FastAPI(title="HomeFlow Agent API", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

创建 `apps/api/tests/test_config.py`：

```python
import os

from app.config import Settings


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-123")
    monkeypatch.setenv("LLM_MODEL", "deepseek-chat")
    s = Settings.from_env()
    assert s.deepseek_api_key == "sk-test-123"
    assert s.llm_model == "deepseek-chat"


def test_settings_defaults():
    monkeypatch_env = {"DEEPSEEK_API_KEY": "", "LLM_MODEL": ""}
    # 通过显式构造测试默认值
    s = Settings(deepseek_api_key="", llm_model="deepseek-chat")
    assert s.deepseek_base_url == "https://api.deepseek.com"
```

- [ ] **Step 3: 初始化 uv 环境并运行测试（RED→GREEN 确认骨架可测）**

```bash
cd apps/api
uv sync --all-groups
uv run pytest tests/test_config.py -v
```

Expected: 2 个测试 PASS（这是骨架的 sanity check，不走完整 RED——它测的是配置读取本身）

- [ ] **Step 4: 启动 FastAPI 验证 /healthz**

```bash
cd apps/api
uv run uvicorn app.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/healthz
```

Expected: `{"status":"ok"}`

（验证后 `kill %1` 关掉 uvicorn）

- [ ] **Step 5: 用 create-next-app 生成前端骨架**

```bash
cd apps
pnpm create next-app@latest web --typescript --eslint --app --no-tailwind --no-src-dir --import-alias "@/*"
cd web
pnpm add ai          # Vercel AI SDK，Task 7 用
pnpm dev             # 启动后访问 http://localhost:3000 验证
```

Expected: Next.js 欢迎页在 3000 端口渲染（验证后停掉）

- [ ] **Step 6: Docker Compose 编排**

创建 `infra/docker-compose.yml`：

```yaml
services:
  api:
    build: ../apps/api
    ports:
      - "8000:8000"
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
      - DEEPSEEK_BASE_URL=${DEEPSEEK_BASE_URL:-https://api.deepseek.com}
      - LLM_MODEL=${LLM_MODEL:-deepseek-chat}
    volumes:
      - ../apps/api:/code
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  web:
    build: ../apps/web
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    volumes:
      - ../apps/web:/code
      - /code/node_modules
      - /code/.next
    command: pnpm dev
```

创建 `apps/api/Dockerfile`：

```dockerfile
FROM python:3.11-slim
WORKDIR /code
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml ./
RUN uv sync --all-groups --no-install-project
COPY . .
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

创建 `apps/web/Dockerfile`：

```dockerfile
FROM node:20-slim
WORKDIR /code
RUN corepack enable
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install
COPY . .
CMD ["pnpm", "dev"]
```

- [ ] **Step 7: Commit**

```bash
git add .gitignore .env.example infra apps
git commit -m "chore: M1 项目骨架（FastAPI + Next.js + docker-compose）"
```

---

## Task 2: Mock IoT 设备层

**Files:**
- Create: `apps/api/app/iot/__init__.py`, `apps/api/app/iot/models.py`, `apps/api/app/iot/service.py`
- Create: `apps/api/tests/conftest.py`, `apps/api/tests/test_iot_service.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `apps/api/app/iot/models.py::DeviceType`（Enum: `LIGHT`/`AC`）
  - `apps/api/app/iot/models.py::DeviceState`（pydantic: `on: bool`、`temperature: int | None`）
  - `apps/api/app/iot/models.py::Device`（pydantic: `id: str`、`name: str`、`type: DeviceType`、`room: str`、`state: DeviceState`）
  - `apps/api/app/iot/service.py::MockIoTService`：
    - `list_devices() -> list[Device]`
    - `get_device(device_id: str) -> Device`（不存在抛 `KeyError`）
    - `find_devices(room: str, type: DeviceType) -> list[Device]`
    - `set_state(device_id: str, *, on: bool | None = None, temperature: int | None = None) -> Device`

- [ ] **Step 1: 写失败测试**

创建 `apps/api/tests/conftest.py`：

```python
import pytest

from app.iot.service import MockIoTService


@pytest.fixture
def iot() -> MockIoTService:
    return MockIoTService.with_seed_data()
```

创建 `apps/api/tests/test_iot_service.py`：

```python
import pytest

from app.iot.models import DeviceType
from app.iot.service import MockIoTService


def test_seed_data_has_devices(iot: MockIoTService):
    devices = iot.list_devices()
    assert len(devices) >= 4  # 至少有 2 灯 + 2 空调


def test_get_device_returns_seeded(iot: MockIoTService):
    d = iot.get_device("light-living-1")
    assert d.type == DeviceType.LIGHT
    assert d.room == "客厅"


def test_get_device_missing_raises(iot: MockIoTService):
    with pytest.raises(KeyError):
        iot.get_device("nonexistent")


def test_find_devices_by_room_and_type(iot: MockIoTService):
    lights = iot.find_devices(room="客厅", type=DeviceType.LIGHT)
    assert len(lights) >= 1
    assert all(d.room == "客厅" and d.type == DeviceType.LIGHT for d in lights)


def test_set_state_on_off(iot: MockIoTService):
    d = iot.set_state("light-living-1", on=True)
    assert d.state.on is True
    d = iot.set_state("light-living-1", on=False)
    assert d.state.on is False


def test_set_state_temperature(iot: MockIoTService):
    d = iot.set_state("ac-living-1", temperature=26)
    assert d.state.temperature == 26


def test_set_state_invalid_temp_raises(iot: MockIoTService):
    with pytest.raises(ValueError):
        iot.set_state("ac-living-1", temperature=99)
```

- [ ] **Step 2: 运行测试确认 FAIL**

```bash
cd apps/api
uv run pytest tests/test_iot_service.py -v
```

Expected: FAIL / ERROR，"ModuleNotFoundError: No module named 'app.iot'"

- [ ] **Step 3: 实现 models 与 service**

创建 `apps/api/app/iot/__init__.py`（空文件）

创建 `apps/api/app/iot/models.py`：

```python
from enum import Enum

from pydantic import BaseModel


class DeviceType(str, Enum):
    LIGHT = "light"
    AC = "ac"


class DeviceState(BaseModel):
    on: bool = False
    temperature: int | None = None


class Device(BaseModel):
    id: str
    name: str
    type: DeviceType
    room: str
    state: DeviceState
```

创建 `apps/api/app/iot/service.py`：

```python
from copy import deepcopy

from app.iot.models import Device, DeviceState, DeviceType


class MockIoTService:
    """内存 Mock IoT 服务。真实项目里这里换成米家/MQTT 客户端；接口保持不变。"""

    def __init__(self, devices: list[Device] | None = None):
        self._devices: dict[str, Device] = {d.id: d for d in (devices or [])}

    @classmethod
    def with_seed_data(cls) -> "MockIoTService":
        return cls(
            devices=[
                Device(
                    id="light-living-1", name="客厅主灯", type=DeviceType.LIGHT, room="客厅",
                    state=DeviceState(on=False),
                ),
                Device(
                    id="light-bedroom-1", name="卧室吸顶灯", type=DeviceType.LIGHT, room="卧室",
                    state=DeviceState(on=False),
                ),
                Device(
                    id="ac-living-1", name="客厅空调", type=DeviceType.AC, room="客厅",
                    state=DeviceState(on=False, temperature=26),
                ),
                Device(
                    id="ac-bedroom-1", name="卧室空调", type=DeviceType.AC, room="卧室",
                    state=DeviceState(on=False, temperature=26),
                ),
            ]
        )

    def list_devices(self) -> list[Device]:
        return list(self._devices.values())

    def get_device(self, device_id: str) -> Device:
        if device_id not in self._devices:
            raise KeyError(f"device not found: {device_id}")
        return self._devices[device_id]

    def find_devices(self, room: str, type: DeviceType) -> list[Device]:
        return [d for d in self._devices.values() if d.room == room and d.type == type]

    def set_state(
        self,
        device_id: str,
        *,
        on: bool | None = None,
        temperature: int | None = None,
    ) -> Device:
        if device_id not in self._devices:
            raise KeyError(f"device not found: {device_id}")
        if temperature is not None and not (16 <= temperature <= 30):
            raise ValueError(f"temperature out of range [16, 30]: {temperature}")
        current = self._devices[device_id]
        new_state = current.state.model_copy()
        if on is not None:
            new_state.on = on
        if temperature is not None:
            new_state.temperature = temperature
        updated = current.model_copy(update={"state": new_state})
        self._devices[device_id] = updated
        return updated
```

- [ ] **Step 4: 运行测试确认 PASS**

```bash
cd apps/api
uv run pytest tests/test_iot_service.py -v
```

Expected: 7 个测试全 PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/iot apps/api/tests/conftest.py apps/api/tests/test_iot_service.py
git commit -m "feat: Mock IoT 设备层（Device 模型 + MockIoTService + 种子数据）"
```

---

## Task 3: LLM Provider 抽象层

**Files:**
- Create: `apps/api/app/llm/__init__.py`, `apps/api/app/llm/base.py`, `apps/api/app/llm/fake.py`, `apps/api/app/llm/deepseek.py`
- Create: `apps/api/tests/test_llm_provider.py`
- Modify: `apps/api/tests/test_config.py`（补充 API key 缺失场景）

**Interfaces:**
- Consumes: `app.config.Settings`（Task 1）
- Produces:
  - `apps/api/app/llm/base.py::ToolCall`（dataclass: `id: str`、`name: str`、`arguments: dict`）
  - `apps/api/app/llm/base.py::LLMResponse`（dataclass: `text: str | None`、`tool_calls: list[ToolCall]`、`usage: dict`）
  - `apps/api/app/llm/base.py::LLMProvider`（Protocol: `async def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse`）
  - `apps/api/app/llm/fake.py::FakeProvider`：构造时传入脚本化响应队列
  - `apps/api/app/llm/deepseek.py::DeepSeekProvider`：`__init__(settings: Settings)` 里校验 API key 存在

- [ ] **Step 1: 写失败测试**

创建 `apps/api/tests/test_llm_provider.py`：

```python
import pytest

from app.config import Settings
from app.llm.base import LLMResponse, ToolCall
from app.llm.deepseek import DeepSeekProvider
from app.llm.fake import FakeProvider


async def test_fake_provider_returns_scripted_response():
    scripted = LLMResponse(text="你好", tool_calls=[], usage={"total_tokens": 10})
    p = FakeProvider(responses=[scripted])
    resp = await p.complete(messages=[{"role": "user", "content": "hi"}], tools=[])
    assert resp.text == "你好"
    assert resp.tool_calls == []


async def test_fake_provider_yields_tool_calls():
    scripted = LLMResponse(
        text=None,
        tool_calls=[ToolCall(id="call-1", name="turn_on_light", arguments={"room": "客厅"})],
        usage={"total_tokens": 5},
    )
    p = FakeProvider(responses=[scripted])
    resp = await p.complete(messages=[], tools=[{"type": "function", "function": {"name": "turn_on_light"}}])
    assert resp.tool_calls[0].name == "turn_on_light"
    assert resp.tool_calls[0].arguments == {"room": "客厅"}


async def test_fake_provider_pops_in_order():
    r1 = LLMResponse(text="first", tool_calls=[], usage={})
    r2 = LLMResponse(text="second", tool_calls=[], usage={})
    p = FakeProvider(responses=[r1, r2])
    assert (await p.complete(messages=[], tools=[])).text == "first"
    assert (await p.complete(messages=[], tools=[])).text == "second"


def test_deepseek_requires_api_key():
    s = Settings(deepseek_api_key="")
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        DeepSeekProvider(settings=s)


def test_deepseek_accepts_valid_settings():
    s = Settings(deepseek_api_key="sk-test-123")
    p = DeepSeekProvider(settings=s)
    assert p.model == s.llm_model
```

- [ ] **Step 2: 运行测试确认 FAIL**

```bash
cd apps/api
uv run pytest tests/test_llm_provider.py -v
```

Expected: ERROR / ModuleNotFoundError: "app.llm"

- [ ] **Step 3: 实现 base / fake / deepseek**

创建 `apps/api/app/llm/__init__.py`（空文件）

创建 `apps/api/app/llm/base.py`：

```python
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)


class LLMProvider(Protocol):
    async def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        """调用 LLM。messages 用 OpenAI 格式；tools 是 OpenAI function-calling schema 列表。"""
        ...
```

创建 `apps/api/app/llm/fake.py`：

```python
from collections import deque

from app.llm.base import LLMResponse


class FakeProvider:
    """测试专用：从预设队列中按顺序返回响应。队列空了抛 RuntimeError。"""

    def __init__(self, responses: list[LLMResponse]):
        self._queue: deque[LLMResponse] = deque(responses)
        self.calls: list[tuple[list[dict], list[dict]]] = []

    async def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        self.calls.append((messages, tools))
        if not self._queue:
            raise RuntimeError("FakeProvider: scripted responses exhausted")
        return self._queue.popleft()
```

创建 `apps/api/app/llm/deepseek.py`：

```python
import json
from typing import Any

from openai import AsyncOpenAI

from app.config import Settings
from app.llm.base import LLMResponse, ToolCall


class DeepSeekProvider:
    """DeepSeek 通过 OpenAI 兼容 API 接入。"""

    def __init__(self, settings: Settings):
        if not settings.deepseek_api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY is not set. Copy .env.example to .env and fill in your key."
            )
        self.model = settings.llm_model
        self._client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )

    async def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        kwargs: dict[str, Any] = {"model": self.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message

        tool_calls: list[ToolCall] = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"__invalid_json__": tc.function.arguments}
            tool_calls.append(
                ToolCall(id=tc.id, name=tc.function.name, arguments=args)
            )

        usage = {}
        if resp.usage is not None:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
                "total_tokens": resp.usage.total_tokens,
            }

        return LLMResponse(text=msg.content, tool_calls=tool_calls, usage=usage)
```

- [ ] **Step 4: 运行测试确认 PASS**

```bash
cd apps/api
uv run pytest tests/test_llm_provider.py -v
```

Expected: 5 个测试全 PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/llm apps/api/tests/test_llm_provider.py
git commit -m "feat: LLM Provider 抽象层（Protocol + FakeProvider + DeepSeekProvider）"
```

---

## Task 4: 工具注册表 + 2 个 IoT 工具

**Files:**
- Create: `apps/api/app/agent/__init__.py`, `apps/api/app/agent/tools.py`
- Create: `apps/api/tests/test_tools.py`

**Interfaces:**
- Consumes: `MockIoTService`（Task 2）
- Produces:
  - `apps/api/app/agent/tools.py::Tool`（dataclass: `name: str`、`description: str`、`parameters: dict`（JSON Schema）、`handler: Callable[..., dict]`）
  - `apps/api/app/agent/tools.py::ToolRegistry`：
    - `register(tool: Tool) -> None`
    - `get(name: str) -> Tool`（不存在抛 `KeyError`）
    - `openai_schemas() -> list[dict]`（OpenAI function-calling 格式）
    - `names() -> list[str]`
  - `apps/api/app/agent/tools.py::make_iot_tools(iot: MockIoTService) -> list[Tool]`：返回 `turn_on_light` 和 `set_temperature` 两个工具

- [ ] **Step 1: 写失败测试**

创建 `apps/api/tests/test_tools.py`：

```python
import pytest

from app.agent.tools import Tool, ToolRegistry, make_iot_tools
from app.iot.models import DeviceType
from app.iot.service import MockIoTService


def test_make_iot_tools_returns_two():
    tools = make_iot_tools(MockIoTService.with_seed_data())
    names = [t.name for t in tools]
    assert names == ["turn_on_light", "set_temperature"]


def test_turn_on_light_handler(iot: MockIoTService):
    tools = {t.name: t for t in make_iot_tools(iot)}
    result = tools["turn_on_light"].handler(room="客厅", on=True)
    assert result["ok"] is True
    assert result["devices"][0]["state"]["on"] is True


def test_turn_on_light_room_without_light(iot: MockIoTService):
    tools = {t.name: t for t in make_iot_tools(iot)}
    result = tools["turn_on_light"].handler(room="厨房", on=True)
    assert result["ok"] is False
    assert "no light" in result["error"].lower()


def test_set_temperature_handler(iot: MockIoTService):
    tools = {t.name: t for t in make_iot_tools(iot)}
    result = tools["set_temperature"].handler(room="卧室", temperature=22)
    assert result["ok"] is True
    assert result["devices"][0]["state"]["temperature"] == 22


def test_set_temperature_out_of_range(iot: MockIoTService):
    tools = {t.name: t for t in make_iot_tools(iot)}
    with pytest.raises(ValueError, match="temperature"):
        tools["set_temperature"].handler(room="卧室", temperature=99)


def test_registry_openai_schemas():
    reg = ToolRegistry()
    reg.register(Tool(
        name="demo",
        description="demo tool",
        parameters={"type": "object", "properties": {"x": {"type": "integer"}}},
        handler=lambda x: {"ok": True},
    ))
    schemas = reg.openai_schemas()
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == "demo"
    assert "properties" in schemas[0]["function"]["parameters"]


def test_registry_get_missing_raises():
    reg = ToolRegistry()
    with pytest.raises(KeyError):
        reg.get("nope")
```

- [ ] **Step 2: 运行测试确认 FAIL**

```bash
cd apps/api
uv run pytest tests/test_tools.py -v
```

Expected: ModuleNotFoundError: "app.agent"

- [ ] **Step 3: 实现 Tool / ToolRegistry / make_iot_tools**

创建 `apps/api/app/agent/__init__.py`（空文件）

创建 `apps/api/app/agent/tools.py`：

```python
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.iot.models import DeviceType
from app.iot.service import MockIoTService


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    handler: Callable[..., dict]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def openai_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]


def make_iot_tools(iot: MockIoTService) -> list[Tool]:
    def turn_on_light(room: str, on: bool = True) -> dict:
        lights = iot.find_devices(room=room, type=DeviceType.LIGHT)
        if not lights:
            return {"ok": False, "error": f"no light found in room: {room}"}
        updated = [iot.set_state(d.id, on=on) for d in lights]
        return {"ok": True, "devices": [d.model_dump() for d in updated]}

    def set_temperature(room: str, temperature: int) -> dict:
        acs = iot.find_devices(room=room, type=DeviceType.AC)
        if not acs:
            return {"ok": False, "error": f"no AC found in room: {room}"}
        updated = [iot.set_state(d.id, temperature=temperature) for d in acs]
        return {"ok": True, "devices": [d.model_dump() for d in updated]}

    return [
        Tool(
            name="turn_on_light",
            description="Turn on or off all lights in a given room. Use this when the user asks to control lights.",
            parameters={
                "type": "object",
                "properties": {
                    "room": {
                        "type": "string",
                        "description": "The room name, e.g. '客厅' or '卧室'.",
                    },
                    "on": {
                        "type": "boolean",
                        "description": "true to turn on, false to turn off. Default true.",
                    },
                },
                "required": ["room"],
            },
            handler=turn_on_light,
        ),
        Tool(
            name="set_temperature",
            description="Set the AC temperature in a given room. Temperature range is 16-30 Celsius.",
            parameters={
                "type": "object",
                "properties": {
                    "room": {
                        "type": "string",
                        "description": "The room name, e.g. '客厅' or '卧室'.",
                    },
                    "temperature": {
                        "type": "integer",
                        "description": "Target temperature in Celsius, between 16 and 30.",
                    },
                },
                "required": ["room", "temperature"],
            },
            handler=set_temperature,
        ),
    ]
```

- [ ] **Step 4: 运行测试确认 PASS**

```bash
cd apps/api
uv run pytest tests/test_tools.py -v
```

Expected: 7 个测试全 PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/agent apps/api/tests/test_tools.py
git commit -m "feat: 工具注册表 + turn_on_light / set_temperature 两个 IoT 工具"
```

---

## Task 5: 手写 Agent Loop（含流式事件）

**Files:**
- Create: `apps/api/app/agent/loop.py`
- Create: `apps/api/tests/test_agent_loop.py`

**Interfaces:**
- Consumes:
  - `LLMProvider.complete()`（Task 3）
  - `ToolRegistry.openai_schemas()` / `ToolRegistry.get()`（Task 4）
- Produces:
  - `apps/api/app/agent/loop.py::AgentEvent`（dataclass，有 `kind: str` 字段，`kind` ∈ `{"tool_call", "tool_result", "text_delta", "error", "done"}`，每种 kind 有对应字段）
  - `apps/api/app/agent/loop.py::AgentLoop`：
    - `__init__(self, llm: LLMProvider, registry: ToolRegistry, max_iterations: int = 6)`
    - `async def stream(self, user_message: str, history: list[dict] | None = None) -> AsyncIterator[AgentEvent]`
  - Agent loop 必须处理：未知工具、工具抛异常、LLM 死循环（触发 `max_iterations` 时 yield `error` 事件）

- [ ] **Step 1: 写失败测试（覆盖 Review Focus #1 #2 #3）**

创建 `apps/api/tests/test_agent_loop.py`：

```python
import pytest

from app.agent.loop import AgentEvent, AgentLoop
from app.agent.tools import Tool, ToolRegistry, make_iot_tools
from app.iot.service import MockIoTService
from app.llm.base import LLMResponse, ToolCall
from app.llm.fake import FakeProvider


async def test_happy_path_tool_call_then_answer():
    """LLM 先发工具调用，再给最终答案。"""
    iot = MockIoTService.with_seed_data()
    reg = ToolRegistry()
    for t in make_iot_tools(iot):
        reg.register(t)

    scripted = [
        LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="c1", name="turn_on_light", arguments={"room": "客厅", "on": True})],
            usage={},
        ),
        LLMResponse(text="好的，客厅灯已打开。", tool_calls=[], usage={}),
    ]
    llm = FakeProvider(responses=scripted)
    loop = AgentLoop(llm=llm, registry=reg)

    events = [e async for e in loop.stream("把客厅灯打开")]
    kinds = [e.kind for e in events]
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert "text_delta" in kinds or "done" in kinds
    final_text = "".join(e.text for e in events if e.kind == "text_delta")
    assert "客厅灯" in final_text

    # 灯真的开了
    assert iot.get_device("light-living-1").state.on is True


async def test_unknown_tool_yields_error_not_crash():
    """LLM 调用不存在的工具 → tool_result 里返回结构化错误，loop 不崩、LLM 能继续回答用户。"""
    reg = ToolRegistry()
    scripted = [
        LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="c1", name="nonexistent_tool", arguments={})],
            usage={},
        ),
        LLMResponse(text="抱歉，我无法执行该操作。", tool_calls=[], usage={}),
    ]
    loop = AgentLoop(llm=FakeProvider(responses=scripted), registry=reg)
    events = [e async for e in loop.stream("do something")]

    # tool_result 里必须有 unknown tool 错误信息
    tool_results = [e for e in events if e.kind == "tool_result"]
    assert any("unknown tool" in str(e.result) for e in tool_results)

    # 最终 LLM 给出了回答
    final_text = "".join(e.text or "" for e in events if e.kind == "text_delta")
    assert "抱歉" in final_text


async def test_tool_exception_propagates_to_llm_not_loop_crash():
    """工具抛 ValueError → 作为 tool result 回传 LLM，loop 不崩。"""
    reg = ToolRegistry()

    def boom(room: str, temperature: int) -> dict:
        raise ValueError("temperature out of range")

    reg.register(Tool(
        name="set_temperature",
        description="set temp",
        parameters={"type": "object", "properties": {"room": {"type": "string"}, "temperature": {"type": "integer"}}},
        handler=boom,
    ))
    scripted = [
        LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="c1", name="set_temperature", arguments={"room": "卧室", "temperature": 99})],
            usage={},
        ),
        LLMResponse(text="温度范围不对，需要 16-30 度。", tool_calls=[], usage={}),
    ]
    loop = AgentLoop(llm=FakeProvider(responses=scripted), registry=reg)
    events = [e async for e in loop.stream("把卧室调到 99 度")]
    # tool_result 事件里的 content 应包含错误信息
    tool_results = [e for e in events if e.kind == "tool_result"]
    assert any("temperature" in str(e.result) for e in tool_results)


async def test_max_iterations_prevents_infinite_loop():
    """LLM 每次都发 tool call、永不返回最终答案 → max_iterations 触发 error 事件。"""
    reg = ToolRegistry()
    reg.register(Tool(
        name="noop",
        description="no-op",
        parameters={"type": "object", "properties": {}},
        handler=lambda: {"ok": True},
    ))

    def endless():
        while True:
            yield LLMResponse(
                text=None,
                tool_calls=[ToolCall(id="c", name="noop", arguments={})],
                usage={},
            )

    class EndlessProvider:
        def __init__(self):
            self._gen = endless()

        async def complete(self, messages, tools):
            return next(self._gen)

    loop = AgentLoop(llm=EndlessProvider(), registry=reg, max_iterations=3)
    events = [e async for e in loop.stream("loop forever")]
    errors = [e for e in events if e.kind == "error"]
    assert any("max" in str(e.message).lower() or "iteration" in str(e.message).lower() for e in errors)


async def test_history_is_passed_to_llm():
    reg = ToolRegistry()
    scripted = [LLMResponse(text="ok", tool_calls=[], usage={})]
    llm = FakeProvider(responses=scripted)
    loop = AgentLoop(llm=llm, registry=reg)
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    _ = [e async for e in loop.stream("next", history=history)]
    # FakeProvider.calls 记录了每次 complete 的入参
    first_messages = llm.calls[0][0]
    assert first_messages[0]["content"] == "hi"
    assert first_messages[1]["content"] == "hello"
```

- [ ] **Step 2: 运行测试确认 FAIL**

```bash
cd apps/api
uv run pytest tests/test_agent_loop.py -v
```

Expected: ModuleNotFoundError: "app.agent.loop"

- [ ] **Step 3: 实现 AgentEvent 与 AgentLoop**

创建 `apps/api/app/agent/loop.py`：

```python
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from app.agent.tools import ToolRegistry
from app.llm.base import LLMProvider, LLMResponse, ToolCall


@dataclass
class AgentEvent:
    kind: str  # "tool_call" | "tool_result" | "text_delta" | "error" | "done"
    # tool_call
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    # tool_result
    result: Any = None
    # text_delta
    text: str | None = None
    # error
    message: str | None = None
    # done
    usage: dict[str, int] = field(default_factory=dict)


class AgentLoop:
    def __init__(
        self,
        llm: LLMProvider,
        registry: ToolRegistry,
        max_iterations: int = 6,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.max_iterations = max_iterations

    async def stream(
        self,
        user_message: str,
        history: list[dict] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        messages: list[dict] = list(history or [])
        messages.append({"role": "user", "content": user_message})
        tools_schema = self.registry.openai_schemas()

        for _ in range(self.max_iterations):
            response: LLMResponse = await self.llm.complete(messages=messages, tools=tools_schema)

            # 情况 1：模型给了最终答案
            if not response.tool_calls:
                if response.text:
                    yield AgentEvent(kind="text_delta", text=response.text)
                yield AgentEvent(kind="done", usage=response.usage)
                return

            # 情况 2：模型发了工具调用
            # 先把 assistant 的 tool_calls 塞回历史
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": response.text}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in response.tool_calls
            ]
            messages.append(assistant_msg)

            for tc in response.tool_calls:
                yield AgentEvent(
                    kind="tool_call",
                    tool_call_id=tc.id,
                    tool_name=tc.name,
                    tool_arguments=tc.arguments,
                )
                result = self._execute_tool(tc)
                yield AgentEvent(
                    kind="tool_result",
                    tool_call_id=tc.id,
                    tool_name=tc.name,
                    result=result,
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

        # 走完 max_iterations 仍未拿到最终答案 → 报错并终止
        yield AgentEvent(
            kind="error",
            message=f"Agent exceeded max_iterations ({self.max_iterations}) without producing a final answer.",
        )
        yield AgentEvent(kind="done", usage={})

    def _execute_tool(self, tc: ToolCall) -> Any:
        """执行工具。工具抛异常或不存在 → 返回错误 dict，供 LLM 继续推理。"""
        try:
            tool = self.registry.get(tc.name)
        except KeyError:
            return {"ok": False, "error": f"unknown tool: {tc.name}"}
        try:
            return tool.handler(**tc.arguments)
        except Exception as e:  # noqa: BLE001 — 工具可能抛任意异常，统一转成结构化错误
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
```

- [ ] **Step 4: 运行测试确认 PASS**

```bash
cd apps/api
uv run pytest tests/test_agent_loop.py -v
```

Expected: 5 个测试全 PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/agent/loop.py apps/api/tests/test_agent_loop.py
git commit -m "feat: 手写 Agent Loop（含 tool 调用、错误处理、max_iterations 兜底）"
```

---

## Task 6: FastAPI SSE 聊天端点

**Files:**
- Create: `apps/api/app/routers/__init__.py`, `apps/api/app/routers/chat.py`
- Create: `apps/api/tests/test_chat_endpoint.py`
- Modify: `apps/api/app/main.py`（挂载 router + 依赖注入 AgentLoop）

**Interfaces:**
- Consumes: `AgentLoop.stream()`（Task 5）、`Settings`（Task 1）
- Produces:
  - `apps/api/app/state.py::state`（dataclass，字段 `agent: AgentLoop | None`、`iot: MockIoTService | None`，可变全局单例）
  - `apps/api/app/state.py::set_agent(agent, iot) -> None`（测试注入用）
  - `POST /api/chat`，请求体 `{"message": str, "session_id": str}`，响应 `text/event-stream`
  - SSE 事件格式（与前端 `apps/web/lib/types.ts` 里的 TS 类型一一对应）：
    - `event: tool_call` / `data: {"id": "...", "name": "...", "arguments": {...}}`
    - `event: tool_result` / `data: {"id": "...", "name": "...", "result": {...}}`
    - `event: text_delta` / `data: {"text": "..."}`
    - `event: error` / `data: {"message": "..."}`
    - `event: done` / `data: {"usage": {...}}`
  - `GET /api/devices`：返回 mock 设备列表（UI 侧边栏用）

- [ ] **Step 1: 写失败测试**

创建 `apps/api/tests/test_chat_endpoint.py`：

```python
import pytest
from fastapi.testclient import TestClient

from app.agent.loop import AgentLoop
from app.agent.tools import ToolRegistry, make_iot_tools
from app.iot.service import MockIoTService
from app.llm.base import LLMResponse, ToolCall
from app.llm.fake import FakeProvider
from app.main import app
from app.state import set_agent


@pytest.fixture
def client():
    return TestClient(app)


def _install_fake_agent(scripted: list[LLMResponse]) -> MockIoTService:
    iot = MockIoTService.with_seed_data()
    reg = ToolRegistry()
    for t in make_iot_tools(iot):
        reg.register(t)
    set_agent(AgentLoop(llm=FakeProvider(responses=scripted), registry=reg), iot)
    return iot


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_devices_endpoint(client):
    _install_fake_agent([])
    r = client.get("/api/devices")
    assert r.status_code == 200
    devices = r.json()
    assert len(devices) >= 4
    assert any(d["id"] == "light-living-1" for d in devices)


def test_chat_sse_emits_events(client):
    scripted = [
        LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="c1", name="turn_on_light", arguments={"room": "客厅", "on": True})],
            usage={},
        ),
        LLMResponse(text="已开灯", tool_calls=[], usage={"total_tokens": 12}),
    ]
    _install_fake_agent(scripted)

    with client.stream(
        "POST",
        "/api/chat",
        json={"message": "把客厅灯打开", "session_id": "s1"},
    ) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        body = "".join(r.iter_text())

    assert "event: tool_call" in body
    assert "event: tool_result" in body
    assert "event: text_delta" in body
    assert "event: done" in body


def test_chat_requires_message(client):
    r = client.post("/api/chat", json={"session_id": "s1"})
    assert r.status_code == 422


def test_chat_without_agent_returns_503(client):
    """未注入 agent 时返回 503 而不是 crash。"""
    from app.state import state

    state.agent = None
    r = client.post("/api/chat", json={"message": "hi", "session_id": "s1"})
    assert r.status_code == 503
```

- [ ] **Step 2: 运行测试确认 FAIL**

```bash
cd apps/api
uv run pytest tests/test_chat_endpoint.py -v
```

Expected: ERROR / 无法 import `app.state` 或 `app.main`

- [ ] **Step 3: 实现 state 模块 + chat router + main 挂载**

创建 `apps/api/app/state.py`：

```python
from dataclasses import dataclass

from app.agent.loop import AgentLoop
from app.iot.service import MockIoTService


@dataclass
class AppState:
    agent: AgentLoop | None = None
    iot: MockIoTService | None = None


# 可变全局单例：router 在请求时读取，测试通过 set_agent 注入
state = AppState()


def set_agent(agent: AgentLoop, iot: MockIoTService) -> None:
    state.agent = agent
    state.iot = iot
```

创建 `apps/api/app/routers/__init__.py`（空文件）

创建 `apps/api/app/routers/chat.py`：

```python
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.state import state

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = Field(min_length=1)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    agent = state.agent
    if agent is None:
        raise HTTPException(status_code=503, detail="agent not initialized")

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for ev in agent.stream(req.message):
                if ev.kind == "tool_call":
                    yield _sse("tool_call", {
                        "id": ev.tool_call_id,
                        "name": ev.tool_name,
                        "arguments": ev.tool_arguments,
                    })
                elif ev.kind == "tool_result":
                    yield _sse("tool_result", {
                        "id": ev.tool_call_id,
                        "name": ev.tool_name,
                        "result": ev.result,
                    })
                elif ev.kind == "text_delta":
                    yield _sse("text_delta", {"text": ev.text})
                elif ev.kind == "error":
                    yield _sse("error", {"message": ev.message})
                elif ev.kind == "done":
                    yield _sse("done", {"usage": ev.usage})
        except Exception as e:  # noqa: BLE001
            yield _sse("error", {"message": f"internal error: {e}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/devices")
async def devices() -> list[dict]:
    iot = state.iot
    if iot is None:
        raise HTTPException(status_code=503, detail="iot not initialized")
    return [d.model_dump() for d in iot.list_devices()]
```

修改 `apps/api/app/main.py` 为：

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.agent.loop import AgentLoop
from app.agent.tools import ToolRegistry, make_iot_tools
from app.config import Settings
from app.iot.service import MockIoTService
from app.llm.deepseek import DeepSeekProvider
from app.routers.chat import router as chat_router
from app.state import set_agent, state


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 启动时初始化默认 agent（DeepSeek + mock IoT）。
    # 测试可以通过 set_agent 在 TestClient 启动前注入 FakeProvider。
    if state.agent is None:
        iot = MockIoTService.with_seed_data()
        registry = ToolRegistry()
        for t in make_iot_tools(iot):
            registry.register(t)
        settings = Settings.from_env()
        # DEEPSEEK_API_KEY 缺失时 DeepSeekProvider 构造抛 ValueError → 启动失败（快速失败）
        agent = AgentLoop(llm=DeepSeekProvider(settings=settings), registry=registry)
        set_agent(agent, iot)
    yield


app = FastAPI(title="HomeFlow Agent API", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(chat_router)
```

**为什么这样设计**（Review Focus #5）：
- **DeepSeekProvider 构造在 lifespan 里**，不在模块顶层 → 测试 import `app.main` 不会崩
- **生产启动时若缺 API key**，lifespan 抛 `ValueError` → uvicorn 启动即失败，错误信息清晰
- **测试通过 `set_agent(...)` 注入 FakeProvider**，绕开 DeepSeek

- [ ] **Step 4: 运行测试确认 PASS**

```bash
cd apps/api
uv run pytest tests/test_chat_endpoint.py -v
```

Expected: 5 个测试全 PASS

- [ ] **Step 5: 手动验证 SSE 断开不泄漏（Review Focus #4）**

```bash
cd apps/api
export DEEPSEEK_API_KEY=sk-test-fake
uv run uvicorn app.main:app --port 8000 &
sleep 2
# 用 curl 触发一次 SSE，1 秒后中断
timeout 1 curl -N -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"把客厅灯打开","session_id":"s1"}' || true
# 检查 uvicorn 进程没崩
kill %1
```

Expected: uvicorn 未输出 traceback，进程优雅退出

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/main.py apps/api/app/state.py apps/api/app/routers apps/api/tests/test_chat_endpoint.py
git commit -m "feat: FastAPI SSE 聊天端点 + 设备列表接口（可注入 agent 状态）"
```

---

## Task 7: Next.js 聊天 UI（流式 + 工具调用可视化）

**Files:**
- Create: `apps/web/lib/types.ts`, `apps/web/lib/api.ts`
- Create: `apps/web/components/Chat.tsx`, `MessageList.tsx`, `MessageInput.tsx`, `ToolCallCard.tsx`
- Modify: `apps/web/app/page.tsx`, `apps/web/app/globals.css`

**Interfaces:**
- Consumes: Task 6 的 SSE 事件格式
- Produces: 可在浏览器打开 `http://localhost:3000`，对话「把客厅灯打开」看到流式输出与工具调用卡片

> **说明**：前端 UI 逻辑薄、状态全在 React 里，M1 用手动验证；M4 再加 Playwright E2E。这符合 Global Constraints。

- [ ] **Step 1: 定义 TS 类型（对应 Task 6 的 SSE 事件）**

创建 `apps/web/lib/types.ts`：

```typescript
export type ToolCallPayload = {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
};

export type ToolResultPayload = {
  id: string;
  name: string;
  result: unknown;
};

export type TextDeltaPayload = { text: string };
export type ErrorPayload = { message: string };
export type DonePayload = { usage: Record<string, number> };

export type AgentEvent =
  | { kind: "tool_call"; data: ToolCallPayload }
  | { kind: "tool_result"; data: ToolResultPayload }
  | { kind: "text_delta"; data: TextDeltaPayload }
  | { kind: "error"; data: ErrorPayload }
  | { kind: "done"; data: DonePayload };

export type ChatItem =
  | { role: "user"; text: string }
  | {
      role: "assistant";
      text: string;
      toolCalls: { call: ToolCallPayload; result?: ToolResultPayload }[];
      error?: string;
    };
```

- [ ] **Step 2: 实现 SSE 客户端**

创建 `apps/web/lib/api.ts`：

```typescript
import type { AgentEvent } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function streamChat(
  message: string,
  sessionId: string,
  onEvent: (e: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`chat failed: ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE 事件以 \n\n 分隔
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const event = parseSseChunk(chunk);
      if (event) onEvent(event);
    }
  }
}

function parseSseChunk(chunk: string): AgentEvent | null {
  let eventName = "";
  let dataLine = "";
  for (const line of chunk.split("\n")) {
    if (line.startsWith("event: ")) eventName = line.slice(7).trim();
    else if (line.startsWith("data: ")) dataLine = line.slice(6);
  }
  if (!eventName || !dataLine) return null;
  const data = JSON.parse(dataLine);
  return { kind: eventName, data } as AgentEvent;
}
```

- [ ] **Step 3: 实现 UI 组件**

创建 `apps/web/components/ToolCallCard.tsx`：

```tsx
"use client";

import type { ToolCallPayload, ToolResultPayload } from "@/lib/types";

export function ToolCallCard({
  call,
  result,
}: {
  call: ToolCallPayload;
  result?: ToolResultPayload;
}) {
  return (
    <div className="tool-card">
      <div className="tool-card-header">
        <span className="tool-icon">🔧</span>
        <code>{call.name}</code>
      </div>
      <pre className="tool-args">{JSON.stringify(call.arguments, null, 2)}</pre>
      {result && (
        <pre className="tool-result">
          {JSON.stringify(result.result, null, 2)}
        </pre>
      )}
    </div>
  );
}
```

创建 `apps/web/components/MessageList.tsx`：

```tsx
"use client";

import type { ChatItem } from "@/lib/types";
import { ToolCallCard } from "./ToolCallCard";

export function MessageList({ items }: { items: ChatItem[] }) {
  return (
    <div className="message-list">
      {items.map((item, i) => (
        <div key={i} className={`message message-${item.role}`}>
          {item.role === "user" ? (
            <div className="bubble bubble-user">{item.text}</div>
          ) : (
            <div className="bubble bubble-assistant">
              {item.toolCalls.map((tc, j) => (
                <ToolCallCard key={j} call={tc.call} result={tc.result} />
              ))}
              {item.text && <div className="assistant-text">{item.text}</div>}
              {item.error && <div className="assistant-error">⚠️ {item.error}</div>}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

创建 `apps/web/components/MessageInput.tsx`：

```tsx
"use client";

import { useState } from "react";

export function MessageInput({
  disabled,
  onSend,
}: {
  disabled: boolean;
  onSend: (text: string) => void;
}) {
  const [value, setValue] = useState("");
  return (
    <form
      className="message-input-form"
      onSubmit={(e) => {
        e.preventDefault();
        const trimmed = value.trim();
        if (!trimmed || disabled) return;
        onSend(trimmed);
        setValue("");
      }}
    >
      <input
        className="message-input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="试着说「把客厅灯打开」"
        disabled={disabled}
        autoFocus
      />
      <button className="send-button" type="submit" disabled={disabled || !value.trim()}>
        发送
      </button>
    </form>
  );
}
```

创建 `apps/web/components/Chat.tsx`：

```tsx
"use client";

import { useState } from "react";
import { streamChat } from "@/lib/api";
import type { AgentEvent, ChatItem } from "@/lib/types";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

export function Chat() {
  const [items, setItems] = useState<ChatItem[]>([]);
  const [busy, setBusy] = useState(false);

  async function handleSend(text: string) {
    setBusy(true);
    const userItem: ChatItem = { role: "user", text };
    // 先放一个空的 assistant item，事件流里逐步填充
    setItems((prev) => [...prev, userItem, { role: "assistant", text: "", toolCalls: [] }]);

    function patchLastAssistant(patch: (a: Extract<ChatItem, { role: "assistant" }>) => Extract<ChatItem, { role: "assistant" }>) {
      setItems((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last && last.role === "assistant") {
          next[next.length - 1] = patch(last);
        }
        return next;
      });
    }

    try {
      await streamChat(text, "session-1", (e: AgentEvent) => {
        if (e.kind === "tool_call") {
          patchLastAssistant((a) => ({
            ...a,
            toolCalls: [...a.toolCalls, { call: e.data }],
          }));
        } else if (e.kind === "tool_result") {
          patchLastAssistant((a) => ({
            ...a,
            toolCalls: a.toolCalls.map((tc) =>
              tc.call.id === e.data.id ? { ...tc, result: e.data } : tc,
            ),
          }));
        } else if (e.kind === "text_delta") {
          patchLastAssistant((a) => ({ ...a, text: a.text + (e.data.text ?? "") }));
        } else if (e.kind === "error") {
          patchLastAssistant((a) => ({ ...a, error: e.data.message }));
        }
      });
    } catch (err) {
      patchLastAssistant((a) => ({
        ...a,
        error: err instanceof Error ? err.message : "stream error",
      }));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat">
      <header className="chat-header">
        <h1>HomeFlow Agent</h1>
        <p className="subtitle">M1 checkpoint · 对话控制智能设备</p>
      </header>
      <MessageList items={items} />
      <MessageInput disabled={busy} onSend={handleSend} />
    </div>
  );
}
```

- [ ] **Step 4: 挂到 page 并加最小样式**

修改 `apps/web/app/page.tsx`：

```tsx
import { Chat } from "@/components/Chat";

export default function Home() {
  return (
    <main>
      <Chat />
    </main>
  );
}
```

替换 `apps/web/app/globals.css` 为：

```css
* {
  box-sizing: border-box;
}
html,
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #f7f7f8;
  color: #1a1a1a;
}
.chat {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px 16px 96px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.chat-header h1 {
  margin: 0;
  font-size: 20px;
}
.subtitle {
  color: #6b6b70;
  font-size: 13px;
  margin-top: 4px;
}
.message-list {
  flex: 1;
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.message {
  display: flex;
}
.message-user {
  justify-content: flex-end;
}
.bubble {
  max-width: 80%;
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.55;
  white-space: pre-wrap;
}
.bubble-user {
  background: #2f6fed;
  color: #fff;
}
.bubble-assistant {
  background: #fff;
  border: 1px solid #e5e5e7;
}
.assistant-text {
  margin-top: 4px;
}
.assistant-error {
  color: #b42318;
  margin-top: 8px;
  font-size: 13px;
}
.tool-card {
  background: #f4f4f6;
  border-radius: 8px;
  padding: 10px;
  margin: 6px 0;
  font-size: 12px;
}
.tool-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  margin-bottom: 6px;
}
.tool-args,
.tool-result {
  margin: 4px 0 0;
  padding: 6px;
  background: #fff;
  border-radius: 4px;
  overflow-x: auto;
}
.message-input-form {
  display: flex;
  gap: 8px;
  padding: 12px;
  background: #fff;
  border-top: 1px solid #e5e5e7;
}
.message-input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #d0d0d5;
  border-radius: 8px;
  font-size: 14px;
}
.send-button {
  padding: 10px 16px;
  background: #2f6fed;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}
.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

- [ ] **Step 5: 手动验证 UI**

```bash
# 终端 1：起后端（DeepSeek API key 要真实）
cd apps/api
cp .env.example .env  # 填入真实 DEEPSEEK_API_KEY
uv run uvicorn app.main:app --port 8000

# 终端 2：起前端
cd apps/web
pnpm dev
```

浏览器打开 `http://localhost:3000`，输入「把客厅灯打开」，Expected：
- 用户气泡显示「把客厅灯打开」
- 出现工具卡片（🔧 turn_on_light，参数里 room=客厅）
- 卡片下出现工具结果（`"on": true`）
- 最后流式出现中文回复
- 后端 Mock IoT 里 `light-living-1.state.on === true`（可在 Task 6 的 `/api/devices` 里 curl 验证）

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat: Next.js 流式聊天 UI + 工具调用可视化卡片"
```

---

## Task 8: E2E checkpoint + README + 学习笔记占位

**Files:**
- Modify: `README.md`（新写）
- Create: `docs/learning/m1-notes.md`

**Interfaces:**
- Consumes: 前面所有任务
- Produces: 一份外人能照着跑起来的 README + 用户自己的学习笔记模板

- [ ] **Step 1: 写 README**

创建 `README.md`：

```markdown
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
cp ../.env.example .env   # 填入 DEEPSEEK_API_KEY
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
```

- [ ] **Step 2: 学习笔记模板（用户自己填）**

创建 `docs/learning/m1-notes.md`：

```markdown
# M1 学习笔记

> 这份笔记是**面试复习材料**的原料。每学一个概念就写一段自己的话，别抄书。

## Function Calling 原理

（用自己的话写：工具 schema 是怎么进 prompt 的？模型输出的是什么？为什么 JSON 格式很重要？）

## Prompt 工程

（工具的 description 写多详细？改一个字会怎样？试过什么例子？）

## 流式（SSE）

（为什么选 SSE 不选 WebSocket？服务端怎么生成事件流？客户端中途断开会怎样？）

## 手写 Agent Loop

（LLM 返回 tool_calls 时消息历史怎么拼？为什么需要 `role: "tool"` 的消息？`max_iterations` 为什么必须有？）

## 遇到的坑

（记录 bug、奇怪行为、查过的资料）

## 面试可能问的问题 + 我的答案

1. Q: Function calling 是怎么实现的？
   A: （自己写）

2. Q: 为什么不用 LangChain？
   A: （提示：M1 想理解原理，M3 会用 LangGraph）

3. Q: 工具调用失败了怎么办？
   A: （提示：看 `AgentLoop._execute_tool`）
```

- [ ] **Step 3: 走一遍 M1 checkpoint demo（完整端到端）**

```bash
# 起后端、前端（同 Task 7 Step 5）
# 浏览器里依次输入：
# 1. 把客厅灯打开
# 2. 把卧室温度调到 22 度
# 3. 关掉客厅的灯
# 验证：
# - 每次都有工具卡片 + 结果 + 中文回复
# - http://localhost:8000/api/devices 里设备状态真的变了
```

Expected: 3 条对话全部走通，UI 展示工具调用，设备状态正确变化。

- [ ] **Step 4: Commit**

```bash
git add README.md docs/learning
git commit -m "docs: M1 checkpoint README + 学习笔记模板"
```

- [ ] **Step 5: 标签 M1 完成**

```bash
git tag -a m1-checkpoint -m "M1 checkpoint: Agent 骨架可演示"
```

---

## 完成后

M1 结束时，用户拥有：

1. 一个能对话控制设备的可演示 demo
2. 完整的 pytest 覆盖（配置、IoT、LLM、工具、agent loop、端点）
3. 每个 Review Focus 风险都有对应测试或手动验证
4. 一份学习笔记模板（面试材料原料）
5. Git 历史：每个 Task 一个 commit，方便回看

**下一步**：M2 写新计划（RAG + 上下文工程 + pgvector + Redis），在 M1 基础上叠加。
