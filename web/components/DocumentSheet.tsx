"use client";

import { useEffect, useMemo, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { DocSummary, Version } from "@/lib/api";
import { passagesByBlock, readableLog, toBlocks } from "@/lib/blocks";
import type { Focus, Job } from "./Workspace";

type Props = {
  doc: DocSummary | null;
  version: Version;
  onVersionChange: (v: Version) => void;
  text: string | undefined;
  textError: string | null;
  job: Job | null;
  otherJobRunning: boolean;
  focus: Focus | null;
  onAdd: () => void;
  onExtract: () => void;
  onReorganize: () => void;
  onDismissJob: () => void;
};

const VERSION_LABELS: Record<Version, string> = { raw: "Extracted text", organized: "Organized" };

export function DocumentSheet(props: Props) {
  const { doc, version, onVersionChange, job, otherJobRunning, onExtract, onReorganize } = props;

  if (!doc) {
    return (
      <main className="flex min-h-[60vh] items-center justify-center p-8">
        <button
          type="button"
          onClick={props.onAdd}
          className="max-w-md rounded-xl border-2 border-dashed border-line px-10 py-14 text-center transition-colors hover:border-moss"
        >
          <span className="block text-2xl font-semibold">Drop a document to read it here</span>
          <span className="mt-3 block font-serif text-muted">
            PDFs, Word files, slide decks, spreadsheets, and scanned images. Text inside pictures is read too, and nothing
            leaves this computer.
          </span>
        </button>
      </main>
    );
  }

  const busy = !!job && !job.error;
  const blocked = busy || otherJobRunning;

  return (
    <main className="flex min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 border-b border-line px-6 py-4 lg:px-10">
        <h2 className="min-w-0 basis-full truncate text-xl font-semibold sm:basis-auto sm:flex-1" title={doc.filename}>
          {doc.filename}
        </h2>

        <div role="tablist" aria-label="Version" className="flex rounded-lg bg-line/60 p-0.5 text-sm">
          {(Object.keys(VERSION_LABELS) as Version[]).map((v) => (
            <button
              key={v}
              type="button"
              role="tab"
              aria-selected={version === v}
              onClick={() => onVersionChange(v)}
              className={`rounded-md px-3 py-1 transition-colors ${
                version === v ? "bg-sheet font-semibold shadow-sm" : "text-muted hover:text-ink"
              }`}
            >
              {VERSION_LABELS[v]}
            </button>
          ))}
        </div>

        <div className="flex gap-2 text-sm">
          {doc.has_raw && (
            <button
              type="button"
              onClick={onReorganize}
              disabled={blocked}
              className="rounded-lg border border-line bg-sheet px-3 py-1.5 font-medium hover:border-moss disabled:opacity-50"
              title="Have the local model restructure the text into clean Markdown"
            >
              {doc.has_organized ? "Organize again" : "Organize text"}
            </button>
          )}
          {doc.can_extract && (
            <button
              type="button"
              onClick={onExtract}
              disabled={blocked}
              className="rounded-lg border border-line bg-sheet px-3 py-1.5 font-medium hover:border-moss disabled:opacity-50"
            >
              {doc.has_raw ? "Read again" : "Read document"}
            </button>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-8 lg:px-10">
        {job ? (
          <Processing job={job} filename={doc.filename} onRetry={job.kind === "extract" ? onExtract : onReorganize} onDismiss={props.onDismissJob} />
        ) : (
          <SheetBody {...props} />
        )}
      </div>
    </main>
  );
}

function SheetBody({ doc, version, text, textError, focus, otherJobRunning, onExtract, onReorganize }: Props) {
  const has = version === "raw" ? doc!.has_raw : doc!.has_organized;

  if (!has) {
    const organizeMissing = version === "organized" && doc!.has_raw;
    return (
      <Paper>
        <h3 className="text-xl font-semibold">{organizeMissing ? "No organized version yet" : "This document hasn't been read yet"}</h3>
        <p className="mt-2 max-w-prose font-serif text-muted">
          {organizeMissing
            ? "The local model can restructure the extracted text into clean headings, lists, and tables. It keeps every fact, and takes about half a minute per page."
            : doc!.can_extract
              ? "Read it to pull out its text, including text inside images and scanned pages."
              : "The original file isn't available anymore. Add it again to read it."}
        </p>
        {(organizeMissing || doc!.can_extract) && (
          <button
            type="button"
            onClick={organizeMissing ? onReorganize : onExtract}
            disabled={otherJobRunning}
            className="mt-5 rounded-lg bg-moss px-4 py-2 font-semibold text-sheet hover:bg-moss-deep disabled:opacity-50"
          >
            {organizeMissing ? "Organize text" : "Read document"}
          </button>
        )}
        {otherJobRunning && <p className="mt-2 text-sm text-muted">Another document is being read. Wait for it to finish.</p>}
      </Paper>
    );
  }

  if (textError) return <Paper><p className="text-danger">{textError}</p></Paper>;
  if (text === undefined) return <Paper><p className="text-muted">Opening…</p></Paper>;
  return <MarkedText text={text} focus={focus} />;
}

function MarkedText({ text, focus }: { text: string; focus: Focus | null }) {
  const blocks = useMemo(() => toBlocks(text), [text]);
  const marks = useMemo(() => passagesByBlock(blocks, focus?.sources ?? null), [blocks, focus]);
  const refs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (!focus) return;
    const target = [...marks.entries()].find(([, passages]) => passages.includes(focus.passage))?.[0];
    if (target === undefined) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    refs.current[target]?.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
  }, [focus, marks]);

  return (
    <Paper>
      <article className="sheet-prose space-y-4">
        {blocks.map((block, i) => {
          const passages = marks.get(i);
          const firstOfRun = passages && !marks.has(i - 1);
          // The passage you're looking at gets the full highlighter stroke; the answer's other passages a faint one
          const markClass = !passages ? "" : passages.includes(focus!.passage) ? "is-marked" : "is-marked is-related";
          return (
            <div
              key={block.start}
              ref={(el) => {
                refs.current[i] = el;
              }}
              className={`doc-block relative -mx-3 rounded-sm px-3 py-0.5 ${markClass}`}
            >
              {firstOfRun && (
                <span
                  className="absolute top-1 -left-7 hidden font-sans text-xs font-semibold text-moss sm:block"
                  aria-label={`Passage ${passages.join(", ")}`}
                >
                  {passages.join(",")}
                </span>
              )}
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.text}</ReactMarkdown>
            </div>
          );
        })}
      </article>
    </Paper>
  );
}

