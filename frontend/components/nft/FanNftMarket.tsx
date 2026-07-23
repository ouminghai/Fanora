"use client";

import axios from "axios";
import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { PhotoSwipeOptions } from "photoswipe";
import { Gallery, Item } from "react-photoswipe-gallery";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import ImageGallery from "@/components/community/ImageGallery";
import MarkdownContent from "@/components/community/MarkdownContent";
import MarkdownEditor from "@/components/community/MarkdownEditor";
import ChainTransactionProgress, { type TransactionPhase } from "@/components/nft/ChainTransactionProgress";
import UserAvatar from "@/components/profile/UserAvatar";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import type { FanNftAiDraft, FanNftCreateResponse, FanNftEngagement, FanNftListing, FanNftPurchaseResponse } from "@/lib/api/types";
import { resetNftTilt, updateNftTilt } from "@/components/nft/nftMotion";

type MarketMode = "market" | "collection" | "item" | "create";
type MarketVariant = "page" | "drawer";

type PublishDraft = {
  name: string;
  description: string;
  theme: string;
  price_fan_tokens: number;
  max_supply: number;
  copyright_declaration: string;
  image_data_url: string;
};

type NftCategory = "recommended" | "co-create" | "story" | "music" | "discussion" | "favorites";

type ImageDimensions = {
  width: number;
  height: number;
};

const NFT_PAGE_SIZE = 50;

const nftCategories: Array<{ id: NftCategory; label: string }> = [
  { id: "recommended", label: "推荐" },
  { id: "co-create", label: "共创" },
  { id: "story", label: "故事" },
  { id: "music", label: "音乐" },
  { id: "discussion", label: "讨论" },
  { id: "favorites", label: "我的收藏" },
];

const itemImageGalleryOptions: PhotoSwipeOptions = {
  bgOpacity: 0.92,
  closeOnVerticalDrag: true,
  showHideAnimationType: "fade",
  wheelToZoom: true,
  paddingFn: () => ({ top: 32, right: 24, bottom: 32, left: 24 }),
};

function errorText(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail || "请求暂时没有完成。";
  if (error instanceof Error) return error.message;
  return "请求暂时没有完成。";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric" }).format(new Date(value));
}

function formatFullDate(value: string | null) {
  if (!value) return "等待确认";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function shortAddress(address: string | null) {
  if (!address) return "等待链上确认";
  return `${address.slice(0, 8)}...${address.slice(-6)}`;
}

function shortHash(hash: string | null) {
  if (!hash) return "等待交易";
  return `${hash.slice(0, 10)}...${hash.slice(-8)}`;
}

function chainName(chainId: number) {
  return chainId === 10143 ? "Monad Testnet" : `Chain ${chainId}`;
}

async function fileToDataUrl(file: File) {
  return await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function categoryText(item: FanNftListing) {
  return [
    item.name,
    item.description,
    item.theme,
    ...item.public_attributes.flatMap((attribute) => [attribute.trait_type, attribute.value]),
  ].join(" ").toLowerCase();
}

function itemMatchesCategory(item: FanNftListing, category: NftCategory) {
  if (category === "recommended") return true;
  if (category === "favorites") return item.favorited;
  const text = categoryText(item);
  if (category === "co-create") return /共创|collab|co-?create|creation|纪念卡/.test(text);
  if (category === "story") return /故事|story|回忆|moment|journey/.test(text);
  if (category === "music") return /音乐|music|concert|演唱|歌|fear and dreams/.test(text);
  return /讨论|discussion|talk|观点|评论/.test(text);
}

function extractMarkdownImageUrls(markdown: string) {
  const urls: string[] = [];
  const pattern = /!\[[^\]]*]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(markdown)) !== null) {
    urls.push(match[1]);
  }
  return Array.from(new Set(urls));
}

function uniqueImageUrls(urls: string[]) {
  return Array.from(new Set(urls.filter(Boolean)));
}

