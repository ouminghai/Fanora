"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, FileImage, Gem, LoaderCircle, Plus, Search, X } from "lucide-react";
import { api, uploadImage } from "@/lib/api/client";
import { apiErrorMessage } from "@/lib/api/errors";
import type { CommunityPostSummary, FanNftListing, MyCollection, NftVisualTemplate } from "@/lib/api/types";
import styles from "@/components/nft/NftVisualTemplateModal.module.css";

type Props = {
  open: boolean;
  templates: NftVisualTemplate[];
  selectedId: string;
  onClose: () => void;
  onSelect: (template: NftVisualTemplate) => void;
  onCreated: (template: NftVisualTemplate) => void;
};

type Tab = "library" | "posts" | "nfts" | "create";
type NftSource = { id: string; name: string; description: string; category: string; imageUrl: string; referenceUrls: string[] };

const PAGE_SIZE = 6;
const POST_PAGE_SIZE = 8;

function Pager({ page, total, pageSize = PAGE_SIZE, onChange }: { page: number; total: number; pageSize?: number; onChange: (page: number) => void }) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  if (pageCount <= 1) return null;
  return <div className={styles.pager}><button type="button" disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="上一页"><ChevronLeft /></button><span>{page} / {pageCount}</span><button type="button" disabled={page >= pageCount} onClick={() => onChange(page + 1)} aria-label="下一页"><ChevronRight /></button></div>;
}

function MasonryImage({ src, alt }: { src: string; alt: string }) {
  // The source dimensions are unknown until load; the natural ratio is required for the masonry layout.
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} loading="lazy" decoding="async" className={styles.masonryImage} />;
}

