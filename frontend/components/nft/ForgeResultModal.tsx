"use client";

import { AlertTriangle, RotateCcw, X } from "lucide-react";
import type { NftForgeSession } from "@/lib/api/types";
import styles from "@/components/nft/NftStudioWorkbench.module.css";

type Props = {
  forge: NftForgeSession | null;
  open: boolean;
  onClose: () => void;
};

export default function ForgeResultModal({ forge, open, onClose }: Props) {
  if (!open || !forge || !["FAILED", "ERROR"].includes(forge.status)) return null;
  return (
    <div className={styles.forgeModalBackdrop} role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}>
      <section className={`${styles.forgeResultModal} ${styles[`result${forge.status}`]}`} role="dialog" aria-modal="true" aria-label="Forge 结果">
        <button type="button" className={styles.resultClose} onClick={onClose} aria-label="关闭"><X /></button>
        <div className={styles.resultIcon}>{forge.status === "FAILED" ? <RotateCcw /> : <AlertTriangle />}</div>
        <small>FANORA MEMORY FORGE // {forge.rules_version}</small>
        <h2>{forge.status === "FAILED" ? "发行失败" : "发行处理异常"}</h2>
        <p>{forge.status === "FAILED" ? `作品和故事已保留，Memory Fragment +1。当前共 ${forge.fragment_balance} 个，可以调整发行参数后再次发布。` : `本次没有计为发行失败，费用已自动恢复。${forge.latest_attempt?.error_message ? ` ${forge.latest_attempt.error_message}` : ""}`}</p>
        <button type="button" className={styles.resultPrimary} onClick={onClose}>返回作品</button>
      </section>
    </div>
  );
}
