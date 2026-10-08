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
