"use client";

import type { DocSummary, Status } from "@/lib/api";
import { ModelPicker } from "./ModelPicker";

const relativeTime = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

function ago(iso: string) {
  const seconds = (new Date(iso).getTime() - Date.now()) / 1000;
  const steps: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31536000],
    ["month", 2592000],
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [unit, size] of steps) {
    if (Math.abs(seconds) >= size) return relativeTime.format(Math.round(seconds / size), unit);
  }
  return "just now";
}

function stateLabel(doc: DocSummary) {
  if (doc.has_organized) return "Organized";
  if (doc.has_raw) return "Extracted";
  return "Not read yet";
}

type Props = {
  docs: DocSummary[];
  selectedId: string | null;
  status: Status | null;
  serverError: string | null;
  busyDocId: string | null;
  canAdd: boolean;
  onAdd: () => void;
  onSelect: (id: string) => void;
  onDelete: (doc: DocSummary) => void;
  onRetryServer: () => void;
  onChooseModel: (model: string) => Promise<void>;
};

export function Library({ docs, selectedId, status, serverError, busyDocId, canAdd, onAdd, onSelect, onDelete, onRetryServer, onChooseModel }: Props) {
  return (
    <aside className="flex min-h-0 flex-col border-line bg-paper lg:border-r">
      <header className="px-5 pt-6 pb-4">
        <h1 className="text-[1.6rem] leading-[1.1] font-bold tracking-tight">MarkItDown OCR LocalRAG</h1>
        <p className="mt-2 text-sm text-muted">Your documents, read on this computer.</p>
      </header>

      <div className="px-5 pb-4">
        <button
          type="button"
          onClick={onAdd}
          disabled={!canAdd}
          className="w-full rounded-lg bg-moss px-4 py-2.5 text-left font-semibold text-sheet transition-colors hover:bg-moss-deep disabled:cursor-not-allowed disabled:opacity-50"
        >
          Add documents
          <span className="block text-xs font-normal opacity-80">or drop files anywhere</span>
        </button>
      </div>

      <nav aria-label="Library" className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
        {docs.length === 0 ? (
          <p className="px-2 text-sm text-muted">Nothing here yet. Add a PDF, Word file, slide deck, spreadsheet, or image.</p>
        ) : (
          <ul className="space-y-0.5">
            {docs.map((doc) => {
              const active = doc.id === selectedId;
              const busy = doc.id === busyDocId;
              return (
                <li key={doc.id} className="group relative">
                  <button
                    type="button"
                    onClick={() => onSelect(doc.id)}
                    aria-current={active ? "page" : undefined}
                    className={`w-full rounded-md py-2 pr-16 pl-3 text-left transition-colors ${
                      active ? "bg-sheet shadow-[inset_3px_0_0_var(--color-moss)]" : "hover:bg-sheet/60"
                    }`}
                  >
                    <span className="block truncate font-medium">{doc.filename}</span>
                    <span className="block text-xs text-muted">
                      {busy ? <span className="text-moss">Reading now…</span> : `${stateLabel(doc)}, ${ago(doc.updated_at)}`}
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(doc)}
                    disabled={busy}
                    aria-label={`Delete ${doc.filename}`}
                    className="absolute top-1/2 right-2 -translate-y-1/2 rounded px-2 py-1 text-xs text-muted opacity-0 transition-opacity group-hover:opacity-100 hover:text-danger focus-visible:opacity-100 disabled:hidden"
                  >
                    Delete
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </nav>

      <footer className="border-t border-line px-5 py-4 text-xs">
        {serverError ? (
          <div className="text-danger">
            <p>{serverError}</p>
            <button type="button" onClick={onRetryServer} className="mt-1 font-semibold underline">
              Check again
            </button>
          </div>
        ) : (
          <ModelPicker status={status} disabled={!!busyDocId} onChoose={onChooseModel} onRetry={onRetryServer} />
        )}
      </footer>
    </aside>
  );
}
