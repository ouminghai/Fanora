"use client";

import { useRef, useState } from "react";
import MarkdownContent from "@/components/community/MarkdownContent";
import ImageAttachmentPicker from "@/components/community/ImageAttachmentPicker";

type MarkdownEditorProps = {
  value: string;
  onChange: (value: string) => void;
  maxLength?: number;
  imageUrls?: string[];
  onImageUrlsChange?: (value: string[]) => void;
  onImageError?: (message: string) => void;
  compact?: boolean;
};

const toolbar = [
  { label: "H2", title: "二级标题", before: "## ", after: "", placeholder: "小标题" },
  { label: "B", title: "粗体", before: "**", after: "**", placeholder: "重点内容" },
  { label: "I", title: "斜体", before: "*", after: "*", placeholder: "强调内容" },
  { label: "❝", title: "引用", before: "> ", after: "", placeholder: "引用内容" },
  { label: "•", title: "无序列表", before: "- ", after: "", placeholder: "列表内容" },
  { label: "1.", title: "有序列表", before: "1. ", after: "", placeholder: "列表内容" },
  { label: "↗", title: "链接", before: "[", after: "](https://)", placeholder: "链接文字" },
  { label: "IMG", title: "图片", before: "![", after: "](https://)", placeholder: "图片说明" },
  { label: "</>", title: "代码", before: "`", after: "`", placeholder: "代码" },
];

export default function MarkdownEditor({ value, onChange, maxLength = 10_000, imageUrls, onImageUrlsChange, onImageError, compact = false }: MarkdownEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [mode, setMode] = useState<"write" | "preview">("write");

  const insert = (before: string, after: string, placeholder: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = value.slice(start, end) || placeholder;
    const nextValue = `${value.slice(0, start)}${before}${selected}${after}${value.slice(end)}`.slice(0, maxLength);
    onChange(nextValue);
    requestAnimationFrame(() => {
      textarea.focus();
      const selectionStart = start + before.length;
      textarea.setSelectionRange(selectionStart, Math.min(selectionStart + selected.length, nextValue.length));
    });
  };

  return (
    <div className={`${compact ? "mt-1" : "mt-4"} overflow-hidden rounded-2xl border border-white/10 bg-white/[.035]`}>
      <div className={`flex flex-wrap items-center justify-between border-b border-white/10 bg-[#0d102d]/80 px-3 ${compact ? "gap-1 py-1" : "gap-3 py-2.5"}`}>
        <div className="flex flex-wrap gap-1">
          {toolbar.map((item) => (
            <button key={item.title} type="button" title={item.title} aria-label={item.title} onClick={() => insert(item.before, item.after, item.placeholder)} disabled={mode === "preview"} className={`flex items-center justify-center rounded-lg font-bold text-white/55 transition-all hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-30 ${compact ? "h-6 min-w-6 px-1.5 text-[10px]" : "h-8 min-w-8 px-2 text-xs"}`}>{item.label}</button>
          ))}
        </div>
        <div className={`flex rounded-lg bg-white/[.05] font-semibold ${compact ? "p-0.5 text-[10px]" : "p-1 text-xs"}`}>
          <button type="button" onClick={() => setMode("write")} className={`rounded-md transition-colors ${compact ? "px-2 py-1" : "px-3 py-1.5"} ${mode === "write" ? "bg-accent text-white" : "text-white/40 hover:text-white"}`}>编辑</button>
          <button type="button" onClick={() => setMode("preview")} className={`rounded-md transition-colors ${compact ? "px-2 py-1" : "px-3 py-1.5"} ${mode === "preview" ? "bg-accent text-white" : "text-white/40 hover:text-white"}`}>预览</button>
        </div>
      </div>
      {mode === "write" ? (
        <textarea ref={textareaRef} required minLength={10} maxLength={maxLength} rows={compact ? 4 : 12} value={value} onChange={(event) => onChange(event.target.value)} placeholder={"使用 Markdown 分享你的故事、作品或灵感…\n\n## 一个小标题\n写下正文，支持 **粗体**、列表、引用和链接。"} className={`block w-full border-0 bg-transparent font-mono text-white outline-none placeholder:text-white/25 focus:ring-0 ${compact ? "resize-none px-3 py-2 text-xs leading-5" : "resize-y px-5 py-4 text-sm leading-7"}`} />
      ) : (
        <div className={compact ? "min-h-20 px-3 py-2" : "min-h-[21rem] px-5 py-4"}>
          {value.trim() ? <MarkdownContent content={value} /> : <p className="text-sm text-white/30">输入 Markdown 内容后可在这里预览排版。</p>}
        </div>
      )}
      <div className={`flex items-center justify-between border-t border-white/5 text-white/30 ${compact ? "px-3 py-1 text-[9px]" : "px-4 py-2 text-[11px]"}`}>
        <span>{compact ? "支持 Markdown" : "支持 Markdown 与 GitHub 风格表格、删除线和任务列表"}</span>
        <span>{value.length}/{maxLength}</span>
      </div>
      {imageUrls && onImageUrlsChange && <div className={`border-t border-white/5 ${compact ? "px-3 pb-2" : "px-4 pb-3"}`}><ImageAttachmentPicker value={imageUrls} onChange={onImageUrlsChange} onError={onImageError} compact dense={compact} /></div>}
    </div>
  );
}
