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
