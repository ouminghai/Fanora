"use client";

import { useCallback, useEffect, useState } from "react";

const CONFIRMATION_TEXT = "我已了解风险";

type PrivateKeyExportModalProps = {
  open: boolean;
  walletAddress: string;
  onClose: () => void;
  onExport: () => Promise<string>;
};

function shortAddress(address: string) {
  return `${address.slice(0, 10)}…${address.slice(-8)}`;
}

export default function PrivateKeyExportModal({
  open,
  walletAddress,
  onClose,
  onExport,
}: PrivateKeyExportModalProps) {
  const [confirmation, setConfirmation] = useState("");
  const [privateKey, setPrivateKey] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetAndClose = useCallback(() => {
    setPrivateKey(null);
    setConfirmation("");
    setRevealed(false);
    setCopied(false);
    setError(null);
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open || !privateKey) return;
    const timer = window.setTimeout(resetAndClose, 60_000);
    return () => window.clearTimeout(timer);
  }, [open, privateKey, resetAndClose]);

  useEffect(() => {
    return () => setPrivateKey(null);
  }, []);

  if (!open) return null;

  const requestExport = async () => {
    if (confirmation !== CONFIRMATION_TEXT) return;
    setExporting(true);
    setError(null);
    try {
      const exportedKey = await onExport();
      setPrivateKey(exportedKey);
      setConfirmation("");
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "私钥导出失败，请重新登录后再试。");
    } finally {
      setExporting(false);
    }
  };

  const copyPrivateKey = async () => {
    if (!privateKey) return;
    await navigator.clipboard.writeText(privateKey);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2_000);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="private-key-export-title"
      className="fixed inset-0 z-[100] flex items-center justify-center bg-jacarta-900/80 px-4 py-8 backdrop-blur-md"
    >
      <div className="w-full max-w-lg animate-[fadeIn_.2s_ease-out] overflow-hidden rounded-[2rem] border border-white/10 bg-white shadow-[0_30px_100px_rgba(0,0,0,.45)] dark:bg-jacarta-800">
        <div className="relative overflow-hidden bg-gradient-to-br from-[#D84747] to-[#8E2A8C] px-7 py-7 text-white">
          <div className="absolute -right-10 -top-12 h-36 w-36 rounded-full border-[24px] border-white/10" />
          <div className="relative flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[.2em] text-white/70">High risk action</p>
              <h2 id="private-key-export-title" className="mt-2 font-display text-2xl font-semibold">导出钱包私钥</h2>
              <p className="mt-2 font-mono text-xs text-white/70">{shortAddress(walletAddress)}</p>
            </div>
            <button
              type="button"
              onClick={resetAndClose}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/10 text-xl transition-colors hover:bg-white/20"
              aria-label="关闭私钥导出"
            >
              ×
            </button>
          </div>
        </div>

        <div className="p-7">
          {!privateKey ? (
            <>
              <div className="rounded-2xl border border-red/20 bg-red/5 p-5 text-sm leading-6 text-jacarta-600 dark:text-jacarta-200">
                <p className="font-bold text-red">任何获得私钥的人都能完全控制这个钱包。</p>
                <ul className="mt-3 list-disc space-y-1 pl-5">
                  <li>Fanora 不会保存、上传或帮助恢复导出的私钥。</li>
                  <li>不要截图，不要通过聊天、邮件或网盘发送。</li>
                  <li>仅在离线且没有他人观看屏幕时操作。</li>
                </ul>
              </div>
              <label className="mt-6 block text-sm font-semibold text-jacarta-700 dark:text-white">
                输入“{CONFIRMATION_TEXT}”继续
                <input
                  value={confirmation}
                  onChange={(event) => {
                    setConfirmation(event.target.value);
                    setError(null);
                  }}
                  autoComplete="off"
                  className="mt-2 w-full rounded-xl border border-jacarta-100 bg-white px-4 py-3 text-jacarta-700 outline-none transition-all focus:border-red focus:ring-2 focus:ring-red/10 dark:border-white/10 dark:bg-white/[.06] dark:text-white"
                  placeholder={CONFIRMATION_TEXT}
                />
              </label>
              {error && <p className="mt-3 rounded-xl bg-red/10 px-4 py-3 text-sm text-red">{error}</p>}
              <button
                type="button"
                disabled={confirmation !== CONFIRMATION_TEXT || exporting}
                onClick={() => void requestExport()}
                className="mt-6 flex w-full items-center justify-center rounded-full bg-red px-6 py-3.5 font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-[#c73d3d] disabled:cursor-not-allowed disabled:opacity-40"
              >
                {exporting && <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />}
                {exporting ? "正在向 Web3Auth 请求…" : "我已确认，导出私钥"}
              </button>
            </>
          ) : (
            <>
              <div className="rounded-2xl border border-orange/30 bg-orange/10 p-4 text-sm leading-6 text-orange">
                私钥将在 60 秒后从页面内存中清除。复制后请妥善离线保存，并尽快清空剪贴板。
              </div>
              <div className="mt-5 rounded-2xl bg-jacarta-900 p-5">
                <p className="break-all font-mono text-sm leading-7 text-white">
                  {revealed ? privateKey : `${privateKey.slice(0, 8)}${"•".repeat(48)}${privateKey.slice(-8)}`}
                </p>
              </div>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setRevealed((current) => !current)}
                  className="rounded-full border border-jacarta-100 px-5 py-3 text-sm font-semibold text-jacarta-700 transition-colors hover:border-accent hover:text-accent dark:border-white/10 dark:text-white"
                >
                  {revealed ? "隐藏私钥" : "显示私钥"}
                </button>
                <button
                  type="button"
                  onClick={() => void copyPrivateKey()}
                  className="rounded-full bg-accent px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-dark"
                >
                  {copied ? "已复制" : "复制私钥"}
                </button>
              </div>
              <button
                type="button"
                onClick={resetAndClose}
                className="mt-3 w-full rounded-full px-5 py-3 text-sm font-semibold text-jacarta-500 transition-colors hover:text-red"
              >
                完成并清除页面中的私钥
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
