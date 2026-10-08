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
