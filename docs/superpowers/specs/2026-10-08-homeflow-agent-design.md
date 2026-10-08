# HomeFlow Agent — 设计文档

- **日期**：2026-10-08
- **目标**：6 个月内从 JS 前端转型到 Agent/AI 岗位，产出一个能作为面试作品集的完整 Agent 项目
- **形态**：单一产品做深（方案 A）+ 递进式 checkpoint
- **主题**：智能家居对话中枢（自然语言控制 IoT + 多步任务编排）

---

## 1. 背景与目标

### 1.1 背景

- 用户是 JS 方向前端工程师，现职做小米 MIoT 相关的 React Native 插件开发（含智能音箱场景）
- 已有 LLM 小 demo 基础（function calling、简单 RAG、LangChain 或类似框架、MCP 均有玩具级实践）
- 对前端行业前景感到担忧，决定转向 Agent 全栈方向

### 1.2 成功标准（可衡量）

- 6 个月内开始投递 Agent/AI 岗位并进入面试
- 有一个面试官看了想深挖的 GitHub 项目（HomeFlow Agent）
- 面试中能对每个技术决策给出「为什么选 X，为什么不选 Y」的反事实答案
- 简历从「实现 XX 页面」改写为「设计 XX Agent 系统，实现 XX 指标」

### 1.3 非目标（YAGNI）

- 不做真实 IoT 协议对接（不做米家私有协议 / MQTT / Zigbee），用 mock 设备层模拟
- 不做语音输入输出（只做文本对话）
- 不做多用户 SaaS（只做单用户 + 本地/单机部署）
- 不做移动端原生 App（Web 响应式即可）
- 不做算法层创新（不训模型、不做新 embedding 方法）

---

## 2. 产品定义

### 2.1 一句话

用户用自然语言下达复杂意图（「睡觉了」「我回家了」「明天早上提醒我带伞，顺便把客厅温度调到 26 度」），agent 理解、拆解、编排多个设备/服务完成，并支持追问和纠错。

### 2.2 核心用户场景（3 个）

| # | 场景 | 意图复杂度 | 考验的技术 |
|---|------|-----------|-----------|
| 1 | 单设备控制（"把客厅灯打开"） | 低 | Tool Use、实体解析（"客厅的灯"→device_id） |
| 2 | 复合场景（"睡觉了"） | 中 | 任务分解、多工具编排、确认与回滚 |
| 3 | 带记忆的连续对话（"刚才那个温度再高一点"） | 高 | 多轮上下文、指代消解、用户偏好记忆（RAG） |

### 2.3 用户画像

单人使用（面试演示 + 自用），身份：开发者。不做多租户。

---

## 3. 技术架构

### 3.1 技术栈定稿

| 层 | 选型 | 关键理由（面试话术素材） |
|----|------|---------------------|
| 前端 | Next.js 15 + TypeScript + Vercel AI SDK | 流式渲染、tool call 可视化、SSE 原理 |
| API 网关 | FastAPI | 异步流式、依赖注入、OpenAPI 自动生成 |
| Agent 编排 | LangGraph | 状态图 vs 简单循环、checkpoint、human-in-the-loop |
| 工具层 | LangChain Tools / 自定义 | 工具描述即 prompt、结构化输出 |
| 向量库 | PostgreSQL + pgvector | 事务一致、运维简单、规模不大时性能足够 |
| 短期记忆 | Redis | 会话对话历史、TTL、上下文窗口裁剪 |
| LLM Provider | DeepSeek / Qwen / OpenAI 兼容抽象层 | 成本、降级、切换 |
| 可观测 | Langfuse（自部署） | trace、token 成本、评估链路 |
| Mock IoT | FastAPI 内独立 service 层 | 边界隔离、可测试、不依赖真实协议 |
| 部署 | Docker Compose + 云（Railway / Fly.io / 阿里云） | 一键起、可演示 |

### 3.2 系统结构（目标终态，M4 达成）

> 说明：下图为项目**最终形态**。M1 起步时只有单 Agent + 2 个工具；场景编排、记忆、追问等节点在 M2-M3 逐步加入。