export default function NftVisualTemplateModal({ open, templates, selectedId, onClose, onSelect, onCreated }: Props) {
  const [tab, setTab] = useState<Tab>("library");
  const [posts, setPosts] = useState<CommunityPostSummary[]>([]);
  const [nfts, setNfts] = useState<NftSource[]>([]);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [selectedPost, setSelectedPost] = useState<CommunityPostSummary | null>(null);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("粉丝周边");
  const [description, setDescription] = useState("");
  const [prompt, setPrompt] = useState("");
  const [referenceUrls, setReferenceUrls] = useState<string[]>([]);
  const [busy, setBusy] = useState<"posts" | "nfts" | "upload" | "create" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => { document.body.style.overflow = previous; window.removeEventListener("keydown", onKeyDown); };
  }, [onClose, open]);

  useEffect(() => {
    if (!open || tab !== "posts" || posts.length) return;
    setBusy("posts");
    api.get<CommunityPostSummary[]>("/community/posts?limit=50&sort=latest")
      .then((response) => setPosts(response.data.filter((post) => Boolean(post.cover_url || post.image_urls.length))))
      .catch((error) => setNotice(apiErrorMessage(error, "Post 图片读取失败。")))
      .finally(() => setBusy(null));
  }, [open, posts.length, tab]);

  useEffect(() => {
    if (!open || tab !== "nfts" || nfts.length) return;
    setBusy("nfts");
    Promise.all([
      api.get<FanNftListing[]>("/nft/me/creations"),
      api.get<MyCollection>("/nft/me"),
    ]).then(([creationsResponse, collectionResponse]) => {
      const creationItems: NftSource[] = creationsResponse.data.flatMap((item) => item.image_url ? [{ id: `creation-${item.id}`, name: item.name, description: item.description, category: item.theme, imageUrl: item.image_url, referenceUrls: [item.image_url, ...item.story_image_urls].slice(0, 6) }] : []);
      const collectibleItems: NftSource[] = collectionResponse.data.collectibles.flatMap((item) => item.image_url ? [{ id: `collectible-${item.token_type_id}`, name: item.name, description: item.description, category: item.category, imageUrl: item.image_url, referenceUrls: [item.image_url] }] : []);
      setNfts([...creationItems, ...collectibleItems].filter((item, index, all) => all.findIndex((candidate) => candidate.imageUrl === item.imageUrl) === index));
    }).catch((error) => setNotice(apiErrorMessage(error, "NFT 图片读取失败。")))
      .finally(() => setBusy(null));
  }, [nfts.length, open, tab]);

  useEffect(() => { setPage(1); }, [query, tab]);

  const visibleTemplates = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return templates;
    return templates.filter((item) => `${item.name} ${item.category} ${item.description}`.toLowerCase().includes(keyword));
  }, [query, templates]);
  const pageItems = <T,>(items: T[], pageSize = PAGE_SIZE) => items.slice((page - 1) * pageSize, page * pageSize);

  const resetCreateForm = () => {
    setSelectedPost(null);
    setName("");
    setCategory("粉丝周边");
    setDescription("");
    setPrompt("");
    setReferenceUrls([]);
    setNotice(null);
  };

  const choosePost = (post: CommunityPostSummary) => {
    setSelectedPost(post);
    setName(`${post.title.slice(0, 28)}视觉模板`);
    setCategory(post.category === "music" ? "音乐" : post.category === "story" ? "故事" : "共创");
    setDescription(`来自社区 Post「${post.title}」的视觉参考。`);
    setPrompt(`Create an original fan-merch NFT inspired by this community story: ${post.body_preview}. Preserve the emotional color, key objects and visual rhythm from the selected references.`);
    setReferenceUrls([post.cover_url, ...post.image_urls].filter((item): item is string => Boolean(item)).slice(0, 6));
    setTab("create");
  };

  const chooseNft = (nft: NftSource) => {
    setSelectedPost(null);
    setName(`${nft.name.slice(0, 30)}视觉模板`);
    setCategory(nft.category || "NFT 收藏");
    setDescription(`从 NFT「${nft.name}」提取的可复用视觉方向。`);
    setPrompt(`Create a new original fan-merch NFT that preserves the visual language, collectible craftsmanship and emotional atmosphere of this NFT reference: ${nft.description}`);
    setReferenceUrls(nft.referenceUrls);
    setTab("create");
  };

  const uploadReferences = async (files: FileList | null) => {
    const selected = Array.from(files || []);
    if (!selected.length) return;
    if (referenceUrls.length + selected.length > 6) { setNotice("每个模板最多 6 张参考图。"); return; }
    setBusy("upload");
    setNotice(null);
    try {
      const urls = await Promise.all(selected.map((file) => uploadImage(file)));
      setReferenceUrls((current) => [...current, ...urls]);
    } catch (error) {
      setNotice(apiErrorMessage(error, "参考图上传 BeeImg 失败。"));
    } finally {
      setBusy(null);
    }
  };

  const createTemplate = async () => {
    if (!name.trim() || !description.trim() || !prompt.trim() || (!referenceUrls.length && !selectedPost)) {
      setNotice("请填写模板名称、说明、提示词并添加至少一张参考图。");
      return;
    }
    setBusy("create");
    setNotice(null);
    try {
      const response = await api.post<NftVisualTemplate>("/nft/creations/agent/templates", {
        name: name.trim(),
        category: category.trim(),
        description: description.trim(),
        prompt: prompt.trim(),
        reference_image_urls: referenceUrls,
        source_post_id: selectedPost?.id ?? null,
        elements: [],
        forbidden: ["Logo", "水印", "可读文字", "未经授权的真实艺人肖像"],
      });
      onCreated(response.data);
      onSelect(response.data);
      resetCreateForm();
      onClose();
    } catch (error) {
      setNotice(apiErrorMessage(error, "视觉模板保存失败。"));
    } finally {
      setBusy(null);
    }
  };

  if (!open) return null;

  return (
    <div className={styles.backdrop} onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section role="dialog" aria-modal="true" aria-label="视觉模板库" className={styles.modal}>
        <header><div><p>VISUAL TEMPLATE VAULT</p><h2>视觉模板库</h2></div><button type="button" onClick={onClose} aria-label="关闭视觉模板库"><X /></button></header>
        <nav aria-label="视觉模板视图">
          <button type="button" className={tab === "library" ? styles.activeTab : ""} onClick={() => setTab("library")}>模板库</button>
          <button type="button" className={tab === "posts" ? styles.activeTab : ""} onClick={() => setTab("posts")}>从 Post 选择</button>
          <button type="button" className={tab === "nfts" ? styles.activeTab : ""} onClick={() => setTab("nfts")}><Gem /> 从 NFT 选择</button>
          <button type="button" className={tab === "create" ? styles.activeTab : ""} onClick={() => setTab("create")}><Plus /> 新建模板</button>
        </nav>
        {notice ? <div className={styles.notice}>{notice}</div> : null}

        {tab === "library" ? <div className={styles.libraryView}>
          <label className={styles.search}><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索模板名称、分类或说明" /></label>
          <div className={styles.masonryGrid}>{pageItems(visibleTemplates).map((template) => <button key={template.id} type="button" className={`${styles.masonryCard} ${template.id === selectedId ? styles.selectedTemplate : ""}`} onClick={() => { onSelect(template); onClose(); }}>
            <span className={styles.masonryImageFrame}><MasonryImage src={template.preview_image_url} alt={template.name} /></span>
            <span className={styles.templateCopy}><strong>{template.name}</strong><small>{template.description}</small><em>{template.is_system ? "官方模板" : "我的模板"} · {template.category}</em></span>
          </button>)}</div><Pager page={page} total={visibleTemplates.length} onChange={setPage} />
        </div> : null}

        {tab === "posts" ? <div className={styles.sourceView}>
          {busy === "posts" ? <div className={styles.loading}><LoaderCircle className="animate-spin" /> 正在读取 Post 图片</div> : <div className={styles.masonryGrid}>{pageItems(posts, POST_PAGE_SIZE).map((post) => {
            const imageUrl = post.cover_url || post.image_urls[0];
            return <button key={post.id} type="button" className={styles.masonryCard} onClick={() => choosePost(post)}>{imageUrl ? <span className={styles.masonryImageFrame}><MasonryImage src={imageUrl} alt={post.title} /></span> : null}<span className={styles.sourceCopy}><strong>{post.title}</strong><small>{post.body_preview}</small><em>{[post.cover_url, ...post.image_urls].filter(Boolean).length} 张参考图</em></span></button>;
          })}</div>}<Pager page={page} total={posts.length} pageSize={POST_PAGE_SIZE} onChange={setPage} /></div> : null}

        {tab === "nfts" ? <div className={styles.sourceView}>
          {busy === "nfts" ? <div className={styles.loading}><LoaderCircle className="animate-spin" /> 正在读取我的 NFT</div> : <div className={styles.masonryGrid}>{pageItems(nfts).map((nft) => <button key={nft.id} type="button" className={styles.masonryCard} onClick={() => chooseNft(nft)}><span className={styles.masonryImageFrame}><MasonryImage src={nft.imageUrl} alt={nft.name} /></span><span className={styles.sourceCopy}><strong>{nft.name}</strong><small>{nft.description}</small><em>{nft.referenceUrls.length} 张参考图 · {nft.category}</em></span></button>)}</div>}
          {!busy && !nfts.length ? <div className={styles.loading}>暂时没有可用的 NFT 图片</div> : null}<Pager page={page} total={nfts.length} onChange={setPage} />
        </div> : null}

        {tab === "create" ? <div className={styles.createView}>
          <div className={styles.formFields}>
            <label>模板名称<input value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：紫色返场票根" /></label>
            <label>分类<input value={category} onChange={(event) => setCategory(event.target.value)} /></label>
            <label className={styles.full}>模板说明<textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="说明适合创作什么类型的 NFT 或粉丝周边" /></label>
            <label className={styles.full}>艺术提示词<textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="描述主体、构图、材质、光线、配色和周边形态…" /></label>
          </div>
          <div className={styles.referenceArea}>
            <div className={styles.referenceHeader}><span><FileImage /> 参考图</span></div>
            <div className={styles.references}>
              {referenceUrls.map((url, index) => <div key={`${url}-${index}`}><Image src={url} alt={`模板参考图 ${index + 1}`} fill sizes="88px" className="object-cover" /><button type="button" aria-label={`移除参考图 ${index + 1}`} onClick={() => setReferenceUrls((current) => current.filter((_, itemIndex) => itemIndex !== index))}><X /></button></div>)}
              {referenceUrls.length < 6 ? <label className={styles.referenceUpload} title="上传到 BeeImg" aria-label="上传参考图到 BeeImg">
                {busy === "upload" ? <LoaderCircle className="animate-spin" /> : <Plus />}
                <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" multiple disabled={Boolean(busy)} onChange={(event) => void uploadReferences(event.target.files)} />
              </label> : null}
              {!referenceUrls.length ? <span>点击 + 上传图片，或先从 Post、NFT 选择图片。</span> : null}
            </div>
          </div>
          <button type="button" className={styles.saveButton} disabled={Boolean(busy)} onClick={() => void createTemplate()}>{busy === "create" ? <LoaderCircle className="animate-spin" /> : <Plus />} 保存并使用模板</button>
        </div> : null}
      </section>
    </div>
  );
}
