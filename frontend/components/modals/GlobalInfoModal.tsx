"use client";

import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { AlertTriangle, CheckCircle2, ExternalLink, Info, X, XCircle } from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect } from "react";
import { useBodyScrollLock } from "@/components/modals/useBodyScrollLock";
import { resetNftTilt, updateNftTilt } from "@/components/nft/nftMotion";
import { startRealisticConfetti } from "@/lib/ui/confetti";

export type GlobalInfoModalProps = {
  title: string;
  message: string;
  tone?: "success" | "warning" | "error" | "info";
  eyebrow?: string;
  imageUrl?: string | null;
  imageAlt?: string;
  celebrate?: boolean;
  actionLabel?: string;
  actionUrl?: string | null;
  confirmLabel?: string;
  dismissible?: boolean;
};

const toneClasses = {
  success: { icon: "bg-green/10 text-green", button: "bg-green text-white hover:bg-green/90" },
  warning: { icon: "bg-orange/10 text-orange", button: "bg-orange text-white hover:bg-orange/90" },
  error: { icon: "bg-red/10 text-red", button: "bg-red text-white hover:bg-red/90" },
  info: { icon: "bg-accent/10 text-accent-light", button: "bg-accent text-white hover:bg-accent-dark" },
};

function ToneIcon({ tone }: { tone: NonNullable<GlobalInfoModalProps["tone"]> }) {
  if (tone === "success") return <CheckCircle2 className="h-6 w-6" />;
  if (tone === "warning") return <AlertTriangle className="h-6 w-6" />;
  if (tone === "error") return <XCircle className="h-6 w-6" />;
  return <Info className="h-6 w-6" />;
}

export default NiceModal.create<GlobalInfoModalProps>(
  ({ title, message, tone = "info", eyebrow, imageUrl, imageAlt = "获得的 NFT", celebrate = false, actionLabel, actionUrl, confirmLabel = "知道了", dismissible = true }) => {
    const modal = useModal();
    const classes = toneClasses[tone];
    useBodyScrollLock(modal.visible);
    const close = useCallback(() => {
      modal.resolve();
      modal.hide();
      window.setTimeout(() => modal.remove(), 320);
    }, [modal]);

    useEffect(() => {
      const onKeyDown = (event: KeyboardEvent) => {
        if (dismissible && event.key === "Escape") close();
      };
      window.addEventListener("keydown", onKeyDown);
      return () => {
        window.removeEventListener("keydown", onKeyDown);
      };
    }, [close, dismissible]);

    useEffect(() => {
      if (!modal.visible || !celebrate) return;
      let disposed = false;
      let stop: (() => void) | undefined;
      void startRealisticConfetti(3000).then((cleanup) => {
        if (disposed) cleanup();
        else stop = cleanup;
      });
      return () => {
        disposed = true;
        stop?.();
      };
    }, [celebrate, modal.visible]);

    return (
      <div
        aria-modal="true"
        role="dialog"
        aria-labelledby="global-info-modal-title"
        className={`fixed inset-0 z-[1400] grid place-items-center overflow-y-auto bg-transparent px-4 py-8 transition-opacity duration-300 ${modal.visible ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onMouseDown={(event) => { if (dismissible && event.target === event.currentTarget) close(); }}
      >
        <section
          className={`relative w-full max-w-2xl overflow-hidden rounded-[2rem] border border-cyan-300/35 bg-[#0d1230] p-7 text-center text-white shadow-[0_40px_140px_rgba(0,0,0,.65)] transition-[opacity,transform,filter] duration-300 ease-[cubic-bezier(.2,.8,.2,1)] sm:p-10 ${modal.visible ? "translate-y-0 scale-100 opacity-100 blur-0" : "translate-y-5 scale-[.97] opacity-0 blur-sm"}`}
        >
          <span className="pointer-events-none absolute -right-28 -top-32 h-64 w-64 rounded-full bg-cyan-300/[.07] blur-3xl" />
          <span className="pointer-events-none absolute -bottom-36 -left-24 h-64 w-64 rounded-full bg-violet-500/[.08] blur-3xl" />
          {dismissible ? (
            <button type="button" aria-label="关闭" onClick={close} className="absolute right-5 top-5 z-10 grid h-10 w-10 place-items-center rounded-full border border-white/10 bg-white/[.04] text-white/55 transition-colors hover:bg-white/10 hover:text-white">
              <X className="h-5 w-5" />
            </button>
          ) : null}

          <div className="relative mx-auto flex w-full flex-col items-center text-center">
            {imageUrl ? (
              <div
                onPointerMove={updateNftTilt}
                onPointerLeave={resetNftTilt}
                onPointerCancel={resetNftTilt}
                onMouseLeave={resetNftTilt}
                className="reward-modal-stage is-revealed nft-tilt-surface nft-flow-border mx-auto mb-9 flex h-56 w-full max-w-sm items-center justify-center overflow-hidden rounded-2xl border border-white/15 bg-black/30 shadow-[0_26px_70px_rgba(0,0,0,.45)] sm:h-64"
              >
                <Image src={imageUrl} alt="" fill unoptimized sizes="384px" className="reward-modal-backdrop object-cover" aria-hidden="true" />
                <Image src={imageUrl} alt={imageAlt} fill unoptimized sizes="384px" className="reward-ticket-image reward-modal-image object-contain" />
                <span className="reward-ticket-pixels" aria-hidden="true" />
              </div>
            ) : null}
            <div className={`mx-auto grid h-14 w-14 place-items-center rounded-full border border-white/[.06] ${classes.icon}`}><ToneIcon tone={tone} /></div>
            {eyebrow ? <p className="mt-7 text-xs font-bold uppercase tracking-[.24em] text-cyan-300">{eyebrow}</p> : null}
            <h2 id="global-info-modal-title" className="mx-auto mt-5 max-w-xl font-display text-3xl font-semibold leading-tight text-white sm:text-4xl">{title}</h2>
            <p className="mx-auto mt-5 max-w-xl whitespace-pre-line text-[15px] leading-8 text-white/62 sm:text-base">{message}</p>

            <div className="mt-9 flex w-full flex-col gap-3 sm:flex-row">
              {actionUrl ? (
                <a href={actionUrl} target="_blank" rel="noreferrer" className={`inline-flex min-h-13 flex-1 items-center justify-center gap-2 rounded-full px-6 py-3.5 text-sm font-bold transition-colors ${classes.button}`}>
                  {actionLabel || "查看详情"}<ExternalLink className="h-4 w-4" />
                </a>
              ) : null}
              <button type="button" onClick={close} className={`inline-flex min-h-13 flex-1 items-center justify-center rounded-full px-6 py-3.5 text-sm font-bold transition-colors ${actionUrl ? "border border-white/18 text-white hover:bg-white/[.07]" : classes.button}`}>
                {confirmLabel}
              </button>
            </div>
          </div>
        </section>
      </div>
    );
  },
);
