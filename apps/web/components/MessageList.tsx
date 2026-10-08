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
