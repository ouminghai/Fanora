/* eslint-disable @next/next/no-img-element */

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MarkdownContent({ content, className = "" }: { content: string; className?: string }) {
  return (
    <div className={`markdown-content text-base leading-8 text-white/70 ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="mb-5 mt-10 font-display text-3xl font-semibold leading-tight text-white first:mt-0 md:text-4xl">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-4 mt-9 font-display text-2xl font-semibold leading-tight text-white first:mt-0 md:text-3xl">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-3 mt-8 font-display text-xl font-semibold text-white first:mt-0">{children}</h3>,
          p: ({ children }) => <p className="my-5 whitespace-pre-wrap leading-8 text-white/68">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
          em: ({ children }) => <em className="text-accent-lighter">{children}</em>,
          ul: ({ children }) => <ul className="my-5 list-disc space-y-2 pl-6 marker:text-accent-light">{children}</ul>,
          ol: ({ children }) => <ol className="my-5 list-decimal space-y-2 pl-6 marker:font-semibold marker:text-accent-light">{children}</ol>,
          li: ({ children }) => <li className="pl-1 leading-7">{children}</li>,
          blockquote: ({ children }) => <blockquote className="my-7 rounded-r-2xl border-l-4 border-accent bg-accent/[.08] px-6 py-3 text-white/75">{children}</blockquote>,
          a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer" className="font-semibold text-accent-lighter underline decoration-accent/35 underline-offset-4 transition-colors hover:text-white">{children}</a>,
          hr: () => <hr className="my-9 border-white/10" />,
          pre: ({ children }) => <pre className="my-7 overflow-x-auto rounded-2xl border border-white/10 bg-[#090c25] p-5 text-sm leading-6 text-white/75">{children}</pre>,
          code: ({ children, className: codeClassName }) => codeClassName
            ? <code className={`${codeClassName} font-mono`}>{children}</code>
            : <code className="rounded-md bg-white/[.08] px-1.5 py-0.5 font-mono text-[.9em] text-accent-lighter">{children}</code>,
          table: ({ children }) => <div className="my-7 overflow-x-auto rounded-2xl border border-white/10"><table className="w-full border-collapse text-left text-sm">{children}</table></div>,
          thead: ({ children }) => <thead className="bg-white/[.06] text-white">{children}</thead>,
          th: ({ children }) => <th className="border-b border-white/10 px-4 py-3 font-semibold">{children}</th>,
          td: ({ children }) => <td className="border-b border-white/5 px-4 py-3 text-white/60">{children}</td>,
          img: ({ src, alt }) => src ? <img src={src} alt={alt || "正文图片"} className="my-8 max-h-[34rem] w-full rounded-2xl border border-white/10 object-cover" loading="lazy" /> : null,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
