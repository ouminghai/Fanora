"use client";

import NiceModal, { useModal } from "@ebay/nice-modal-react";
import Image from "next/image";
import ChainTransactionProgress, { type TransactionKind, type TransactionPhase } from "@/components/nft/ChainTransactionProgress";
import { useBodyScrollLock } from "@/components/modals/useBodyScrollLock";

export type GlobalProcessModalProps = {
  title: string;
  message: string;
  eyebrow?: string;
  gifUrl?: string | null;
  phase?: Exclude<TransactionPhase, "idle">;
  progressKind?: TransactionKind;
  artifactName?: string;
  imageUrl?: string | null;
};

const GlobalProcessModal = NiceModal.create<GlobalProcessModalProps>(
  ({ title, message, eyebrow = "AI REVIEW", gifUrl = "/img/process/cyancat.gif", phase, progressKind, artifactName = "Fanora NFT", imageUrl }) => {
    const modal = useModal();
    useBodyScrollLock(modal.visible);

    return (
      <div
        aria-modal="true"
        role="dialog"
        aria-label={phase && progressKind ? title : undefined}
        aria-labelledby={phase && progressKind ? undefined : "global-process-modal-title"}
        className={`fixed inset-0 z-[1450] grid place-items-center overflow-y-auto bg-[#030617]/88 px-4 py-8 backdrop-blur-xl transition-opacity duration-300 ${modal.visible ? "cursor-wait opacity-100" : "pointer-events-none cursor-default opacity-0"}`}
      >
        <section className={`relative w-full ${phase && progressKind ? "max-w-5xl" : "max-w-xl"} overflow-hidden rounded-[2rem] border border-cyan-300/35 bg-[#0d1230] p-7 text-center text-white shadow-[0_40px_160px_rgba(0,0,0,.72)] transition-[opacity,transform,filter] duration-300 ease-[cubic-bezier(.2,.8,.2,1)] sm:p-10 ${modal.visible ? "translate-y-0 scale-100 opacity-100 blur-0" : "translate-y-5 scale-[.97] opacity-0 blur-sm"}`}>
          <span className="pointer-events-none absolute -right-24 -top-24 h-56 w-56 rounded-full bg-cyan-300/[.08] blur-3xl" />
          <span className="pointer-events-none absolute -bottom-28 -left-20 h-56 w-56 rounded-full bg-violet-500/[.08] blur-3xl" />
          <div className="relative mx-auto flex w-full flex-col items-center text-center">
            {phase && progressKind ? (
              <ChainTransactionProgress phase={phase} kind={progressKind} title={title} detail={message} artifactName={artifactName} imageUrl={imageUrl} embedded />
            ) : (
              <>
                {gifUrl ? <Image src={gifUrl} alt="AI 正在处理" width={160} height={160} unoptimized priority className="mx-auto h-28 w-28 object-contain sm:h-32 sm:w-32" /> : null}
                <p className="mt-5 text-xs font-bold uppercase tracking-[.28em] text-cyan-300">{eyebrow}</p>
                <h2 id="global-process-modal-title" className="mt-4 font-display text-3xl font-semibold sm:text-4xl">{title}</h2>
                <p className="mx-auto mt-4 max-w-md text-sm leading-7 text-white/55">{message}</p>
                <div className="mx-auto mt-8 flex w-fit items-center gap-2" aria-hidden="true">
                  {[0, 1, 2].map((item) => <span key={item} className="h-2 w-2 animate-pulse rounded-full bg-cyan-300" style={{ animationDelay: `${item * 180}ms` }} />)}
                </div>
              </>
            )}
            <p className="mt-7 text-[10px] font-semibold uppercase tracking-[.24em] text-white/25">请保持当前页面开启</p>
          </div>
        </section>
      </div>
    );
  },
);

export async function hideGlobalProcessModal() {
  void NiceModal.hide(GlobalProcessModal);
  await new Promise((resolve) => window.setTimeout(resolve, 320));
  NiceModal.remove(GlobalProcessModal);
}

export default GlobalProcessModal;
