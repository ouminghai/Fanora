"use client";

import { useEffect, useRef } from "react";
import { Check, LoaderCircle, ShieldCheck, Sparkles, X } from "lucide-react";
import styles from "@/components/nft/NftStudioWorkbench.module.css";

type Props = {
  open: boolean;
  successRate: number;
  forgeCost: number;
  busy: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export default function PublishConfirmModal({ open, successRate, forgeCost, busy, onClose, onConfirm }: Props) {
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    confirmButtonRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [busy, onClose, open]);

  if (!open) return null;

  return (
    <div
      className={styles.forgeModalBackdrop}
      role="presentation"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target && !busy) onClose();
      }}
    >
      <section
        className={styles.publishConfirmModal}
        role="dialog"
        aria-modal="true"
        aria-labelledby="publish-confirm-title"
        aria-describedby="publish-confirm-description"
      >
        <button type="button" className={styles.resultClose} onClick={onClose} disabled={busy} aria-label="关闭发行确认">
          <X />
        </button>

        <div className={styles.publishConfirmHeading}>
          <span><ShieldCheck /></span>
          <div>
            <small>FANORA MEMORY FORGE</small>
            <h2 id="publish-confirm-title">确认发行这件作品？</h2>
          </div>
        </div>

        <p id="publish-confirm-description" className={styles.publishConfirmDescription}>
          确认后将进行最终发行判定。请核对本次费用与结果规则。
        </p>

        <dl className={styles.publishConfirmStats}>
          <div><dt>发行成功率</dt><dd>{successRate}%</dd></div>
          <div><dt>本次判定消耗</dt><dd>{forgeCost} FAN</dd></div>
          <div><dt>成功后发布费</dt><dd>100 FAN</dd></div>
        </dl>

        <div className={styles.publishConfirmNotice}>
          <Sparkles />
          <p><strong>失败不会丢失作品</strong><span>作品会被保留，并获得 1 个 Memory Fragment。</span></p>
        </div>

        <div className={styles.publishConfirmActions}>
          <button type="button" className={styles.publishConfirmCancel} onClick={onClose} disabled={busy}>取消</button>
          <button ref={confirmButtonRef} type="button" className={styles.publishConfirmSubmit} onClick={onConfirm} disabled={busy}>
            {busy ? <><LoaderCircle className="animate-spin" /> 正在确认发行</> : <><Check /> 确认发行</>}
          </button>
        </div>
      </section>
    </div>
  );
}
