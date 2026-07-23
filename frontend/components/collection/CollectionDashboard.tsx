"use client";

import axios from "axios";
import { Download, ExternalLink, RefreshCw, ShieldCheck, Sparkles, UserRound } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Abi } from "viem";
import { useReadContract } from "wagmi";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import ChainTransactionProgress, { type TransactionPhase } from "@/components/nft/ChainTransactionProgress";
import { resetNftTilt, updateNftTilt } from "@/components/nft/nftMotion";
import UserAvatar from "@/components/profile/UserAvatar";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import type { CollectibleAvatarResponse, CollectibleNft, MembershipCardAction, MembershipIdentityNft, MyCollection } from "@/lib/api/types";
import membershipIdentityArtifact from "../../../shared/contracts/FanoraMembershipIdentity.json";

type CollectionTab = "identity" | "collectibles";

const statusLabels: Record<string, string> = {
  NOT_CONFIGURED: "等待链上配置",
  READY: "可同步",
  PENDING: "等待链上提交",
  SUBMITTED: "已提交链上",
  CONFIRMING: "确认中",
  CONFIRMED: "链上已确认",
  RETRYABLE: "可重新同步",
  FAILED: "同步失败",
  DRAFT: "草稿",
  UNDER_REVIEW: "审核中",
  APPROVED: "已批准",
  REJECTED: "已拒绝",
  PINNING: "正在写入 IPFS",
  MINTING: "正在铸造",
  MINTED: "已铸造",
};

const tabs: Array<{ id: CollectionTab; label: string }> = [
  { id: "identity", label: "链上身份" },
  { id: "collectibles", label: "我的收藏" },
];

function errorText(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail || "请求暂时没有完成。";
  if (error instanceof Error) return error.message;
  return "请求暂时没有完成。";
}

function formatDate(value: string | null) {
  if (!value) return "尚未正式入会";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date(value));
}