```
┌─────────────────────────────────────────────┐
│  Next.js Chat UI (TS)                       │
│  流式渲染 · 工具调用可视化 · 设备状态面板        │
└──────────────────┬──────────────────────────┘
                   │ SSE + REST
┌──────────────────▼──────────────────────────┐
│  FastAPI Gateway                            │
│  auth · session · streaming · rate limit    │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  LangGraph Agent Core (状态图)                │
│                                             │
│  ┌──────────┐   ┌──────────┐   ┌─────────┐  │
│  │ 理解意图  │──▶│ 规划/分解 │──▶│ 执行循环 │  │
│  └──────────┘   └──────────┘   └────┬────┘  │
│                                     │       │
│       ┌─────────────┬───────────────┼────┐  │
│       ▼             ▼               ▼    ▼  │
│   device_ctl   scene_executor   memory  ask │
│       │             │               │    │  │
└───────┼─────────────┼───────────────┼────┼──┘
        ▼             ▼               ▼    │
┌────────────┐ ┌────────────┐  ┌─────────┐ │
│ Mock IoT   │ │ Scene Store│  │ pgvector│ │
│ 设备状态机   │ │ 场景编排表  │  │ 偏好记忆 │ │
└────────────┘ └────────────┘  └─────────┘ │
                                            │
        Redis (会话) · Langfuse (trace) ◀───┘
```

### 3.3 项目目录结构

```
homeflow-agent/
├── apps/
│   ├── web/                # Next.js 前端
│   └── api/                # FastAPI 后端
├── packages/
│   └── shared/             # TS 类型定义（OpenAPI 生成）
├── infra/
│   ├── docker-compose.yml  # pg + redis + langfuse + api + web
│   └── migrations/
├── evals/                  # 评估用例与脚本（贯穿全程）
├── docs/
│   ├── learning/           # 每阶段学习笔记（面试复习材料）
│   ├── adr/                # 架构决策记录
│   └── superpowers/specs/  # 设计文档（本文件）
└── README.md
```

### 3.4 关键架构决策（面试叙事素材）

每个决策都要准备「为什么选 X，为什么不选 Y」：

1. **LangGraph 而非手写循环**：状态可持久化（断点续跑）、human-in-the-loop（"确认关掉所有灯？"）、可视化调试
2. **pgvector 而非独立向量库**：设备状态、场景、记忆放同一事务；规模不大时性能足够；运维简单
3. **Mock IoT 层独立**：agent 依赖的是「设备能力接口」而非具体协议——这是所有真实 IoT Agent 的标准做法
4. **Provider 抽象层**：DeepSeek/Qwen/OpenAI 三家一键切换，方便对比效果和成本
5. **SSE 而非 WebSocket**：单向流式足够、代理/CDN 友好、连接恢复简单

---

## 4. 阶段划分与 Checkpoint

6 个月切成 4 个阶段（M1-M4），每阶段产出一个**可演示的 checkpoint**，同时对应简历上的一个 bullet。

### M1（月 1-2，8 周）：Agent 骨架 —— 「让 LLM 能动手」

- **学**：LLM API、Prompt 工程、Function Calling 原理、流式（SSE）、FastAPI 基础、Python 起步（用 TS 经验类比）
- **建**：
  - FastAPI 项目骨架
  - 单 Agent + 2 个工具（`turn_on_light`、`set_temperature`）
  - Next.js 流式对话 UI（含工具调用过程可视化）
  - LLM Provider 抽象层（M1 内定下首发 provider：DeepSeek 或 Qwen，以成本与效果实测为准）
- **Checkpoint**：对话「把客厅灯打开」→ 灯真的开了，UI 上能看到工具调用过程
- **面试话术**：「Function calling 的本质是把工具 schema 塞进 prompt，模型输出结构化 JSON，我再路由执行」

### M2（月 3，4 周）：上下文工程 + RAG —— 「让 Agent 记得、懂你」

- **学**：Embedding、向量检索、chunking、rerank、上下文窗口管理、prompt 缓存
- **建**：
  - pgvector 偏好记忆
  - 实体解析（"客厅的灯" → device_id）
  - 多轮指代消解（"刚才那个温度再高一点"）
- **Checkpoint**：跨 5 轮对话后说「再高一点」，agent 能接上
- **面试话术**：「RAG 不只是查相似，还要处理实体歧义、时效性、评估检索质量」

### M3（月 4，4 周）：LangGraph + 评估 —— 「让 Agent 靠谱」

- **学**：LangGraph 状态图、checkpoint、human-in-the-loop、多 Agent、评估方法论、Langfuse
- **建**：
  - 复合场景编排（"睡觉了" → 关灯 + 关空调 + 设闹钟）
  - 确认与回滚
  - **evals 套件**（50+ 用例）
  - Langfuse trace 上报
