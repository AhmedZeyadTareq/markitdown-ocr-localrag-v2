"use client";

import { useState } from "react";
import type { Status } from "@/lib/api";

type Props = {
  status: Status | null;
  disabled: boolean;
  onChoose: (model: string) => Promise<void>;
  onRetry: () => void;
};

export function ModelPicker({ status, disabled, onChoose, onRetry }: Props) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!status) return <p className="text-muted">Connecting…</p>;

  if (!status.ollama) {
    return (
      <div>
        <p className="flex items-center gap-2 text-danger">
          <span aria-hidden className="size-2 rounded-full bg-danger" />
          Ollama isn&apos;t running. Open the Ollama app.
        </p>
        <button type="button" onClick={onRetry} className="mt-1 font-semibold underline">
          Check again
        </button>
      </div>
    );
  }

  if (status.models.length === 0) {
    return (
      <div>
        <p className="text-danger">No models installed. In a terminal, run: ollama pull gemma3:12b</p>
        <button type="button" onClick={onRetry} className="mt-1 font-semibold underline">
          Check again
        </button>
      </div>
    );
  }

  const choose = async (name: string) => {
    setSaving(true);
    setError(null);
    try {
      await onChoose(name);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const ready = status.model_available;
  let hint: string;
  if (!ready) hint = `${status.model} isn't installed anymore. Pick another model.`;
  else if (disabled) hint = "You can switch models when the current task finishes.";
  else {
    const current = status.models.find((m) => m.name === status.model);
    const prefix = current?.parameters ? `${current.parameters} parameters. ` : "";
    hint = prefix + (status.vision
      ? "Reads text inside images and scanned pages."
      : "Can't read images: scanned files use Tesseract, and images inside documents are skipped.");
  }

  return (
    <div>
      <label htmlFor="model" className="flex items-center gap-2 font-semibold">
        <span aria-hidden className={`size-2 rounded-full ${ready ? "bg-moss" : "bg-danger"}`} />
        Model
      </label>
      <select
        id="model"
        value={status.model}
        disabled={disabled || saving}
        onChange={(e) => choose(e.target.value)}
        className="mt-1.5 w-full cursor-pointer rounded-md border border-line bg-sheet px-2 py-1.5 text-sm text-ink hover:border-moss disabled:cursor-not-allowed disabled:opacity-60"
      >
        {!ready && <option value={status.model}>{status.model} (not installed)</option>}
        {status.models.map((m) => (
          <option key={m.name} value={m.name}>
            {m.vision ? m.name : `${m.name} (text only)`}
          </option>
        ))}
      </select>
      <p aria-live="polite" className={`mt-1.5 ${error || !ready ? "text-danger" : "text-muted"}`}>
        {saving ? "Switching…" : (error ?? hint)}
      </p>
    </div>
  );
}
