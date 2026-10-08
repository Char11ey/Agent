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