- **Checkpoint**：跑一遍 evals 输出质量报告 + Langfuse 里能看到完整 trace
- **面试话术**：「Agent 没有测试就像盲飞，我用 golden dataset + LLM-as-judge + 工具调用正确率三层评估」

### M4（月 5-6，8 周）：产品化 + 面试冲刺 —— 「能拿去卖」

- **学**：FastAPI 鉴权、Docker 部署、压测、成本监控、流式优化
- **建**：
  - JWT 登录（即使单用户也做，目的是展示鉴权能力；不做多租户/权限体系）
  - 部署上云（Railway / Fly.io / 阿里云，三选一）
  - 压测（50 并发）
  - 成本监控面板
  - 完整 README + 架构文档 + 3 分钟演示视频
- **Checkpoint**：公网上能访问的 demo + 一份面试官看了会想聊的 README
- **面试冲刺**：简历改写、项目讲稿（5 分钟版 + 15 分钟版）、深挖问答库（50 问 50 答）

### 4.1 每周节奏（工作日业余）

- 工作日 5 个晚上 × 1-2h：学概念 + 记笔记（笔记直接变成面试复习材料）
- 周末 4-6h：写代码、做 checkpoint
- 每月最后一个周末：复盘 + 演示 checkpoint 给朋友/同事看（练习讲项目）

---

## 5. 测试与评估策略

| 类型 | 什么时候做 | 工具 |
|------|-----------|------|
| 单元测试 | M1 起，每个工具都要 | pytest + pytest-asyncio |
| Agent 行为测试 | M2 起，RAG 效果 | golden dataset + 对比脚本 |
| 端到端评估 | M3 起，每次 prompt/图改动 | `evals/` 目录，LLM-as-judge + 规则断言 |
| 前端 E2E | M4 | Playwright 跑核心对话流 |
| 压测 | M4 | locust / k6 |

**面试价值**：大部分候选人简历写「用 LangChain 做了 RAG」，而能说出「我写了 evals 套件，检索命中率从 62% 优化到 89%」就是差异化。

---

## 6. 作品呈现（面向面试）

1. **GitHub 仓库**：干净 README（架构图 + GIF 演示 + 决策记录 ADR）
2. **演示视频**（3 分钟）：核心场景跑通 + trace 展示
3. **博客 3-5 篇**（掘金 / 知乎 / Medium）：「从 0 到 1 做一个 IoT Agent」「RAG 在实体解析上的坑」等
4. **简历改写**：从「实现 XX 页面」转为「设计 XX Agent 系统，实现 XX 指标」
5. **面试问答库**：每个技术决策都要有「为什么不用 X」的反事实答案

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 工作忙，学不动 | 进度延迟 | 每周节奏弹性化，允许 M1-M2 合并拉长 |
| LangGraph 版本迭代快 | 知识过时 | 锁版本 + 关注官方 changelog，面试强调「原理而非 API」 |
| 6 个月后市场变化 | 目标岗位收缩 | 每月做一次市场扫描，动态调整 M4 面试冲刺方向 |
| Python 后端不熟 | 写得慢 | M1 前 2 周先补 Python + FastAPI 基础（用你 TS 的经验做类比） |
| 项目做浅了 | 面试深挖扛不住 | 每个决策写 ADR，强制自己写「为什么不选 X」 |

---

## 8. 术语速查（面试复习）

- **Function Calling**：把工具 schema 塞进 prompt，模型输出结构化 JSON，由外部执行
- **RAG**：Retrieval-Augmented Generation，先检索再生成，减少幻觉、支持私有知识
- **LangGraph**：LangChain 团队的状态图 Agent 编排框架，支持 checkpoint、human-in-the-loop
- **pgvector**：PostgreSQL 的向量扩展，支持相似度检索
- **SSE**：Server-Sent Events，单向流式 HTTP，适合 LLM token 流
- **LLM-as-judge**：用强模型给弱模型/agent 输出打分，用于评估
- **Human-in-the-loop**：Agent 在关键决策点暂停等用户确认
- **Checkpoint（LangGraph）**：Agent 状态可持久化，可恢复执行
- **ADR**：Architecture Decision Record，架构决策记录
- **MCP**：Model Context Protocol，模型上下文协议，工具/数据源的统一接入标准

---

## 附录 A：相关背景

- 用户现有 demo 练手目录：`/Users/liuliangjie/agent-learning/`（01-05 JS 脚本 + chat-app）
- 用户工作：小米 MIoT RN 插件开发（含智能音箱相关）
- 项目创建日期：2026-10-08
