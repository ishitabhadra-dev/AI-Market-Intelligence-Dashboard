import { useEffect, useRef, useState } from "react";
import { Streamlit } from "streamlit-component-lib";
import type { Article, ChatMessage } from "../types";

interface Props {
  messages?: ChatMessage[];
  examples?: string[];
  placeholder?: string;
  answer?: string;
  sources?: string[];
  evidence?: Article[];
}

export function MarketAgent({
  messages = [],
  examples = [],
  placeholder = "Ask about market themes, risks, or sectors…",
  answer = "",
  sources = [],
  evidence = [],
}: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const displayMessages: ChatMessage[] = [...messages];
  if (answer && !displayMessages.some((m) => m.role === "assistant" && m.content === answer)) {
    displayMessages.push({ role: "assistant", content: answer });
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    const base = 200 + displayMessages.length * 80 + evidence.length * 40;
    Streamlit.setFrameHeight(Math.min(680, base));
  }, [displayMessages.length, evidence.length, answer]);

  const send = (text: string) => {
    const q = text.trim();
    if (!q) return;
    // Unique eventId so Streamlit only processes this click once (avoids rerun loops).
    Streamlit.setComponentValue({
      action: "ask",
      question: q,
      eventId: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      ts: Date.now(),
    });
    setInput("");
  };

  return (
    <div className="mi-root mi-agent">
      <div className="mi-chat">
        {displayMessages.length === 0 && (
          <div className="mi-chat-empty">
            <p>Ask grounded questions over your ingested news corpus.</p>
            {examples.length > 0 && (
              <div className="mi-examples">
                {examples.map((ex) => (
                  <button
                    key={ex}
                    type="button"
                    className="mi-example-btn"
                    onClick={() => send(ex)}
                  >
                    {ex}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {displayMessages.map((m, i) => (
          <div key={`${m.role}-${i}`} className={`mi-bubble ${m.role}`}>
            <span className="mi-bubble-role">{m.role === "user" ? "You" : "Agent"}</span>
            <div className="mi-bubble-body">{m.content}</div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="mi-agent-input-row">
        <textarea
          className="mi-textarea"
          value={input}
          placeholder={placeholder}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(input);
            }
          }}
        />
        <button type="button" className="mi-btn" onClick={() => send(input)} disabled={!input.trim()}>
          Ask
        </button>
      </div>

      {sources.length > 0 && (
        <div className="mi-sources">
          <p className="mi-label">Sources</p>
          <ul>
            {sources.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {evidence.length > 0 && (
        <div className="mi-evidence">
          <p className="mi-label">Retrieved evidence ({evidence.length})</p>
          {evidence.map((a, i) => (
            <div key={a.id ?? i} className="mi-evidence-item">
              <strong>#{i + 1}</strong> {a.title}
              <span className="mi-meta-text"> — {a.source}</span>
            </div>
          ))}
        </div>
      )}

      <style>{`
        .mi-agent { display: flex; flex-direction: column; gap: 0.75rem; }
        .mi-chat {
          max-height: 320px;
          overflow-y: auto;
          padding: 0.5rem;
          background: rgba(10,15,28,0.5);
          border: 1px solid var(--border);
          border-radius: 12px;
        }
        .mi-chat-empty { color: var(--muted); font-size: 0.9rem; padding: 0.5rem; }
        .mi-examples { display: flex; flex-direction: column; gap: 0.4rem; margin-top: 0.75rem; }
        .mi-example-btn {
          text-align: left;
          background: rgba(79,140,255,0.1);
          border: 1px solid var(--border);
          color: var(--text);
          border-radius: 8px;
          padding: 0.5rem 0.75rem;
          font-size: 0.82rem;
          cursor: pointer;
        }
        .mi-example-btn:hover { border-color: var(--accent); }
        .mi-bubble {
          margin-bottom: 0.65rem;
          padding: 0.65rem 0.85rem;
          border-radius: 12px;
          max-width: 95%;
        }
        .mi-bubble.user {
          background: rgba(79,140,255,0.15);
          margin-left: auto;
          border: 1px solid rgba(79,140,255,0.25);
        }
        .mi-bubble.assistant {
          background: rgba(16,185,129,0.08);
          border: 1px solid rgba(16,185,129,0.2);
        }
        .mi-bubble-role {
          font-size: 0.65rem;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: var(--muted);
        }
        .mi-bubble-body {
          margin-top: 0.35rem;
          font-size: 0.9rem;
          line-height: 1.5;
          white-space: pre-wrap;
        }
        .mi-agent-input-row {
          display: flex;
          gap: 0.5rem;
          align-items: flex-end;
        }
        .mi-agent-input-row .mi-textarea { flex: 1; }
        .mi-sources ul, .mi-evidence { margin: 0; padding-left: 1.1rem; font-size: 0.82rem; color: var(--muted); }
        .mi-evidence-item { margin-bottom: 0.35rem; }
      `}</style>
    </div>
  );
}
