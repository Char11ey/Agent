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