function stripMarkdown(markdown: string) {
  return markdown
    .replace(/!\[[^\]]*]\([^)]+\)/g, "")
    .replace(/\[([^\]]+)]\([^)]+\)/g, "$1")
    .replace(/[`*_>#-]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function NftCard({
  item,
  index = 0,
  busy,
  selected = false,
  onLike,
  onOpen,
}: {
  item: FanNftListing;
  index?: number;
  busy?: boolean;
  selected?: boolean;
  onLike: (item: FanNftListing) => void;
  onOpen: (item: FanNftListing) => void;
}) {
  const soldOut = item.remaining_supply <= 0;
  const summary = stripMarkdown(item.description) || item.description;
  return (
    <article
      onPointerMove={updateNftTilt}
      onPointerLeave={resetNftTilt}
      onPointerCancel={resetNftTilt}
      onMouseLeave={resetNftTilt}
      className={`nft-tilt-surface group community-reveal overflow-hidden rounded-lg border border-jacarta-100 bg-white shadow-sm dark:border-white/10 dark:bg-jacarta-700 ${selected ? "nft-flow-border" : ""}`}
      style={{ animationDelay: `${Math.min(index, 12) * 55}ms` }}
    >
      <Link href={`/item/${item.id}`} onClick={(event) => { event.preventDefault(); event.currentTarget.blur(); onOpen(item); }} className="block">
        <div className="relative aspect-square overflow-hidden bg-jacarta-100 dark:bg-white/5">
          {item.image_url ? (
            <Image
              fill
              unoptimized
              src={item.image_url}
              alt={item.name}
              sizes="(max-width: 639px) 100vw, (max-width: 1023px) 50vw, 25vw"
              className="object-cover transition-transform duration-500 group-hover:scale-[1.04]"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-jacarta-400">等待图片</div>
          )}
          <span className="absolute left-4 top-4 rounded-full bg-black/60 px-3 py-1 text-xs font-semibold text-white backdrop-blur">
            {soldOut ? "已售罄" : `${item.remaining_supply}/${item.max_supply}`}
          </span>
        </div>
      </Link>
      <div className="p-5">
        <div className="flex items-center gap-3">
          <UserAvatar
            avatarUrl={item.creator.avatar_url}
            seed={item.creator.id}
            displayName={item.creator.display_name}
            className="h-9 w-9 rounded-full"
          />
          <div className="min-w-0">
            <Link href={`/collection/${item.creator.id}`} className="block truncate text-sm font-semibold text-jacarta-700 hover:text-accent dark:text-white">
              {item.creator.display_name}
            </Link>
            <p className="text-xs text-jacarta-400">{item.creator.level}</p>
          </div>
        </div>
        <Link href={`/item/${item.id}`} onClick={(event) => { event.preventDefault(); event.currentTarget.blur(); onOpen(item); }} className="mt-4 block">
          <h3 className="truncate font-display text-lg font-semibold text-jacarta-700 group-hover:text-accent dark:text-white">
            {item.name}
          </h3>
          <p className="mt-2 line-clamp-2 min-h-10 text-sm leading-5 text-jacarta-500 dark:text-jacarta-300">
            {summary}
          </p>
        </Link>
        <div className="mt-5 flex items-center justify-between gap-3 border-t border-jacarta-100 pt-4 dark:border-white/10">
          <div>
            {/* <p className="text-xs text-jacarta-400"></p> */}
            <FanTokenAmount amount={item.price_fan_tokens} showSymbol className="mt-1 font-semibold text-accent" />
          </div>
          <button
            type="button"
            onClick={() => onLike(item)}
            disabled={busy}
            aria-label={item.liked ? "取消点赞 NFT" : "点赞 NFT"}
            className={`inline-flex h-10 min-w-10 items-center justify-center gap-1 rounded-full border px-3 text-sm font-semibold transition-colors disabled:opacity-50 ${
              item.liked
                ? "border-red/30 bg-red/10 text-red"
                : "border-jacarta-100 bg-white text-jacarta-500 hover:border-red/30 hover:text-red dark:border-white/10 dark:bg-white/[.04] dark:text-white/65"
            }`}
          >
            <span aria-hidden="true" className="text-base leading-none">{item.liked ? "♥" : "♡"}</span>
            <span>{item.like_count}</span>
          </button>
        </div>
      </div>
    </article>
  );
}

function PublishModal({
  open,
  onClose,
  onPublished,
}: {
  open: boolean;
  onClose: () => void;
  onPublished: (item: FanNftListing) => void;
}) {
  const { user, refreshUser } = useAuth();
  const publishFeeFanTokens = 100;
  const [rendered, setRendered] = useState(open);
  const [visible, setVisible] = useState(open);
  const [draft, setDraft] = useState<PublishDraft>({
    name: "",
    description: "",
    theme: "",
    price_fan_tokens: 10,
    max_supply: 10,
    copyright_declaration: "我确认拥有该图片和内容的发布权，并授权 Fanora 将其作为公开 NFT metadata 发布。",
    image_data_url: "",
  });
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [progressText, setProgressText] = useState("正在准备发布 NFT...");
  const [publishPhase, setPublishPhase] = useState<TransactionPhase>("idle");
  const [storyImageUrls, setStoryImageUrls] = useState<string[]>([]);
  const [aiBrief, setAiBrief] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiAttributes, setAiAttributes] = useState<Array<{ trait_type: string; value: string }>>([]);

  const generateAiDraft = async () => {
    const story = aiBrief.trim() || stripMarkdown(draft.description);
    const theme = draft.theme.trim();
    if (story.length < 10 || theme.length < 2) {
      setNotice("先填写主题，并用至少 10 个字描述希望保存的粉丝故事或画面。");
      return;
    }
    setAiBusy(true);
    setNotice("Agent 正在生成可编辑的 metadata 草稿与 NFT 图片…");
    try {
      const response = await api.post<FanNftAiDraft>("/nft/creations/ai-draft", {
        theme,
        story,
        preferred_name: draft.name || null,
        visual_style: "高级音乐纪念品、电影感舞台光影、方形收藏卡构图",
        reference_notes: "保留粉丝个人故事的情绪，不使用品牌 Logo、水印或可读文字",
        generate_image: true,
      });
      const result = response.data;
      setDraft((current) => ({
        ...current,
        name: result.name,
        description: result.description,
        theme: result.theme,
        image_data_url: result.image_data_url || current.image_data_url,
      }));
      setAiAttributes(result.suggested_attributes);
      setNotice(result.image_data_url
        ? "AI 草稿和图片已生成。请确认名称、描述、图片、定价和数量后再发布。"
        : `metadata 草稿已生成；${result.image_error || "图片服务暂不可用，请上传自己的图片。"}`);
    } catch (error) {
      setNotice(errorText(error));
    } finally {
      setAiBusy(false);
    }
  };

  useEffect(() => {
    if (open) {
      setRendered(true);
      const frame = window.setTimeout(() => setVisible(true), 10);
      return () => window.clearTimeout(frame);
    }
    setVisible(false);
    const timer = window.setTimeout(() => setRendered(false), 220);
    return () => window.clearTimeout(timer);
  }, [open]);

  const publish = async () => {
    if (!user) {
      setNotice("请先连接钱包登录。");
      return;
    }
    if (!user.is_official_member) {
      setNotice("正式入会后才能发布粉丝 NFT。");
      return;
    }
    if (user.fan_token_balance < publishFeeFanTokens) {
      setNotice(`可用 FAN 不足，发布 NFT 需要 ${publishFeeFanTokens} FAN。`);
      return;
    }
    setBusy(true);
    setPublishPhase("processing");
    setNotice(null);
    setProgressText("正在上传图片与 metadata 到 IPFS，并创建链上限量资产。这个过程可能需要几十秒。");
    try {
      const response = await api.post<FanNftCreateResponse>("/nft/creations", {
        ...draft,
        story_image_urls: storyImageUrls,
        public_attributes: aiAttributes.length ? aiAttributes : [{ trait_type: "Theme", value: draft.theme }],
      });
      setProgressText("链上铸造已确认，正在更新你的 NFT 页面。");
      setPublishPhase("complete");
      await refreshUser();
      await new Promise((resolve) => window.setTimeout(resolve, 1400));
      onPublished(response.data.listing);
      setNotice("NFT 已发布到 Pinata，并创建了链上限量资产。");
      setDraft((current) => ({ ...current, name: "", description: "", theme: "", image_data_url: "" }));
      setStoryImageUrls([]);
      setAiAttributes([]);
      setAiBrief("");
    } catch (error) {
      setPublishPhase("idle");
      setNotice(errorText(error));
    } finally {
      setBusy(false);
    }
  };

  if (!rendered) return null;

  return (
    <div
      className={`fixed inset-0 z-[1000] flex items-center justify-center bg-black/70 px-4 py-8 backdrop-blur-sm transition-opacity duration-200 ${
        visible ? "opacity-100" : "opacity-0"
      }`}
    >
      <section
        className={`relative max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-lg border border-jacarta-100 bg-white p-6 shadow-2xl transition-all duration-200 dark:border-white/10 dark:bg-jacarta-800 ${
          visible ? "translate-y-0 scale-100 opacity-100" : "translate-y-3 scale-95 opacity-0"
        }`}
      >
        <button
          type="button"
          onClick={onClose}
          disabled={busy}
          aria-label="关闭发布 NFT 弹窗"
          className="absolute right-4 top-4 z-10 grid h-11 w-11 place-items-center rounded-full border border-jacarta-200 bg-white text-2xl font-semibold leading-none text-jacarta-700 shadow-md transition-colors hover:border-accent hover:bg-accent hover:text-white disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/15 dark:bg-white/[.08] dark:text-white/85"
        >
          <span aria-hidden="true" className="block leading-none">×</span>
        </button>

        {busy ? (
          <div className="flex min-h-[520px] flex-col items-center justify-center text-center">
            <Image
              src="/img/process/cyancat.gif"
              alt="正在发布 NFT"
              width={220}
              height={220}
              unoptimized
              className="h-20 w-20 object-contain sm:h-24 sm:w-24"
            />
            {publishPhase !== "idle" ? (
              <ChainTransactionProgress
                phase={publishPhase}
                kind="publish"
                title={publishPhase === "complete" ? "NFT 已形成" : "正在发布 NFT"}
                detail={progressText}
                artifactName={draft.name || "Fanora NFT"}
                imageUrl={draft.image_data_url}
              />
            ) : null}
          </div>
        ) : (
          <>
        <div className="flex flex-wrap items-center justify-between gap-4 pr-10">
          <div>
            <p className="text-xs font-bold uppercase text-accent">Create Fan NFT</p>
            <h2 className="mt-2 font-display text-2xl font-semibold text-jacarta-700 dark:text-white">发布限量粉丝 NFT</h2>
          </div>
          <div className="grid gap-2 rounded-lg bg-jacarta-50 px-4 py-3 text-sm dark:bg-white/[.04] sm:grid-cols-2">
          <div>
            <p className="text-xs text-jacarta-400">可用 FAN</p>
            <FanTokenAmount amount={user?.fan_token_balance ?? 0} showSymbol className="mt-1 font-semibold text-jacarta-700 dark:text-white" />
          </div>
          <div>
            <p className="text-xs text-jacarta-400">发布费</p>
            <FanTokenAmount amount={publishFeeFanTokens} showSymbol className="mt-1 font-semibold text-accent" />
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[300px_1fr]">
        <div className="grid content-start gap-3">
        <label className="flex aspect-square cursor-pointer flex-col items-center justify-center overflow-hidden rounded-lg border border-dashed border-jacarta-200 bg-jacarta-50 text-center text-sm text-jacarta-400 dark:border-white/10 dark:bg-white/[.04]">
          <span className="mb-3 text-xs font-semibold text-jacarta-500 dark:text-jacarta-200">NFT 图片</span>
          {draft.image_data_url ? (
            <Image src={draft.image_data_url} alt="NFT 预览" width={300} height={300} className="h-full w-full object-cover" />
          ) : (
            <span>上传图片</span>
          )}
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="sr-only"
            onChange={async (event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              const imageDataUrl = await fileToDataUrl(file);
              setDraft((current) => ({ ...current, image_data_url: imageDataUrl }));
            }}
          />
        </label>
        <textarea
          value={aiBrief}
          onChange={(event) => setAiBrief(event.target.value)}
          maxLength={1500}
          className="min-h-24 rounded-lg border-jacarta-100 text-sm dark:border-white/10 dark:bg-jacarta-900 dark:text-white"
          placeholder="描述希望 AI 保存的粉丝故事、舞台瞬间或视觉意象…"
        />
        <button
          type="button"
          onClick={() => void generateAiDraft()}
          disabled={aiBusy || busy}
          className="rounded-lg border border-accent/30 bg-accent/10 px-4 py-3 text-sm font-semibold text-accent transition-colors hover:bg-accent hover:text-white disabled:opacity-50"
        >
          {aiBusy ? "AI 生成中…" : "AI 生成草稿与图片"}
        </button>
        <p className="text-xs leading-5 text-jacarta-400">生成结果只会填入草稿，不会自动设置价格、供应量或上链发布。</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold text-jacarta-700 dark:text-white">
            NFT 名称
            <input className="rounded-lg border-jacarta-100 font-normal dark:border-white/10 dark:bg-jacarta-900 dark:text-white" placeholder="例如 FEAR and DREAMS 纪念卡" value={draft.name} onChange={(event) => setDraft({...draft, name: event.target.value})} />
          </label>
          <label className="grid gap-2 text-sm font-semibold text-jacarta-700 dark:text-white">
            主题 / 分类
            <input className="rounded-lg border-jacarta-100 font-normal dark:border-white/10 dark:bg-jacarta-900 dark:text-white" placeholder="例如 音乐、共创、故事" value={draft.theme} onChange={(event) => setDraft({...draft, theme: event.target.value})} />
          </label>
          <label className="grid gap-2 text-sm font-semibold text-jacarta-700 dark:text-white">
            定价 FAN
            <input type="number" min={1} className="rounded-lg border-jacarta-100 font-normal dark:border-white/10 dark:bg-jacarta-900 dark:text-white" value={draft.price_fan_tokens} onChange={(event) => setDraft({...draft, price_fan_tokens: Number(event.target.value)})} />
          </label>
          <label className="grid gap-2 text-sm font-semibold text-jacarta-700 dark:text-white">
            发行数量
            <input type="number" min={1} max={1000} className="rounded-lg border-jacarta-100 font-normal dark:border-white/10 dark:bg-jacarta-900 dark:text-white" value={draft.max_supply} onChange={(event) => setDraft({...draft, max_supply: Number(event.target.value)})} />
          </label>
          <label className="grid gap-2 text-sm font-semibold text-jacarta-700 sm:col-span-2 dark:text-white">
            NFT 故事描述
            <MarkdownEditor
              value={draft.description}
              onChange={(description) => setDraft((current) => ({ ...current, description }))}
              maxLength={1000}
              imageUrls={storyImageUrls}
              onImageUrlsChange={setStoryImageUrls}
              onImageError={setNotice}
            />
          </label>
          <label className="grid gap-2 text-sm font-semibold text-jacarta-700 sm:col-span-2 dark:text-white">
            版权声明
            <textarea className="min-h-20 rounded-lg border-jacarta-100 font-normal dark:border-white/10 dark:bg-jacarta-900 dark:text-white" value={draft.copyright_declaration} onChange={(event) => setDraft({...draft, copyright_declaration: event.target.value})} />
          </label>
        </div>
      </div>
      <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
        {notice ? <p className="text-sm text-accent">{notice}</p> : <span />}
        <button type="button" disabled={busy} onClick={() => void publish()} className="min-w-32 rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-white hover:bg-accent-dark disabled:opacity-50">
          {busy ? "正在发布..." : "发布 NFT"}
        </button>
      </div>
          </>
        )}
      </section>
    </div>
  );
}

type ItemTab = "details" | "chain" | "activity";

function VerifiedMark() {
  return (
    <span className="nft-flow-border inline-flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-green dark:border-jacarta-600">
      <span className="text-xs font-bold text-white">✓</span>
    </span>
  );
}

function ItemImagePreview({ imageUrl, name, verified }: { imageUrl: string | null; name: string; verified: boolean }) {
  const [dimensions, setDimensions] = useState<ImageDimensions>({ width: 1600, height: 1600 });

  useEffect(() => {
    if (!imageUrl) return;
    let cancelled = false;
    const sourceImage = new window.Image();
    sourceImage.onload = () => {
      if (!cancelled && sourceImage.naturalWidth > 0 && sourceImage.naturalHeight > 0) {
        setDimensions({ width: sourceImage.naturalWidth, height: sourceImage.naturalHeight });
      }
    };
    sourceImage.src = imageUrl;
    return () => {
      cancelled = true;
    };
  }, [imageUrl]);

  if (!imageUrl) {
    return (
      <div className="flex min-h-[400px] h-full items-center justify-center overflow-hidden rounded-2.5xl bg-white text-sm text-jacarta-400 shadow-sm dark:bg-jacarta-700">
        等待 NFT 图片
      </div>
    );
  }

  return (
    <Gallery options={itemImageGalleryOptions} withCaption>
      <Item<HTMLButtonElement>
        original={imageUrl}
        thumbnail={imageUrl}
        width={dimensions.width}
        height={dimensions.height}
        alt={name}
        caption={name}
      >
        {({ ref, open }) => (
          <button
            ref={ref}
            type="button"
            onClick={open}
            onPointerMove={updateNftTilt}
            onPointerLeave={resetNftTilt}
            onPointerCancel={resetNftTilt}
            onMouseLeave={resetNftTilt}
            aria-label={`放大查看 ${name}`}
            className={`nft-tilt-surface group relative h-full min-h-[400px] w-full overflow-hidden rounded-2.5xl bg-white shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent dark:bg-jacarta-700 ${verified ? "nft-flow-border" : ""}`}
          >
            <Image
              fill
              unoptimized
              priority
              src={imageUrl}
              alt={name}
              sizes="(max-width: 767px) 100vw, 540px"
              className="object-contain transition-transform duration-300 group-hover:scale-[1.02]"
            />
          </button>
        )}
      </Item>
    </Gallery>
  );
}

function FanNftTabs({ item, activeTab, onTabChange }: { item: FanNftListing; activeTab: ItemTab; onTabChange: (tab: ItemTab) => void }) {
  const storyImages = uniqueImageUrls([...extractMarkdownImageUrls(item.description), ...(item.story_image_urls ?? [])]);
  const tabs: Array<{ id: ItemTab; label: string }> = [
    { id: "details", label: "创作详情" },
    { id: "chain", label: "链上信息" },
    { id: "activity", label: "铸造记录" },
  ];
  return (
    <section className="mt-14">
      <div className="flex flex-wrap gap-8 border-b border-jacarta-100 dark:border-jacarta-600">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onTabChange(tab.id)}
            className={`relative pb-4 text-base font-semibold transition-colors ${
              activeTab === tab.id ? "text-jacarta-700 dark:text-white" : "text-jacarta-400 hover:text-accent"
            }`}
          >
            {tab.label}
            {activeTab === tab.id ? <span className="absolute inset-x-0 -bottom-px h-0.5 bg-accent" /> : null}
          </button>
        ))}
      </div>

      {activeTab === "details" ? (
        <div className="grid gap-6 rounded-b-2lg border border-t-0 border-jacarta-100 bg-white p-6 dark:border-jacarta-600 dark:bg-jacarta-700 md:grid-cols-[1.2fr_.8fr]">
          <div>
            <h3 className="font-display text-xl font-semibold text-jacarta-700 dark:text-white">{item.name}</h3>
            <MarkdownContent content={item.description} className="mt-4" />
            <p className="mt-5 text-sm text-jacarta-400">主题：{item.theme}</p>
          </div>
          <div className="grid content-start gap-3">
            <ImageGallery images={storyImages} alt={`${item.name} 故事图片`} className="aspect-[4/3] rounded-lg bg-jacarta-100 dark:bg-white/[.04]" />
            {item.public_attributes.length ? item.public_attributes.map((attribute) => (
              <div key={`${attribute.trait_type}-${attribute.value}`} className="rounded-lg bg-jacarta-50 p-4 dark:bg-white/[.04]">
                <p className="text-xs text-jacarta-400">{attribute.trait_type}</p>
                <p className="mt-1 font-semibold text-jacarta-700 dark:text-white">{attribute.value}</p>
              </div>
            )) : (
              <div className="rounded-lg bg-jacarta-50 p-4 text-sm text-jacarta-400 dark:bg-white/[.04]">暂无公开属性</div>
            )}
          </div>
        </div>
      ) : null}

      {activeTab === "chain" ? (
        <div className="rounded-b-2lg border border-t-0 border-jacarta-100 bg-white p-6 dark:border-jacarta-600 dark:bg-jacarta-700">
          <dl className="grid gap-4 md:grid-cols-2">
            <div><dt className="text-sm text-jacarta-400">Contract Address:</dt><dd className="mt-1 break-all font-mono text-sm text-jacarta-700 dark:text-white">{item.contract_address || "等待链上确认"}</dd></div>
            <div><dt className="text-sm text-jacarta-400">Token ID:</dt><dd className="mt-1 font-mono text-sm text-jacarta-700 dark:text-white">{item.token_id ?? "等待链上确认"}</dd></div>
            <div><dt className="text-sm text-jacarta-400">Token Standard:</dt><dd className="mt-1 font-semibold text-jacarta-700 dark:text-white">ERC-1155</dd></div>
            <div><dt className="text-sm text-jacarta-400">Blockchain:</dt><dd className="mt-1 font-semibold text-jacarta-700 dark:text-white">{chainName(item.chain_id)}</dd></div>
            <div><dt className="text-sm text-jacarta-400">Metadata URI:</dt><dd className="mt-1 break-all font-mono text-sm text-jacarta-700 dark:text-white">{item.metadata_uri || "等待 Pinata metadata"}</dd></div>
            <div><dt className="text-sm text-jacarta-400">Status:</dt><dd className="mt-1 font-semibold text-jacarta-700 dark:text-white">{item.status}</dd></div>
          </dl>
          {item.explorer_url ? (
            <a href={item.explorer_url} target="_blank" rel="noreferrer" className="mt-6 inline-flex rounded-lg bg-accent px-5 py-3 text-sm font-semibold text-white hover:bg-accent-dark">
              在 MonadVision 查看
            </a>
          ) : null}
        </div>
      ) : null}

      {activeTab === "activity" ? (
        <div className="overflow-hidden rounded-b-2lg border border-t-0 border-jacarta-100 bg-white dark:border-jacarta-600 dark:bg-jacarta-700">
          <div className="grid grid-cols-[1fr_1.2fr_1.2fr_1fr] gap-4 bg-jacarta-50 px-5 py-4 text-sm font-semibold text-jacarta-500 dark:bg-white/[.06] dark:text-jacarta-200">
            <span>Event</span><span>From</span><span>Transaction</span><span>Date</span>
          </div>
          {item.mint_records.length ? item.mint_records.map((record) => (
            <div key={record.id} className="grid grid-cols-[1fr_1.2fr_1.2fr_1fr] gap-4 border-t border-jacarta-100 px-5 py-4 text-sm dark:border-jacarta-600">
              <span className="font-semibold text-jacarta-700 dark:text-white">Mint x{record.amount}</span>
              <span className="min-w-0">
                <span className="block truncate text-accent">{record.buyer.display_name}</span>
                <span className="font-mono text-xs text-jacarta-400">{shortAddress(record.wallet_address)}</span>
              </span>
              <span className="font-mono text-xs text-jacarta-500 dark:text-jacarta-300">
                {record.transaction_hash ? <a className="hover:text-accent" href={`https://testnet.monadexplorer.com/tx/${record.transaction_hash}`} target="_blank" rel="noreferrer">{shortHash(record.transaction_hash)} ↗</a> : "等待链上交易"}
              </span>
              <span className="text-jacarta-400">{formatFullDate(record.minted_at || record.created_at)}</span>
            </div>
          )) : (
            <div className="px-5 py-10 text-center text-sm text-jacarta-400">还没有粉丝购买铸造记录。</div>
          )}
        </div>
      ) : null}
    </section>
  );
}

