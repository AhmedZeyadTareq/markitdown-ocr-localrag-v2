export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type Version = "raw" | "organized";

export type DocSummary = {
  id: string;
  filename: string;
  has_raw: boolean;
  has_organized: boolean;
  can_extract: boolean;
  raw_chars: number;
  updated_at: string;
};

export type ModelInfo = { name: string; vision: boolean; parameters: string | null; size_gb: number };

export type Status = {
  ollama: boolean;
  model: string;
  model_available: boolean;
  vision: boolean;
  models: ModelInfo[];
};

export type Source = { text: string; start: number };

export type StreamEvent =
  | { type: "log"; message: string }
  | { type: "progress"; done: number; total: number }
  | { type: "done"; document?: DocSummary }
  | { type: "error"; message: string }
  | { type: "sources"; sources: Source[] }
  | { type: "token"; text: string };

async function errorFrom(response: Response) {
  try {
    const body = await response.json();
    return new Error(typeof body.detail === "string" ? body.detail : response.statusText);
  } catch {
    return new Error(response.statusText || `Request failed (${response.status})`);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new Error("Can't reach the app server. Start it with: python -m backend.api");
  }
  if (!response.ok) throw await errorFrom(response);
  return response.json();
}

export const getStatus = () => request<Status>("/api/status");
export const chooseModel = (model: string) =>
  request<Status>("/api/model", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model }),
  });
export const listDocuments = () => request<DocSummary[]>("/api/documents");
export const deleteDocument = (id: string) => request<{ deleted: string }>(`/api/documents/${id}`, { method: "DELETE" });
export const getText = (id: string, version: Version) =>
  request<{ text: string }>(`/api/documents/${id}/text?version=${version}`).then((r) => r.text);

export function uploadDocument(file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<DocSummary>("/api/documents", { method: "POST", body: form });
}

/** POSTs to a streaming endpoint and yields each Server-Sent Event as it arrives. */
export async function* streamEvents(path: string, body?: unknown): AsyncGenerator<StreamEvent> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Can't reach the app server. Start it with: python -m backend.api");
  }
  if (!response.ok || !response.body) throw await errorFrom(response);

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let boundary;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      for (const line of chunk.split("\n")) {
        if (line.startsWith("data: ")) yield JSON.parse(line.slice(6)) as StreamEvent;
      }
    }
  }
}
