import type { Source } from "./api";

/** A paragraph-sized piece of the document, with its character range in the full text. */
export type Block = { text: string; start: number; end: number };

export function toBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  const separator = /\n[ \t]*\n+/g;
  let start = 0;
  let match;
  while ((match = separator.exec(text)) !== null) {
    if (match.index > start) blocks.push({ text: text.slice(start, match.index), start, end: match.index });
    start = match.index + match[0].length;
  }
  if (start < text.length) blocks.push({ text: text.slice(start), start, end: text.length });
  return blocks.filter((b) => b.text.trim());
}

/** Maps each block index to the passage numbers (1-based) of the sources that overlap it. */
export function passagesByBlock(blocks: Block[], sources: Source[] | null) {
  const marks = new Map<number, number[]>();
  sources?.forEach((source, i) => {
    if (source.start < 0) return;
    const end = source.start + source.text.length;
    blocks.forEach((block, b) => {
      if (block.start < end && block.end > source.start) marks.set(b, [...(marks.get(b) ?? []), i + 1]);
    });
  });
  return marks;
}

/** Turns backend log lines like "[✔] Content saved to C:\...\extracted.md" into short readable steps. */
export function readableLog(message: string): { tone: "done" | "warn" | "error" | "work"; text: string } {
  const match = message.match(/^\[(.+?)\]\s*([\s\S]*)$/);
  const tag = match?.[1] ?? "";
  let text = match?.[2] ?? message;
  const saved = text.match(/^Content saved to .*[\\/]([^\\/]+)$/);
  if (saved) text = `Saved ${saved[1]}`;
  const tone = tag.includes("✔") || tag.includes("✅") ? "done" : tag.includes("⚠") ? "warn" : tag.includes("❌") ? "error" : "work";
  return { tone, text };
}