type FanNftMarketProps = {
  mode: MarketMode;
  itemId?: string;
  variant?: MarketVariant;
  onClose?: () => void;
};

export default function FanNftMarket({ mode, itemId, variant = "page", onClose }: FanNftMarketProps) {
  const params = useParams<{ id?: string }>();
  const router = useRouter();
  const { user, refreshUser } = useAuth();
  const [items, setItems] = useState<FanNftListing[]>([]);
  const [item, setItem] = useState<FanNftListing | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ItemTab>("details");
  const [activeCategory, setActiveCategory] = useState<NftCategory>("recommended");
  const [publishOpen, setPublishOpen] = useState(mode === "create");
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [drawerClosing, setDrawerClosing] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const nextOffset = useRef(0);
  const loadingItems = useRef(false);
  const loadMoreSentinel = useRef<HTMLDivElement | null>(null);
  const [hasMoreItems, setHasMoreItems] = useState(true);
  const [loadingMoreItems, setLoadingMoreItems] = useState(false);
  const [buyPhase, setBuyPhase] = useState<TransactionPhase>("idle");
  const drawerScrollRef = useRef<HTMLElement | null>(null);

  const id = itemId || params?.id;
  useLayoutEffect(() => {
    if (mode !== "item" || variant !== "drawer" || !drawerScrollRef.current) return;
    drawerScrollRef.current.scrollTop = 0;
  }, [id, loading, mode, variant]);

  const loadItemPage = useCallback(async (reset = false) => {
    if (loadingItems.current) return;
    loadingItems.current = true;
    if (reset) setLoading(true);
    else setLoadingMoreItems(true);
    const offset = reset ? 0 : nextOffset.current;
    try {
      const response = await api.get<FanNftListing[]>(`/nft/creations?limit=${NFT_PAGE_SIZE}&offset=${offset}`);
      const page = mode === "collection" && id
        ? response.data.filter((entry) => entry.creator.id === id)
        : response.data;
      setItems((current) => {
        if (reset) return page;
        const knownIds = new Set(current.map((entry) => entry.id));
        return [...current, ...page.filter((entry) => !knownIds.has(entry.id))];
      });
      nextOffset.current = offset + response.data.length;
      setHasMoreItems(response.data.length === NFT_PAGE_SIZE);
      if (mode === "collection" && reset) setItem(page[0] || null);
    } catch (error) {
      setNotice(errorText(error));
    } finally {
      loadingItems.current = false;
      if (reset) setLoading(false);
      else setLoadingMoreItems(false);
    }
  }, [id, mode]);

  const load = useCallback(async () => {
    if (mode !== "item") {
      await loadItemPage(true);
      return;
    }
    setLoading(true);
    try {
      if (id) {
        const response = await api.get<FanNftListing>(`/nft/creations/${id}`);
        setItem(response.data);
      }
    } catch (error) {
      setNotice(errorText(error));
    } finally {
      setLoading(false);
    }
  }, [id, loadItemPage, mode]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (mode === "create") setPublishOpen(true);
  }, [mode]);

  useEffect(() => {
    if (mode === "item") return;
    const handlePopState = () => {
      const match = window.location.pathname.match(/^\/item\/([^/]+)$/);
      if (match) {
        setSelectedItemId(match[1]);
        setDrawerClosing(false);
      } else {
        setSelectedItemId(null);
        setDrawerClosing(false);
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [mode]);

  useEffect(() => {
    if (!selectedItemId) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previousOverflow; };
  }, [selectedItemId]);

  useEffect(() => () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
  }, []);

  const visibleItems = useMemo(() => {
    const next = mode === "item" && item ? [item] : items;
    return next.filter((entry) => itemMatchesCategory(entry, activeCategory));
  }, [activeCategory, item, items, mode]);

  useEffect(() => {
    const sentinel = loadMoreSentinel.current;
    if (mode === "item" || !sentinel || !hasMoreItems || loading) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) void loadItemPage();
      },
      { rootMargin: "600px 0px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMoreItems, loadItemPage, loading, mode, visibleItems.length]);

  const buy = async () => {
    if (!item) return;
    if (!user) {
      router.push("/login");
      return;
    }
    setBusy("buy");
    setBuyPhase("processing");
    setNotice(null);
    try {
      const response = await api.post<FanNftPurchaseResponse>(`/nft/creations/${item.id}/buy`);
      setItem(response.data.listing);
      await refreshUser();
      setBuyPhase("complete");
      setNotice("购买成功，NFT 已铸造到你的钱包。");
      await new Promise((resolve) => window.setTimeout(resolve, 1400));
      setBuyPhase("idle");
    } catch (error) {
      setBuyPhase("idle");
      setNotice(errorText(error));
    } finally {
      setBusy(null);
    }
  };

  const toggleEngagement = async (action: "like" | "favorite") => {
    if (!item) return;
    if (!user) {
      router.push("/login");
      return;
    }
    setBusy(action);
    setNotice(null);
    try {
      const response = await api.post<FanNftEngagement>(`/nft/creations/${item.id}/${action}`);
      setItem((current) => current ? {
        ...current,
        liked: response.data.liked,
        favorited: response.data.favorited,
        like_count: response.data.like_count,
        favorite_count: response.data.favorite_count,
      } : current);
    } catch (error) {
      setNotice(errorText(error));
    } finally {
      setBusy(null);
    }
  };

  const toggleCardLike = async (target: FanNftListing) => {
    if (!user) {
      router.push("/login");
      return;
    }
    setBusy(`like:${target.id}`);
    setNotice(null);
    try {
      const response = await api.post<FanNftEngagement>(`/nft/creations/${target.id}/like`);
      const patch = {
        liked: response.data.liked,
        favorited: response.data.favorited,
        like_count: response.data.like_count,
        favorite_count: response.data.favorite_count,
      };
      setItems((current) => current.map((entry) => entry.id === target.id ? { ...entry, ...patch } : entry));
      setItem((current) => current?.id === target.id ? { ...current, ...patch } : current);
      await refreshUser();
    } catch (error) {
      setNotice(errorText(error));
    } finally {
      setBusy(null);
    }
  };

  const openItem = (target: FanNftListing) => {
    window.history.pushState({ nftDrawer: true, itemId: target.id }, "", `/item/${target.id}`);
    setDrawerClosing(false);
    setSelectedItemId(target.id);
  };

  const closeItem = useCallback(() => {
    if (!selectedItemId || drawerClosing) return;
    setDrawerClosing(true);
    closeTimer.current = setTimeout(() => {
      if (window.location.pathname.startsWith("/item/")) window.history.back();
      else {
        setSelectedItemId(null);
        setDrawerClosing(false);
      }
    }, 220);
  }, [drawerClosing, selectedItemId]);

  useEffect(() => {
    if (!selectedItemId) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeItem();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [closeItem, selectedItemId]);

  const backToGallery = () => {
    if (variant === "drawer") {
      onClose?.();
      return;
    }
    if (window.history.length > 1) {
      router.back();
      return;
    }
    router.push("/collections");
  };

  const Root = mode === "item" && variant === "drawer" ? "div" : "main";
  return (
    <Root ref={(node) => { drawerScrollRef.current = node; }} className={mode === "item" ? variant === "drawer" ? "community-letter-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain bg-[#f7f7fb] dark:bg-jacarta-900" : "min-h-screen bg-[#f7f7fb] pb-24 pt-[88px] dark:bg-jacarta-900" : "web3-page-shell min-h-screen pb-24 pt-28 md:pt-32"}>
      <div className={mode === "item" ? variant === "drawer" ? "mx-auto max-w-7xl px-5 pt-16 md:px-8 md:pt-14" : "mx-auto max-w-7xl px-5 pt-12" : "container"}>
        <PublishModal
          open={publishOpen}
          onClose={() => {
            setPublishOpen(false);
            if (mode === "create") router.push("/collections");
          }}
          onPublished={(created) => router.push(`/item/${created.id}`)}
        />

        {notice ? <div className="community-reveal mb-7 rounded-2xl border border-accent/20 bg-accent/10 px-5 py-4 text-sm font-semibold text-accent-lighter">{notice}</div> : null}

        {loading && mode !== "create" ? (
          <div className="flex min-h-[42vh] items-center justify-center">
            <span aria-label="正在读取 NFT" className="h-8 w-8 animate-spin rounded-full border-2 border-accent/20 border-t-accent" />
          </div>
        ) : null}

        {mode === "item" && item && !loading ? (
          <div className="community-reveal">
          {variant === "page" ? <button
            type="button"
            onClick={backToGallery}
            className="mb-8 inline-flex items-center gap-2 rounded-full border border-jacarta-100 bg-white px-5 py-2.5 text-sm font-semibold text-jacarta-700 transition-colors hover:border-accent hover:text-accent dark:border-white/10 dark:bg-jacarta-700 dark:text-white"
          >
            <span aria-hidden="true">←</span>
            返回 Gallery
          </button> : null}
          <section className="md:flex md:flex-wrap md:items-stretch">
            <figure className="mb-8 flex md:w-2/5 md:flex-shrink-0 md:flex-grow-0 md:basis-auto lg:w-1/2">
              <ItemImagePreview imageUrl={item.image_url} name={item.name} verified={Boolean(item.contract_address && item.token_id !== null && ["MINTED", "CONFIRMED"].includes(item.status))} />
            </figure>
            <div className="md:w-3/5 md:basis-auto md:pl-8 lg:w-1/2 lg:pl-[3.75rem]">
              <div className="mb-3 flex items-center gap-4">
                <div className="flex min-w-0 items-center gap-2">
                  <Link href={`/collection/${item.creator.id}`} className="truncate text-sm font-bold text-accent">
                    {item.creator.display_name}
                  </Link>
                  <VerifiedMark />
                </div>
                <div className="ml-auto flex shrink-0 gap-2">
                  <button
                    type="button"
                    onClick={() => void toggleEngagement("like")}
                    disabled={Boolean(busy)}
                    className={`flex items-center gap-2 rounded-xl border px-4 py-2 text-sm transition-colors ${
                      item.liked
                        ? "border-red/30 bg-red/10 text-red"
                        : "border-jacarta-100 bg-white text-jacarta-500 hover:text-red dark:border-jacarta-600 dark:bg-jacarta-700 dark:text-jacarta-200"
                    }`}
                    aria-label="点赞 NFT"
                  >
                    ♥ {item.like_count}
                  </button>
                  <button
                    type="button"
                    onClick={() => void toggleEngagement("favorite")}
                    disabled={Boolean(busy)}
                    className={`flex items-center gap-2 rounded-xl border px-4 py-2 text-sm transition-colors ${
                      item.favorited
                        ? "border-accent/40 bg-accent/10 text-accent"
                        : "border-jacarta-100 bg-white text-jacarta-500 hover:text-accent dark:border-jacarta-600 dark:bg-jacarta-700 dark:text-jacarta-200"
                    }`}
                    aria-label="收藏 NFT"
                  >
                    ★ {item.favorite_count}
                  </button>
                </div>
              </div>

              <h1 className="mb-4 font-display text-4xl font-semibold text-jacarta-700 dark:text-white">{item.name}</h1>

              <div className="mb-8 flex flex-wrap items-center gap-x-4 gap-y-2 whitespace-nowrap">
                <FanTokenAmount amount={item.price_fan_tokens} showSymbol className="text-sm font-medium tracking-tight text-green" />
                <span className="text-sm text-jacarta-400 dark:text-jacarta-300">Fixed price</span>
                <span className="text-sm text-jacarta-400 dark:text-jacarta-300">{item.remaining_supply}/{item.max_supply} available</span>
              </div>

              <p className="mb-10 leading-8 dark:text-jacarta-300">{item.description}</p>

              <div className="mb-8 flex flex-wrap">
                <div className="mr-8 mb-4 flex">
                  <figure className="mr-4 shrink-0">
                    <Link href={`/collection/${item.creator.id}`} className="relative block">
                      <UserAvatar avatarUrl={item.creator.avatar_url} seed={item.creator.id} displayName={item.creator.display_name} className="h-12 w-12 rounded-2lg" />
                      <span className="absolute -right-3 top-[60%]"><VerifiedMark /></span>
                    </Link>
                  </figure>
                  <div className="flex flex-col justify-center">
                    <span className="block text-sm text-jacarta-400 dark:text-white">Creator</span>
                    <Link href={`/collection/${item.creator.id}`} className="block text-accent">
                      <span className="text-sm font-bold">@{item.creator.display_name}</span>
                    </Link>
                  </div>
                </div>
                <div className="mb-4 flex">
                  <figure className="mr-4 shrink-0">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2lg bg-jacarta-100 text-xs text-jacarta-500 dark:bg-jacarta-600 dark:text-white">
                      1155
                    </div>
                  </figure>
                  <div className="flex flex-col justify-center">
                    <span className="block text-sm text-jacarta-400 dark:text-white">Owned by</span>
                    <span className="text-sm font-bold text-accent">{item.minted_supply} collectors</span>
                  </div>
                </div>
              </div>

              <div className="rounded-2lg border border-jacarta-100 bg-white p-8 dark:border-jacarta-600 dark:bg-jacarta-700">
                {buyPhase !== "idle" ? (
                  <ChainTransactionProgress
                    phase={buyPhase}
                    kind="mint"
                    compact
                    title={buyPhase === "complete" ? "NFT 已进入钱包" : "正在购买并铸造"}
                    detail={buyPhase === "complete" ? "Monad 已确认交易，收藏记录正在更新。" : "交易已提交，正在连接验证节点并铸造 NFT。"}
                    artifactName={item.name}
                    imageUrl={item.image_url}
                  />
                ) : (
                  <>
                <div className="mb-8 sm:flex sm:flex-wrap">
                  <div className="sm:w-1/2 sm:pr-4 lg:pr-8">
                    <span className="text-sm text-jacarta-400 dark:text-jacarta-300">当前价格</span>
                    <div className="mt-3">
                      <FanTokenAmount amount={item.price_fan_tokens} showSymbol className="font-display text-2xl font-semibold text-green" />
                      <span className="block text-sm text-jacarta-400 dark:text-jacarta-300">发布费和购买均使用 FAN Token</span>
                    </div>
                  </div>
                  <div className="mt-4 dark:border-jacarta-600 sm:mt-0 sm:w-1/2 sm:border-l sm:border-jacarta-100 sm:pl-4 lg:pl-8">
                    <span className="text-sm text-jacarta-400 dark:text-jacarta-300">发行进度</span>
                    <div className="mt-4 h-2 rounded-full bg-jacarta-100 dark:bg-jacarta-600">
                      <div className="h-2 rounded-full bg-accent" style={{ width: `${Math.min(100, Math.round((item.minted_supply / item.max_supply) * 100))}%` }} />
                    </div>
                    <span className="mt-3 block text-sm text-jacarta-400 dark:text-jacarta-300">{item.minted_supply} minted · {item.remaining_supply} remaining</span>
                  </div>
                </div>
                <button type="button" disabled={Boolean(busy) || item.remaining_supply <= 0} onClick={() => void buy()} className="inline-block w-full rounded-full bg-accent px-8 py-3 text-center font-semibold text-white shadow-accent-volume transition-all hover:bg-accent-dark disabled:opacity-50">
                  {busy === "buy" ? "正在购买..." : item.remaining_supply <= 0 ? "已售罄" : "购买并铸造"}
                </button>
                  </>
                )}
              </div>
            </div>
          </section>
          <FanNftTabs item={item} activeTab={activeTab} onTabChange={setActiveTab} />
          </div>
        ) : null}

        {mode !== "item" && !loading ? (
          <>
          <div className="community-reveal sticky top-20 z-10 mb-8 flex items-center gap-4 py-2 [animation-delay:100ms]">
            <nav className="flex min-w-0 flex-1 items-center gap-6 overflow-x-auto" aria-label="NFT 分类">
              {nftCategories.map((category) => (
                <button
                  key={category.id}
                  type="button"
                  onClick={() => setActiveCategory(category.id)}
                  className={`shrink-0 border-b-2 px-0.5 py-3 text-sm font-semibold transition-colors ${
                    activeCategory === category.id
                      ? "border-accent text-white"
                      : "border-transparent text-white/45 hover:text-white"
                  }`}
                >
                  {category.label}
                </button>
              ))}
            </nav>
            <button
              type="button"
              onClick={() => setPublishOpen(true)}
              className="web3-action-button shrink-0 rounded-full px-5 py-2.5 text-sm font-semibold text-white"
            >
              发布 NFT
            </button>
          </div>
          {visibleItems.length ? (
            <section className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {visibleItems.map((entry, index) => (
                <NftCard
                  key={entry.id}
                  item={entry}
                  index={index}
                  busy={busy === `like:${entry.id}`}
                  selected={selectedItemId === entry.id}
                  onLike={(target) => void toggleCardLike(target)}
                  onOpen={openItem}
                />
              ))}
            </section>
          ) : (
            <div className="community-reveal py-20 text-center text-white/40">还没有粉丝 NFT。</div>
          )}
          <div ref={loadMoreSentinel} aria-hidden="true" className="flex min-h-24 items-center justify-center">
            {loadingMoreItems ? (
              <span className="h-8 w-8 animate-spin rounded-full border-2 border-accent/20 border-t-accent" />
            ) : hasMoreItems ? (
              <span className="text-xs text-white/30">继续向下浏览</span>
            ) : items.length > 0 ? (
              <span className="text-xs text-white/30">已经浏览完全部 NFT</span>
            ) : null}
          </div>
          </>
        ) : null}
      </div>
      {mode !== "item" && selectedItemId ? (
        <div
          role="presentation"
          onMouseDown={(event) => { if (event.target === event.currentTarget) closeItem(); }}
          className={`community-drawer-backdrop fixed inset-0 z-[1000] flex items-end justify-center bg-[#050619]/75 px-0 pt-5 backdrop-blur-md md:px-8 md:pt-10 ${drawerClosing ? "is-closing" : ""}`}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-label="NFT 详情"
            className="community-letter-drawer relative flex min-h-[95dvh] max-h-[calc(100dvh-1.25rem)] w-full max-w-7xl flex-col overflow-hidden rounded-t-lg bg-[#f7f7fb] shadow-[0_45px_140px_rgba(0,0,0,.72),0_0_70px_rgba(131,88,255,.16)] dark:bg-jacarta-900 md:max-h-[calc(100dvh-2.5rem)]"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              onClick={closeItem}
              aria-label="关闭 NFT 详情"
              className="absolute right-4 top-4 z-20 flex h-10 w-10 items-center justify-center rounded-full border border-jacarta-100 bg-white/90 text-2xl leading-none text-jacarta-600 shadow-lg transition-colors hover:border-accent hover:text-accent dark:border-white/15 dark:bg-[#090b23]/85 dark:text-white/75 dark:hover:border-accent/50 dark:hover:text-white"
            >
              <span aria-hidden="true" className="-translate-y-px">×</span>
            </button>
            <FanNftMarket mode="item" itemId={selectedItemId} variant="drawer" onClose={closeItem} />
          </section>
        </div>
      ) : null}
    </Root>
  );
}