function formatChainDate(value: string | null | undefined) {
  if (!value) return "等待链上确认";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function shortAddress(address: string) {
  return `${address.slice(0, 8)}...${address.slice(-6)}`;
}

function Status({ value }: { value: string }) {
  const confirmed = ["CONFIRMED", "MINTED"].includes(value);
  const failed = ["FAILED", "REJECTED"].includes(value);
  const tone = confirmed ? "text-green" : failed ? "text-red" : "text-accent";
  const dot = confirmed ? "bg-green" : failed ? "bg-red" : "bg-accent";
  return (
    <span className={`inline-flex items-center gap-2 text-xs font-semibold ${tone} ${confirmed ? "nft-flow-border rounded-full px-2.5 py-1" : ""}`}>
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      {statusLabels[value] || value}
    </span>
  );
}

function IdentityPanel({
  identity,
  syncStatus,
  level,
  walletAddress,
  chainTokenId,
  chainOwner,
  chainVerified,
  chainChecking,
  fanTokenBalance,
  fanTokenLifetimeEarned,
  busy,
  syncPhase,
  cardPhase,
  downloading,
  onSync,
  onCardAction,
  onDownload,
}: {
  identity: MembershipIdentityNft | null | undefined;
  syncStatus: string;
  level: string;
  walletAddress: string;
  chainTokenId: bigint | null;
  chainOwner: string | null;
  chainVerified: boolean;
  chainChecking: boolean;
  fanTokenBalance: number;
  fanTokenLifetimeEarned: number;
  busy: boolean;
  syncPhase: TransactionPhase;
  cardPhase: TransactionPhase;
  downloading: boolean;
  onSync: () => void;
  onCardAction: () => void;
  onDownload: () => void;
}) {
  const visibleTokenId = chainTokenId && chainTokenId > 0n
    ? chainTokenId.toString()
    : identity?.token_id?.toString();
  const nftExplorerUrl = identity?.contract_address && visibleTokenId
    ? `https://testnet.monadvision.com/nft/${identity.contract_address}/${visibleTokenId}?tab=Overview`
    : null;

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,420px)_1fr] lg:items-start">
      <article
        onPointerMove={updateNftTilt}
        onPointerLeave={resetNftTilt}
        onPointerCancel={resetNftTilt}
        onMouseLeave={resetNftTilt}
        className={`nft-tilt-surface overflow-hidden rounded-lg border border-jacarta-100 bg-white shadow-sm dark:border-white/10 dark:bg-jacarta-700 ${chainVerified ? "nft-flow-border" : ""}`}
      >
        <button
          type="button"
          onClick={onCardAction}
          disabled={busy}
          className={`membership-card-stage relative block aspect-[421/734] w-full overflow-hidden bg-[#100b24] text-left disabled:cursor-not-allowed ${cardPhase === "processing" ? "is-sealed" : ""} ${cardPhase === "complete" ? "is-revealed" : ""}`}
          aria-label={identity?.is_member_card ? "刷新会员证图片" : "制作会员证 NFT"}
        >
          <Image
            key={`${identity?.token_id ?? "pending"}-${identity?.metadata_version ?? 0}-${identity?.image_url || "fallback"}`}
            fill
            unoptimized={Boolean(identity?.is_member_card && identity?.image_url)}
            src={identity?.is_member_card && identity?.image_url ? identity.image_url : "/img/membercard/membercard.jpg"}
            alt={`${level} Fanora 链上会员身份`}
            sizes="(max-width: 1023px) 100vw, 420px"
            className="membership-card-image object-cover"
          />
          <span className="membership-card-pixels" aria-hidden="true" />
          {!identity?.is_member_card || cardPhase === "processing" ? (
            <span className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#081832]/35 px-8 text-center text-white backdrop-blur-[2px]">
              <span className="flex h-14 w-14 items-center justify-center rounded-full border border-white/30 bg-black/25 shadow-2xl">
                {cardPhase === "processing" ? <RefreshCw className="h-6 w-6 animate-spin" /> : <ShieldCheck className="h-7 w-7" />}
              </span>
              <strong className="mt-4 font-display text-lg font-semibold">
                {cardPhase === "processing" ? "会员证仍在封印中" : "制作你的链上会员证"}
              </strong>
              <span className="mt-2 text-xs leading-5 text-white/75">
                {cardPhase === "processing" ? "等待 Monad 验证节点完成确认" : "无需消耗 FAN，确认后揭晓完整卡面"}
              </span>
            </span>
          ) : null}
          {identity?.card_needs_refresh && cardPhase === "idle" ? (
            <span className="absolute inset-x-4 bottom-4 z-10 rounded-md bg-[#081832]/85 px-4 py-3 text-center text-xs font-semibold text-white backdrop-blur-md">
              等级或资料已更新，点击卡面刷新会员证
            </span>
          ) : null}
          <span className="absolute right-4 top-4 z-10 rounded-full bg-black/45 px-3 py-1 font-mono text-[10px] text-white/80 backdrop-blur-md">
            #{identity?.token_id ?? "--"}
          </span>
        </button>
        <div className="flex items-center justify-between gap-3 px-5 py-4">
          <Status value={identity?.status || syncStatus} />
          {nftExplorerUrl ? (
            <a
              href={nftExplorerUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs font-semibold text-accent hover:text-accent-dark"
            >
              在 MonadVision 查看 NFT <ExternalLink className="h-3.5 w-3.5" />
            </a>
          ) : null}
        </div>
      </article>

      <div className="pt-1">
        <p className="text-xs font-bold uppercase text-accent">Soulbound Identity</p>
        <h2 className="mt-3 font-display text-3xl font-semibold text-jacarta-700 dark:text-white">
          你的粉丝身份，永久记录在链上
        </h2>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-jacarta-500 dark:text-jacarta-300">
          缴纳会费后，Fanora 会按累计获得 FAN 确认会员等级，并铸造不可转移的会员身份。
          发布或购买 NFT 消耗的是可用 FAN，不会降低链上身份的累计等级进度。
        </p>

        <dl className="mt-6 grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg bg-jacarta-50 px-4 py-4 dark:bg-white/[.04]">
            <dt className="text-xs text-jacarta-400">可用 FAN</dt>
            <dd>
              <FanTokenAmount amount={fanTokenBalance} showSymbol className="mt-2 font-display text-xl font-semibold text-accent" />
            </dd>
          </div>
          <div className="rounded-lg bg-jacarta-50 px-4 py-4 dark:bg-white/[.04]">
            <dt className="text-xs text-jacarta-400">累计 FAN</dt>
            <dd>
              <FanTokenAmount amount={fanTokenLifetimeEarned} showSymbol className="mt-2 font-display text-xl font-semibold text-jacarta-700 dark:text-white" />
            </dd>
          </div>
        </dl>

        <div
          className={`mt-6 flex items-start gap-3 rounded-lg border px-4 py-4 ${
            chainVerified
              ? "border-green/25 bg-green/10"
              : "border-accent/20 bg-accent/5"
          }`}
        >
          <span
            className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white ${
              chainVerified ? "bg-green" : "bg-accent"
            }`}
          >
            {chainVerified ? "✓" : "…"}
          </span>
          <div>
            <p className={`font-semibold ${chainVerified ? "text-green" : "text-accent"}`}>
              {chainVerified
                ? "Monad 链上已验证"
                : chainChecking
                  ? "正在从 Monad 验证身份"
                  : "等待 Monad 链上确认"}
            </p>
            <p className="mt-1 text-xs leading-5 text-jacarta-500 dark:text-jacarta-300">
              {chainVerified
                ? `identityTokenOf(当前钱包) = #${chainTokenId?.toString()}，ownerOf(#${chainTokenId?.toString()}) 与当前钱包一致。`
                : "页面正在直接读取身份合约，不仅依赖 Fanora 数据库记录。"}
            </p>
          </div>
        </div>

        {cardPhase !== "idle" ? (
          <div className="mt-6">
            <ChainTransactionProgress
              phase={cardPhase}
              kind="member-card"
              compact
              title={cardPhase === "complete" ? "会员证 NFT 已揭晓" : "正在制作会员证 NFT"}
              detail={cardPhase === "complete" ? "卡面、二维码与链上 metadata 已完成确认。" : "交易已提交，节点正在依次合成卡面、写入 IPFS 并确认链上身份。"}
              artifactName={`${level} Member Card${visibleTokenId ? ` #${visibleTokenId}` : ""}`}
              imageUrl={identity?.image_url}
            />
          </div>
        ) : syncPhase !== "idle" ? (
          <div className="mt-6">
            <ChainTransactionProgress
              phase={syncPhase}
              kind="identity"
              compact
              title={syncPhase === "complete" ? "身份区块已确认" : "正在刷新链上身份"}
              detail={syncPhase === "complete" ? "等级、Owner 与身份 Token 已完成链上校验。" : "交易已提交，验证节点正在依次读取并确认身份数据。"}
              artifactName={`${level} Identity${visibleTokenId ? ` #${visibleTokenId}` : ""}`}
            />
          </div>
        ) : null}

        <dl className="mt-8 grid border-y border-jacarta-100 py-6 dark:border-white/10 sm:grid-cols-3">
          <div className="py-2 sm:border-r sm:border-jacarta-100 sm:px-5 sm:first:pl-0 dark:sm:border-white/10">
            <dt className="text-xs text-jacarta-400">Level ID</dt>
            <dd className="mt-2 font-display text-xl font-semibold text-jacarta-700 dark:text-white">
              {identity?.level_id ?? "--"}
            </dd>
          </div>
          <div className="py-2 sm:border-r sm:border-jacarta-100 sm:px-5 dark:sm:border-white/10">
            <dt className="text-xs text-jacarta-400">Metadata</dt>
            <dd className="mt-2 font-display text-xl font-semibold text-jacarta-700 dark:text-white">
              v{identity?.metadata_version ?? 1}
            </dd>
          </div>
          <div className="py-2 sm:px-5">
            <dt className="text-xs text-jacarta-400">Network</dt>
            <dd className="mt-2 font-display text-xl font-semibold text-jacarta-700 dark:text-white">
              Monad Testnet
            </dd>
          </div>
        </dl>

        <dl className="mt-6 grid gap-x-8 gap-y-5 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-jacarta-400">持有人钱包</dt>
            <dd className="mt-1 font-mono text-jacarta-700 dark:text-white" title={walletAddress}>
              {shortAddress(walletAddress)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-jacarta-400">链上 Owner</dt>
            <dd className="mt-1 font-mono text-jacarta-700 dark:text-white" title={chainOwner || ""}>
              {chainOwner ? shortAddress(chainOwner) : "等待读取"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-jacarta-400">Identity Token</dt>
            <dd className="mt-1 font-mono text-jacarta-700 dark:text-white">
              {chainTokenId && chainTokenId > 0n ? `#${chainTokenId.toString()}` : identity?.token_id ? `#${identity.token_id}` : "--"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-jacarta-400">身份合约</dt>
            <dd className="mt-1 font-mono text-jacarta-700 dark:text-white" title={identity?.contract_address || ""}>
              {identity?.contract_address ? shortAddress(identity.contract_address) : "等待配置"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-jacarta-400">确认区块</dt>
            <dd className="mt-1 font-mono text-jacarta-700 dark:text-white">
              {identity?.mint_operation?.block_number?.toLocaleString("en-US") || "等待确认"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-jacarta-400">铸造时间</dt>
            <dd className="mt-1 text-jacarta-700 dark:text-white">{formatChainDate(identity?.minted_at)}</dd>
          </div>
        </dl>

        {identity?.mint_operation?.transaction_hash ? (
          <div className="mt-6 rounded-lg bg-jacarta-50 px-4 py-3 dark:bg-white/[.04]">
            <p className="text-xs text-jacarta-400">铸造交易</p>
            <a
              href={`https://testnet.monadexplorer.com/tx/${identity.mint_operation.transaction_hash}`}
              target="_blank"
              rel="noreferrer"
              className="mt-1 block truncate font-mono text-xs font-semibold text-accent hover:text-accent-dark"
              title={identity.mint_operation.transaction_hash}
            >
              {identity.mint_operation.transaction_hash}
            </a>
          </div>
        ) : null}

        <div className="mt-8 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onCardAction}
            disabled={busy}
            className="web3-action-button inline-flex min-w-48 items-center justify-center gap-2 rounded-lg px-6 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? <RefreshCw className="h-4 w-4 animate-spin" /> : identity?.is_member_card ? <RefreshCw className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
            {busy ? "等待链上确认..." : identity?.is_member_card ? "刷新会员证" : "制作会员证"}
          </button>
          {identity?.download_url ? (
            <button
              type="button"
              onClick={onDownload}
              disabled={downloading || busy}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-jacarta-100 bg-white px-5 py-3 text-sm font-semibold text-jacarta-700 transition-colors hover:border-accent hover:text-accent disabled:opacity-50 dark:border-white/10 dark:bg-white/[.04] dark:text-white"
            >
              <Download className="h-4 w-4" />
              {downloading ? "正在准备..." : "下载会员证"}
            </button>
          ) : null}
          <button
            type="button"
            onClick={onSync}
            disabled={busy}
            className="inline-flex min-w-40 items-center justify-center rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-white shadow-accent-volume transition-colors hover:bg-accent-dark disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "正在同步..." : identity?.status === "CONFIRMED" ? "校验链上身份" : "同步链上身份"}
          </button>
          {nftExplorerUrl ? (
            <a
              href={nftExplorerUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center rounded-lg border border-jacarta-100 bg-white px-5 py-3 text-sm font-semibold text-jacarta-700 transition-colors hover:border-accent hover:text-accent dark:border-white/10 dark:bg-white/[.04] dark:text-white"
            >
              在 MonadVision 查看 NFT ↗
            </a>
          ) : null}
          {identity?.metadata_gateway_url ? (
            <a
              href={identity.metadata_gateway_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center rounded-lg border border-jacarta-100 bg-white px-5 py-3 text-sm font-semibold text-jacarta-700 transition-colors hover:border-accent hover:text-accent dark:border-white/10 dark:bg-white/[.04] dark:text-white"
            >
              IPFS 身份档案 ↗
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function CollectibleCard({
  item,
  index = 0,
  isAvatar,
  avatarBusy,
  onSetAvatar,
}: {
  item: CollectibleNft;
  index?: number;
  isAvatar: boolean;
  avatarBusy: boolean;
  onSetAvatar: (item: CollectibleNft) => void;
}) {
  const detailHref = item.fan_nft_creation_id ? `/item/${item.fan_nft_creation_id}` : null;
  const image = (
    <div className="relative aspect-square overflow-hidden bg-jacarta-100 dark:bg-white/5">
      {item.image_url ? (
        <Image
          fill
          unoptimized
          src={item.image_url}
          alt={item.name}
          sizes="(max-width: 639px) 100vw, (max-width: 1023px) 50vw, 25vw"
          className="object-cover transition-transform duration-500 group-hover:scale-[1.03]"
        />
      ) : (
        <div className="flex h-full items-center justify-center text-sm text-jacarta-400">等待 NFT 图片</div>
      )}
    </div>
  );

  return (
    <article
      onPointerMove={updateNftTilt}
      onPointerLeave={resetNftTilt}
      onPointerCancel={resetNftTilt}
      onMouseLeave={resetNftTilt}
      className="nft-tilt-surface group community-reveal overflow-hidden rounded-lg border border-jacarta-100 bg-white dark:border-white/10 dark:bg-jacarta-700"
      style={{ animationDelay: `${Math.min(index, 12) * 55}ms` }}
    >
      {detailHref ? <Link href={detailHref} className="block">{image}</Link> : image}
      <div className="p-5">
        <div className="flex items-center justify-between gap-3">
          <Status value={item.status} />
          <span className="font-mono text-xs text-jacarta-400">#{item.token_id}</span>
        </div>
        {detailHref ? (
          <Link href={detailHref} className="mt-3 block">
            <h3 className="font-display text-lg font-semibold text-jacarta-700 transition-colors hover:text-accent dark:text-white">{item.name}</h3>
          </Link>
        ) : (
          <h3 className="mt-3 font-display text-lg font-semibold text-jacarta-700 dark:text-white">{item.name}</h3>
        )}
        <p className="mt-2 line-clamp-2 min-h-10 text-sm text-jacarta-500 dark:text-jacarta-300">
          {item.description}
        </p>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          {item.explorer_url ? (
            <a href={item.explorer_url} target="_blank" rel="noreferrer" className="text-xs font-semibold text-accent">
              查看链上资产 ↗
            </a>
          ) : <span />}
          <button
            type="button"
            onClick={() => onSetAvatar(item)}
            disabled={!item.image_url || isAvatar || avatarBusy || item.status !== "CONFIRMED"}
            title={isAvatar ? "当前头像" : item.image_url ? "将这枚 NFT 设为头像" : "NFT 图片不可用"}
            className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-jacarta-100 bg-white px-3 text-xs font-semibold text-jacarta-600 transition-colors hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-55 dark:border-white/10 dark:bg-white/[.04] dark:text-jacarta-200"
          >
            {avatarBusy ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <UserRound className="h-3.5 w-3.5" />}
            {avatarBusy ? "设置中..." : isAvatar ? "当前头像" : "设为头像"}
          </button>
        </div>
      </div>
    </article>
  );
}

export default function CollectionDashboard() {
  const router = useRouter();
  const { user, status, refreshUser } = useAuth();
  const [collection, setCollection] = useState<MyCollection | null>(null);
  const [activeTab, setActiveTab] = useState<CollectionTab>("identity");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [identityPhase, setIdentityPhase] = useState<TransactionPhase>("idle");
  const [cardPhase, setCardPhase] = useState<TransactionPhase>("idle");
  const [downloadingCard, setDownloadingCard] = useState(false);
  const [avatarBusyTokenId, setAvatarBusyTokenId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const initializedUserRef = useRef<string | null>(null);
  const autoCardSyncKeyRef = useRef<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get<MyCollection>("/nft/me");
      setCollection(response.data);
      return response.data;
    } catch (error) {
      setNotice(errorText(error));
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const copyWallet = async () => {
    if (!user) return;
    await navigator.clipboard.writeText(user.primary_wallet.address);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  const syncIdentity = useCallback(async (announce = true) => {
    setBusy("identity");
    if (announce) setIdentityPhase("processing");
    if (announce) setNotice(null);
    try {
      await api.post<MyCollection>("/nft/identity/sync");
      const [collectionResponse] = await Promise.all([
        api.get<MyCollection>("/nft/me"),
        refreshUser(),
      ]);
      setCollection(collectionResponse.data);
      if (announce) {
        const confirmed = collectionResponse.data.identity?.status === "CONFIRMED";
        setIdentityPhase(confirmed ? "complete" : "idle");
        setNotice(confirmed ? "链上会员身份与徽章数据已更新。" : "同步任务已记录，可稍后重试。");
        if (confirmed) await new Promise((resolve) => window.setTimeout(resolve, 1400));
        setIdentityPhase("idle");
      }
    } catch (error) {
      if (announce) setIdentityPhase("idle");
      setNotice(errorText(error));
    } finally {
      setBusy(null);
    }
  }, [refreshUser]);

  const runMembershipCardAction = useCallback(async () => {
    const hasCard = Boolean(collection?.identity?.is_member_card);
    setBusy("member-card");
    setCardPhase("processing");
    setNotice(null);
    try {
      const endpoint = hasCard ? "/nft/identity/card/refresh" : "/nft/identity/card";
      const response = await api.post<MembershipCardAction>(endpoint);
      setCollection(response.data.collection);
      await refreshUser();
      setCardPhase("complete");
      setNotice(
        response.data.changed
          ? "会员证已按最新等级和资料更新，Token ID 保持不变。"
          : "会员证已经是最新版本，无需重复写入链上。",
      );
      await new Promise((resolve) => window.setTimeout(resolve, 1800));
      setCardPhase("idle");
    } catch (error) {
      setCardPhase("idle");
      setNotice(errorText(error));
    } finally {
      setBusy(null);
    }
  }, [collection?.identity?.is_member_card, refreshUser]);

  const downloadMembershipCard = useCallback(async () => {
    const downloadUrl = collection?.identity?.download_url;
    if (!downloadUrl) return;
    setDownloadingCard(true);
    try {
      const response = await fetch(downloadUrl);
      if (!response.ok) throw new Error("download failed");
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = `fanora-member-card-${collection.identity?.token_id || "identity"}.png`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(objectUrl);
    } catch {
      window.open(downloadUrl, "_blank", "noopener,noreferrer");
    } finally {
      setDownloadingCard(false);
    }
  }, [collection?.identity?.download_url, collection?.identity?.token_id]);

  const setCollectibleAvatar = useCallback(async (item: CollectibleNft) => {
    if (!item.image_url || avatarBusyTokenId) return;
    setAvatarBusyTokenId(item.token_type_id);
    setNotice(null);
    try {
      await api.post<CollectibleAvatarResponse>(`/nft/collectibles/${item.token_type_id}/avatar`);
      await refreshUser();
      setNotice(`已将「${item.name}」设为头像。`);
    } catch (error) {
      setNotice(errorText(error));
    } finally {
      setAvatarBusyTokenId(null);
    }
  }, [avatarBusyTokenId, refreshUser]);

  useEffect(() => {
    if (status === "anonymous" || status === "error") {
      router.replace("/login");
      return;
    }
    if (status !== "authenticated" || !user) return;
    if (initializedUserRef.current === user.id) return;
    initializedUserRef.current = user.id;
    void load();
  }, [load, router, status, syncIdentity, user]);

  const identity = collection?.identity;
  useEffect(() => {
    if (status !== "authenticated" || !user?.is_official_member || !collection || busy) return;
    if (identity?.is_member_card && !identity.card_needs_refresh) return;
    const syncKey = [
      user.id,
      user.level,
      user.fan_token_lifetime_earned,
      identity?.token_id || "new",
      identity?.metadata_version || 0,
    ].join(":");
    if (autoCardSyncKeyRef.current === syncKey) return;
    autoCardSyncKeyRef.current = syncKey;
    void runMembershipCardAction();
  }, [busy, collection, identity, runMembershipCardAction, status, user]);
  const identityContractAddress = identity?.contract_address as `0x${string}` | undefined;
  const walletAddress = user?.primary_wallet.address as `0x${string}` | undefined;
  const identityChainId = identity?.chain_id as 10143 | 143 | undefined;
  const {
    data: rawChainTokenId,
    isLoading: chainTokenLoading,
  } = useReadContract({
    address: identityContractAddress,
    abi: membershipIdentityArtifact.abi as Abi,
    functionName: "identityTokenOf",
    args: walletAddress ? [walletAddress] : undefined,
    chainId: identityChainId,
    query: {
      enabled: Boolean(identityContractAddress && walletAddress && identityChainId),
      refetchInterval: 15_000,
    },
  });
  const chainTokenId = typeof rawChainTokenId === "bigint" ? rawChainTokenId : null;
  const {
    data: rawChainOwner,
    isLoading: chainOwnerLoading,
  } = useReadContract({
    address: identityContractAddress,
    abi: membershipIdentityArtifact.abi as Abi,
    functionName: "ownerOf",
    args: chainTokenId && chainTokenId > 0n ? [chainTokenId] : undefined,
    chainId: identityChainId,
    query: {
      enabled: Boolean(identityContractAddress && identityChainId && chainTokenId && chainTokenId > 0n),
      refetchInterval: 15_000,
    },
  });
  const chainOwner = typeof rawChainOwner === "string" ? rawChainOwner : null;
  const chainVerified = Boolean(
    walletAddress &&
      chainTokenId &&
      chainTokenId > 0n &&
      chainOwner?.toLowerCase() === walletAddress.toLowerCase() &&
      (!identity?.token_id || chainTokenId === BigInt(identity.token_id)),
  );
  const chainChecking = chainTokenLoading || Boolean(chainTokenId && chainTokenId > 0n && chainOwnerLoading);

  if (!user || loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f7f7fb] pt-24 dark:bg-jacarta-900 dark:text-white">
        <span className="mr-3 h-5 w-5 animate-spin rounded-full border-2 border-accent/25 border-t-accent" />
        正在读取链上收藏...
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f7f7fb] pb-24 pt-[88px] dark:bg-jacarta-900">
      <div className="community-reveal relative h-[220px] overflow-hidden sm:h-[300px]">
        <Image
          fill
          priority
          src="/img/fanora/eason-concert.webp"
          alt="Fanora 演唱会会员收藏封面"
          sizes="100vw"
          className="object-cover object-center"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#140d2d]/65 via-transparent to-black/10" />
      </div>

      <section className="community-reveal relative bg-white pb-10 pt-24 [animation-delay:80ms] dark:bg-jacarta-800 sm:pt-28">
        <div className="absolute left-1/2 top-0 z-10 -translate-x-1/2 -translate-y-1/2">
          <div className="relative">
            <UserAvatar
              avatarUrl={user.avatar_url}
              seed={user.id}
              displayName={user.display_name}
              className="h-32 w-32 rounded-lg border-[5px] border-white shadow-xl dark:border-jacarta-700 sm:h-36 sm:w-36"
            />
            {user.is_official_member ? (
              <span title="Fanora 正式会员" className="absolute -bottom-1 -right-2 flex h-8 w-8 items-center justify-center rounded-full border-[3px] border-white bg-green text-sm font-bold text-white dark:border-jacarta-700">
                ✓
              </span>
            ) : null}
          </div>
        </div>

        <div className="mx-auto max-w-4xl px-5 text-center">
          <h1 className="font-display text-3xl font-semibold text-jacarta-700 dark:text-white sm:text-4xl">
            {user.display_name || user.username || "Fanora Member"}
          </h1>
          <button
            type="button"
            onClick={() => void copyWallet()}
            title="复制钱包地址"
            className="mt-4 inline-flex items-center gap-2 rounded-full border border-jacarta-100 bg-jacarta-50 px-4 py-2 font-mono text-xs text-jacarta-600 transition-colors hover:border-accent hover:text-accent dark:border-white/10 dark:bg-white/5 dark:text-jacarta-200"
          >
            <span>{shortAddress(user.primary_wallet.address)}</span>
            <span aria-hidden="true">{copied ? "✓" : "⧉"}</span>
          </button>
          <p className="mx-auto mt-5 max-w-xl text-base leading-7 text-jacarta-500 dark:text-jacarta-300">
            {user.bio || "用每一次参与，留下属于自己的 Proof of Fandom。"}
          </p>
          {/* <p className="mt-2 text-sm text-jacarta-400">{formatDate(user.official_member_since)}加入 Fanora</p> */}

          <div className="mx-auto mt-7 grid max-w-3xl grid-cols-2 divide-x divide-y divide-jacarta-100 border-y border-jacarta-100 py-5 dark:divide-white/10 dark:border-white/10 sm:grid-cols-4 sm:divide-y-0">
            <div>
              <p className="text-xs text-jacarta-400">会员等级</p>
              <p className="mt-2 font-display font-semibold text-jacarta-700 dark:text-white">{user.level}</p>
            </div>
            <div>
              <p className="text-xs text-jacarta-400">可用 FAN</p>
              <FanTokenAmount amount={user.fan_token_balance} showSymbol className="mt-2 justify-center font-display font-semibold text-accent" />
            </div>
            <div>
              <p className="text-xs text-jacarta-400">累计 FAN</p>
              <FanTokenAmount amount={user.fan_token_lifetime_earned} showSymbol className="mt-2 justify-center font-display font-semibold text-jacarta-700 dark:text-white" />
            </div>
            <div>
              <p className="text-xs text-jacarta-400">链上收藏</p>
              <p className="mt-2 font-display font-semibold text-jacarta-700 dark:text-white">{collection?.collectibles.length || 0}</p>
            </div>
          </div>
        </div>
      </section>

      <div className="community-reveal border-b border-jacarta-100 bg-white [animation-delay:140ms] dark:border-white/10 dark:bg-jacarta-800">
        <nav className="mx-auto flex max-w-6xl gap-8 overflow-x-auto px-5" aria-label="收藏分类">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`relative shrink-0 py-5 text-sm font-semibold transition-colors ${activeTab === tab.id ? "text-accent" : "text-jacarta-500 hover:text-jacarta-700 dark:text-jacarta-300 dark:hover:text-white"}`}
            >
              {tab.label}
              {activeTab === tab.id ? <span className="absolute inset-x-0 bottom-0 h-0.5 bg-accent" /> : null}
            </button>
          ))}
        </nav>
      </div>

      <div key={activeTab} className="community-reveal mx-auto max-w-6xl px-5 pt-10 [animation-delay:180ms]">
        {notice ? (
          <div className="mb-7 border-l-4 border-accent bg-white px-5 py-4 text-sm text-jacarta-700 shadow-sm dark:bg-jacarta-800 dark:text-white">
            {notice}
          </div>
        ) : null}

        {!user.is_official_member ? (
          <section className="py-14 text-center">
            <h2 className="font-display text-2xl font-semibold text-jacarta-700 dark:text-white">尚未激活会员身份</h2>
            <p className="mx-auto mt-3 max-w-lg text-sm leading-7 text-jacarta-500 dark:text-jacarta-300">
              缴纳当前会费后，系统会更新你的会员等级，并把 FanoraMembershipIdentity 铸造到登录钱包。
            </p>
            <Link href="/membership/join" className="mt-6 inline-flex rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-white">
              前往入会
            </Link>
          </section>
        ) : null}

        {user.is_official_member && activeTab === "identity" ? (
          <IdentityPanel
            identity={identity}
            syncStatus={collection?.identity_sync_status || "NOT_CONFIGURED"}
            level={user.level}
            walletAddress={user.primary_wallet.address}
            chainTokenId={chainTokenId}
            chainOwner={chainOwner}
            chainVerified={chainVerified}
            chainChecking={chainChecking}
            fanTokenBalance={user.fan_token_balance}
            fanTokenLifetimeEarned={user.fan_token_lifetime_earned}
            busy={Boolean(busy)}
            syncPhase={identityPhase}
            cardPhase={cardPhase}
            downloading={downloadingCard}
            onSync={() => void (identity?.is_member_card ? runMembershipCardAction() : syncIdentity())}
            onCardAction={() => void runMembershipCardAction()}
            onDownload={() => void downloadMembershipCard()}
          />
        ) : null}

        {user.is_official_member && activeTab === "collectibles" ? (
          <section>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase text-accent">Collected on Monad</p>
                <h2 className="mt-2 font-display text-2xl font-semibold text-jacarta-700 dark:text-white">我的链上收藏</h2>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-jacarta-400">{collection?.collectibles.length || 0} 项</span>
                <Link href="/collections/create" className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-dark">
                  发布 NFT
                </Link>
              </div>
            </div>
            {collection?.collectibles.length ? (
              <div className="mt-7 grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {collection.collectibles.map((item, index) => (
                  <CollectibleCard
                    key={item.token_type_id}
                    item={item}
                    index={index}
                    isAvatar={Boolean(item.image_url && user.avatar_url === item.image_url)}
                    avatarBusy={avatarBusyTokenId === item.token_type_id}
                    onSetAvatar={(target) => void setCollectibleAvatar(target)}
                  />
                ))}
              </div>
            ) : (
              <div className="mt-7 border-y border-jacarta-100 py-16 text-center dark:border-white/10">
                <p className="font-display text-lg font-semibold text-jacarta-700 dark:text-white">收藏仍在等待你的故事</p>
                <p className="mt-2 text-sm text-jacarta-400">完成限定活动或通过纪念徽章审核后，资产会出现在这里。</p>
              </div>
            )}
          </section>
        ) : null}

      </div>
    </main>
  );
}