function Paper({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-[52rem] rounded-sm bg-sheet px-7 py-10 shadow-[0_1px_0_var(--color-line),0_12px_32px_-18px_rgb(34_49_43/0.35)] sm:px-14 sm:py-14">
      {children}
    </div>
  );
}

function Processing({ job, filename, onRetry, onDismiss }: { job: Job; filename: string; onRetry: () => void; onDismiss: () => void }) {
  const steps = job.logs.map(readableLog);
  const title = job.kind === "extract" ? `Reading ${filename}` : `Organizing ${filename}`;
  const progress = job.progress && job.progress.total > 0 ? job.progress : null;

  return (
    <Paper>
      <h3 className="text-xl font-semibold">{job.error ? "Something stopped the work" : title}</h3>

      {!job.error && (
        <div aria-hidden className="relative mt-6 overflow-hidden" style={{ height: "9rem" }}>
          <div className="space-y-3">
            {[92, 100, 84, 97, 71, 88, 60].map((w, i) => (
              <div key={i} className="h-2.5 rounded-full bg-line/70" style={{ width: `${w}%` }} />
            ))}
          </div>
          <div className="reading-band absolute inset-x-0 top-0 h-1/4" />
        </div>
      )}

      {progress && !job.error && (
        <div className="mt-6">
          <p className="text-sm text-muted">
            Part {Math.min(progress.done + 1, progress.total)} of {progress.total}
          </p>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-line" role="progressbar" aria-valuenow={progress.done} aria-valuemax={progress.total}>
            <div className="h-full bg-moss transition-[width] duration-500" style={{ width: `${(progress.done / progress.total) * 100}%` }} />
          </div>
        </div>
      )}

      <ol className="mt-6 space-y-1.5 text-sm" aria-live="polite">
        {steps.map((step, i) => (
          <li key={i} className="flex gap-2.5">
            <span
              aria-hidden
              className={`mt-1.5 size-1.5 shrink-0 rounded-full ${
                step.tone === "done" ? "bg-moss" : step.tone === "warn" ? "bg-mark" : step.tone === "error" ? "bg-danger" : "bg-muted"
              }`}
            />
            <span className={step.tone === "error" ? "text-danger" : ""}>{step.text}</span>
          </li>
        ))}
      </ol>

      {job.error && (
        <div className="mt-6">
          <p className="text-danger">{job.error}</p>
          <div className="mt-4 flex gap-2">
            <button type="button" onClick={onRetry} className="rounded-lg bg-moss px-4 py-2 font-semibold text-sheet hover:bg-moss-deep">
              Try again
            </button>
            <button type="button" onClick={onDismiss} className="rounded-lg border border-line px-4 py-2 font-medium hover:border-moss">
              Dismiss
            </button>
          </div>
        </div>
      )}
    </Paper>
  );
}
