"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  chooseModel,
  deleteDocument,
  getStatus,
  getText,
  listDocuments,
  streamEvents,
  uploadDocument,
  type DocSummary,
  type Source,
  type Status,
  type Version,
} from "@/lib/api";
import { ChatPanel, type Message } from "./ChatPanel";
import { DocumentSheet } from "./DocumentSheet";
import { Library } from "./Library";

export type Job = {
  kind: "extract" | "reorganize";
  docId: string;
  logs: string[];
  progress?: { done: number; total: number };
  error?: string;
};

export type Focus = { sources: Source[]; passage: number; nonce: number };

const ACCEPTED = ".pdf,.docx,.pptx,.xlsx,.xls,.png,.jpg,.jpeg,.bmp,.tiff,.html,.htm,.txt,.md,.csv,.json,.xml,.epub";

const errorMessage = (e: unknown) => (e instanceof Error ? e.message : String(e));

export function Workspace() {
  const [status, setStatus] = useState<Status | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [docs, setDocs] = useState<DocSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [version, setVersion] = useState<Version>("raw");
  const [texts, setTexts] = useState<Record<string, string>>({});
  // Tied to the text it belongs to, so a failure for one document isn't shown on another
  const [textError, setTextError] = useState<{ key: string; message: string } | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [messages, setMessages] = useState<Record<string, Message[]>>({});
  const [focus, setFocus] = useState<Focus | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const selected = docs.find((d) => d.id === selectedId) ?? null;
  const textKey = selected ? `${selected.id}:${version}` : "";
  const hasVersion = selected ? (version === "raw" ? selected.has_raw : selected.has_organized) : false;

  const refresh = useCallback(async () => {
    try {
      const [s, d] = await Promise.all([getStatus(), listDocuments()]);
      setStatus(s);
      setDocs(d);
      setServerError(null);
      return d;
    } catch (e) {
      setServerError(errorMessage(e));
      return null;
    }
  }, []);

  useEffect(() => {
    refresh().then((d) => {
      if (d?.length) setSelectedId((current) => current ?? d[0].id);
    });
  }, [refresh]);

  // Coming back to the tab picks up models pulled (or Ollama started) in the meantime
  useEffect(() => {
    const onFocus = () => getStatus().then(setStatus).catch(() => {});
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  // Load the document text for the current version the first time it's shown
  useEffect(() => {
    if (!selected || !hasVersion || texts[textKey] !== undefined) return;
    let cancelled = false;
    setTextError(null);
    getText(selected.id, version)
      .then((text) => !cancelled && setTexts((t) => ({ ...t, [textKey]: text })))
      .catch((e) => !cancelled && setTextError({ key: textKey, message: errorMessage(e) }));
    return () => {
      cancelled = true;
    };
  }, [selected, hasVersion, version, textKey, texts]);

  const updateDoc = (doc: DocSummary) => {
    setDocs((list) => [doc, ...list.filter((d) => d.id !== doc.id)]);
    // Text changed on the server, so drop cached copies and stale highlights
    setTexts((t) => Object.fromEntries(Object.entries(t).filter(([k]) => !k.startsWith(`${doc.id}:`))));
    setFocus(null);
  };

  const runJob = async (docId: string, kind: Job["kind"]) => {
    setJob({ kind, docId, logs: [] });
    try {
      for await (const event of streamEvents(`/api/documents/${docId}/${kind}`)) {
        if (event.type === "log") setJob((j) => j && { ...j, logs: [...j.logs, event.message] });
        else if (event.type === "progress") setJob((j) => j && { ...j, progress: { done: event.done, total: event.total } });
        else if (event.type === "error") {
          setJob((j) => j && { ...j, error: event.message });
          return false;
        } else if (event.type === "done" && event.document) {
          updateDoc(event.document);
          if (kind === "reorganize" && docId === selectedId) setVersion("organized");
        }
      }
      setJob(null);
      return true;
    } catch (e) {
      setJob((j) => j && { ...j, error: errorMessage(e) });
      return false;
    }
  };

  const addFiles = async (files: FileList | File[]) => {
    const list = Array.from(files);
    if (!list.length || job) return;
    const uploaded: DocSummary[] = [];
    for (const file of list) {
      try {
        const doc = await uploadDocument(file);
        uploaded.push(doc);
        updateDoc(doc);
      } catch (e) {
        setServerError(`Couldn't add ${file.name}: ${errorMessage(e)}`);
      }
    }
    if (!uploaded.length) return;
    setSelectedId(uploaded[0].id);
    setVersion("raw");
    for (const doc of uploaded) {
      if (!doc.has_raw && !(await runJob(doc.id, "extract"))) break;
    }
  };

  const removeDoc = async (doc: DocSummary) => {
    if (!window.confirm(`Delete ${doc.filename} and everything saved for it?`)) return;
    try {
      await deleteDocument(doc.id);
      setDocs((list) => list.filter((d) => d.id !== doc.id));
      if (selectedId === doc.id) setSelectedId(null);
    } catch (e) {
      setServerError(errorMessage(e));
    }
  };

  const ask = async (question: string) => {
    if (!selected) return;
    const key = textKey;
    const askedVersion = version;
    const index = (messages[key]?.length ?? 0) + 1;
    const update = (change: (m: Message) => Message) =>
      setMessages((all) => ({ ...all, [key]: all[key].map((m, i) => (i === index ? change(m) : m)) }));

    setMessages((all) => ({
      ...all,
      [key]: [
        ...(all[key] ?? []),
        { role: "user", text: question, version: askedVersion },
        { role: "assistant", text: "", version: askedVersion, pending: true },
      ],
    }));

    try {
      for await (const event of streamEvents(`/api/documents/${selected.id}/chat`, { question, version: askedVersion })) {
        if (event.type === "log") update((m) => ({ ...m, note: event.message }));
        else if (event.type === "sources") {
          update((m) => ({ ...m, sources: event.sources, note: undefined }));
          setFocus({ sources: event.sources, passage: 1, nonce: Date.now() });
        } else if (event.type === "token") update((m) => ({ ...m, text: m.text + event.text }));
        else if (event.type === "error") update((m) => ({ ...m, error: event.message }));
      }
    } catch (e) {
      update((m) => ({ ...m, error: errorMessage(e) }));
    } finally {
      update((m) => ({ ...m, pending: false, note: undefined }));
    }
  };

  const select = (id: string) => {
    setSelectedId(id);
    setVersion("raw");
    setFocus(null);
  };

  const changeVersion = (v: Version) => {
    setVersion(v);
    setFocus(null);
  };

  const showPassage = (sources: Source[], passage: number, messageVersion: Version) => {
    if (messageVersion !== version) setVersion(messageVersion);
    setFocus({ sources, passage, nonce: Date.now() });
  };

  return (
    <div
      className="relative grid min-h-full grid-cols-1 lg:h-full lg:grid-cols-[17rem_minmax(0,1fr)_25rem] lg:grid-rows-[minmax(0,1fr)]"
      onDragOver={(e) => {
        if (!e.dataTransfer.types.includes("Files")) return;
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => {
        if (e.currentTarget === e.target || !e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        addFiles(e.dataTransfer.files);
      }}
    >
      <input
        ref={fileInput}
        type="file"
        multiple
        accept={ACCEPTED}
        className="sr-only"
        tabIndex={-1}
        onChange={(e) => {
          if (e.target.files) addFiles(e.target.files);
          e.target.value = "";
        }}
      />

      <Library
        docs={docs}
        selectedId={selectedId}
        status={status}
        serverError={serverError}
        busyDocId={job && !job.error ? job.docId : null}
        canAdd={!job || !!job.error}
        onAdd={() => fileInput.current?.click()}
        onSelect={select}
        onDelete={removeDoc}
        onRetryServer={refresh}
        onChooseModel={async (model) => setStatus(await chooseModel(model))}
      />

      <DocumentSheet
        doc={selected}
        version={version}
        onVersionChange={changeVersion}
        text={texts[textKey]}
        textError={textError?.key === textKey ? textError.message : null}
        job={job && job.docId === selected?.id ? job : null}
        otherJobRunning={!!job && !job.error && job.docId !== selected?.id}
        focus={focus}
        onAdd={() => fileInput.current?.click()}
        onExtract={() => selected && runJob(selected.id, "extract")}
        onReorganize={() => selected && runJob(selected.id, "reorganize")}
        onDismissJob={() => setJob(null)}
      />

      <ChatPanel
        doc={selected}
        version={version}
        hasText={hasVersion && texts[textKey] !== undefined}
        busy={!!job && !job.error && job.docId === selected?.id}
        messages={messages[textKey] ?? []}
        onAsk={ask}
        onShowPassage={showPassage}
      />

      {dragging && (
        <div className="pointer-events-none absolute inset-3 z-20 grid place-items-center rounded-xl border-2 border-dashed border-moss bg-paper/85">
          <p className="text-2xl font-semibold text-moss">Drop to add to your library</p>
        </div>
      )}
    </div>
  );
}
