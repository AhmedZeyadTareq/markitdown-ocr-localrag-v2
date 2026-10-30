"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { DocSummary, Source, Version } from "@/lib/api";
import { readableLog } from "@/lib/blocks";

export type Message = {
  role: "user" | "assistant";
  text: string;
  version: Version;
  sources?: Source[];
  pending?: boolean;
  note?: string;
  error?: string;
};

type Props = {
  doc: DocSummary | null;
  version: Version;
  hasText: boolean;
  busy: boolean;
  messages: Message[];
  onAsk: (question: string) => void;
  onShowPassage: (sources: Source[], passage: number, version: Version) => void;
};

export function ChatPanel({ doc, version, hasText, busy, messages, onAsk, onShowPassage }: Props) {
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const pending = messages.some((m) => m.pending);
  const canAsk = !!doc && hasText && !busy && !pending;

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  const submit = () => {
    const question = draft.trim();
    if (!question || !canAsk) return;
    onAsk(question);
    setDraft("");
  };

  let blockedReason: string | null = null;
  if (!doc) blockedReason = "Pick a document to ask about it.";
  else if (busy) blockedReason = "You can ask questions once reading finishes.";
  else if (!hasText)
    blockedReason = version === "organized" ? "Organize the text first, or switch to the extracted text." : "Read the document first.";

  return (
    <section aria-label="Questions" className="flex min-h-[28rem] flex-col border-line bg-sheet lg:min-h-0 lg:border-l">
      <header className="border-b border-line px-6 py-4">
        <h2 className="text-lg font-semibold">Ask this document</h2>
        <p className="text-sm text-muted">
          Answers use only the {version === "raw" ? "extracted text" : "organized version"}, and the passages they come from get
          highlighted.
        </p>
      </header>

      <div className="min-h-0 flex-1 space-y-7 overflow-y-auto px-6 py-6">
        {messages.length === 0 && !blockedReason && (
          <p className="font-serif text-muted">
            Try asking for a name, a number, a date, or a summary of a section.
          </p>
        )}
        {messages.map((message, i) =>
          message.role === "user" ? (
            <p key={i} className="font-semibold">
              {message.text}
            </p>
          ) : (
            <Answer key={i} message={message} onShowPassage={onShowPassage} />
          ),
        )}
        <div ref={endRef} />
      </div>

      <form
        className="border-t border-line p-4"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        {blockedReason && <p className="mb-2 text-sm text-muted">{blockedReason}</p>}
        <div className="flex items-end gap-2 rounded-xl border border-line bg-paper/50 p-2 focus-within:border-moss">
          <label htmlFor="question" className="sr-only">
            Your question
          </label>
          <textarea
            id="question"
            rows={2}
            value={draft}
            disabled={!canAsk && !pending}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Who signed the contract?"
            className="max-h-40 min-h-[2.75rem] flex-1 resize-none bg-transparent px-2 py-1.5 outline-none focus-visible:outline-none placeholder:text-muted/70 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!canAsk || !draft.trim()}
            className="rounded-lg bg-moss px-4 py-2 font-semibold text-sheet hover:bg-moss-deep disabled:opacity-40"
          >
            Ask
          </button>
        </div>
      </form>
    </section>
  );
}

function Answer({ message, onShowPassage }: { message: Message; onShowPassage: Props["onShowPassage"] }) {
  const waiting = message.pending && !message.text;
  return (
    <div className="border-l-2 border-line pl-4">
      {message.error ? (
        <p className="text-danger">{message.error}</p>
      ) : waiting ? (
        <p className="text-sm text-muted">{message.note ? readableLog(message.note).text : "Searching the document…"}</p>
      ) : (
        <div className="sheet-prose space-y-3 text-[1rem]">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
          {message.pending && <span aria-hidden className="answer-caret inline-block h-4 w-[2px] translate-y-0.5 bg-moss" />}
        </div>
      )}

      {message.sources && message.sources.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-muted">From passages</span>
          {message.sources.map((source, p) => (
            <button
              key={p}
              type="button"
              onClick={() => onShowPassage(message.sources!, p + 1, message.version)}
              title={source.text.slice(0, 160)}
              className="min-w-6 rounded bg-mark/50 px-1.5 py-0.5 font-semibold hover:bg-mark"
            >
              {p + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
