"use client";

import NiceModal from "@ebay/nice-modal-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import MarkdownEditor from "@/components/community/MarkdownEditor";
import PostDetail from "@/components/community/PostDetail";
import GlobalInfoModal from "@/components/modals/GlobalInfoModal";
import GlobalProcessModal, { hideGlobalProcessModal } from "@/components/modals/GlobalProcessModal";
import UserIdentityLink from "@/components/profile/UserIdentityLink";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import { apiErrorMessage } from "@/lib/api/errors";
import type { CommunityPostDetail, CommunityPostSummary, FanNftListing, FanTask, OfficialCommunity, PostEngagement } from "@/lib/api/types";

const categories = [
  { id: "all", label: "推荐" },
  { id: "creation", label: "共创" },
  { id: "story", label: "故事" },
  { id: "music", label: "音乐" },
  { id: "discussion", label: "讨论" },
  { id: "bookmarked", label: "我的收藏" },
];
const labels: Record<string, string> = { creation: "共创", story: "故事", music: "音乐", discussion: "讨论" };
const POST_PAGE_SIZE = 25;
const YOUTUBE_URL_PATTERN = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?[^ \n)]*v=|shorts\/|embed\/)|youtu\.be\/)[A-Za-z0-9_-]{6,}[^ \n)]*/i;

function hasYoutubeVideo(value: string) {
  return YOUTUBE_URL_PATTERN.test(value);
}

function buildPostBody(body: string, videoUrl: string) {
  const cleanBody = body.trim();
  const cleanVideoUrl = videoUrl.trim();
  if (!cleanVideoUrl) return cleanBody;
  return [`视频：${cleanVideoUrl}`, cleanBody].filter(Boolean).join("\n\n");
}

export default function CreationWall() {
  const { user, refreshUser } = useAuth();
  const [posts, setPosts] = useState<CommunityPostSummary[]>([]);
  const [community, setCommunity] = useState<OfficialCommunity | null>(null);
  const [category, setCategory] = useState("all");
  const [composer, setComposer] = useState(false);
  const [columnCount, setColumnCount] = useState(1);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [draft, setDraft] = useState({ title: "", body: "", category: "creation", image_urls: [] as string[], video_url: "", linked_nft_creation_id: "" });
  const [tasks, setTasks] = useState<FanTask[]>([]);
  const [myNftItems, setMyNftItems] = useState<FanNftListing[]>([]);
  const tagInjectedForOpenComposer = useRef(false);
  const nextOffset = useRef(0);
  const loadingPosts = useRef(false);
  const loadMoreSentinel = useRef<HTMLDivElement | null>(null);
  const [hasMorePosts, setHasMorePosts] = useState(true);
  const [loadingMorePosts, setLoadingMorePosts] = useState(false);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [drawerClosing, setDrawerClosing] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadContext = useCallback(async () => {
    const [communityResponse, taskResponse] = await Promise.all([
      api.get<OfficialCommunity>("/community"),
      api.get<FanTask[]>("/tasks"),
    ]);
    setCommunity(communityResponse.data);
    setTasks(taskResponse.data);
  }, []);

  const loadPostPage = useCallback(async (reset = false) => {
    if (loadingPosts.current) return;
    loadingPosts.current = true;
    setLoadingMorePosts(true);
    const offset = reset ? 0 : nextOffset.current;
    try {
      const response = await api.get<CommunityPostSummary[]>(
        `/community/posts?limit=${POST_PAGE_SIZE}&offset=${offset}`,
      );
      const page = response.data;
      setPosts((current) => {
        if (reset) return page;
        const knownIds = new Set(current.map((post) => post.id));
        return [...current, ...page.filter((post) => !knownIds.has(post.id))];
      });
      nextOffset.current = offset + page.length;
      setHasMorePosts(page.length === POST_PAGE_SIZE);
    } finally {
      loadingPosts.current = false;
      setLoadingMorePosts(false);
    }
  }, []);

  const reload = useCallback(async () => {
    await Promise.all([loadContext(), loadPostPage(true)]);
  }, [loadContext, loadPostPage]);

  useEffect(() => { void reload().catch((error) => setNotice(apiErrorMessage(error))); }, [reload, user]);
  useEffect(() => {
    const handlePopState = () => {
      if (!window.location.pathname.startsWith("/community/posts/")) {
        setSelectedPostId(null);
        setDrawerClosing(false);
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);
  useEffect(() => {
    if (!selectedPostId) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previousOverflow; };
  }, [selectedPostId]);
  useEffect(() => () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
  }, []);
  useEffect(() => {
    const updateColumns = () => {
      const width = window.innerWidth;
      setColumnCount(width >= 1202 ? 4 : width >= 1025 ? 3 : width >= 575 ? 2 : 1);
    };
    updateColumns();
    window.addEventListener("resize", updateColumns);
    return () => window.removeEventListener("resize", updateColumns);
  }, []);
  const joined = community?.joined || Boolean(user?.communities.some((item) => item.slug === "fanora-official"));
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requestedCategory = params.get("category");
    if (requestedCategory && categories.some((item) => item.id === requestedCategory)) setCategory(requestedCategory);
    if (params.get("composer") === "1" && user?.is_official_member && joined) setComposer(true);
  }, [joined, user]);
  useEffect(() => {
    if (!user?.is_official_member || !joined) {
      setMyNftItems([]);
      return;
    }
    void api.get<FanNftListing[]>("/nft/me/creations")
      .then((response) => setMyNftItems(response.data))
      .catch(() => setMyNftItems([]));
  }, [joined, user?.is_official_member]);
  const visiblePosts = useMemo(() => category === "all" ? posts : category === "bookmarked" ? posts.filter((post) => post.bookmarked) : posts.filter((post) => post.category === category), [category, posts]);
  useEffect(() => {
    const sentinel = loadMoreSentinel.current;
    if (!sentinel || !hasMorePosts) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) void loadPostPage().catch((error) => setNotice(apiErrorMessage(error)));
      },
      { rootMargin: "600px 0px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMorePosts, loadPostPage, visiblePosts.length]);
  const masonryColumns = useMemo(() => {
    const columns: Array<Array<{ post: CommunityPostSummary; index: number }>> = Array.from({ length: columnCount }, () => []);
    const heights = Array.from({ length: columnCount }, () => 0);
    visiblePosts.forEach((post, index) => {
      const column = heights.indexOf(Math.min(...heights));
      columns[column].push({ post, index });
      heights[column] += post.cover_url ? (index % 3 === 0 ? 520 : index % 3 === 1 ? 440 : 390) : 320;
    });
    return columns;
  }, [columnCount, visiblePosts]);

  const requireInteraction = () => {
    if (!user) { setNotice("请先登录，再点赞或收藏创作。 "); return false; }
    if (!user.is_official_member) { setNotice("正式入会后可以点赞、收藏和评论。 "); return false; }
    if (!joined) { setNotice("请先加入 Fanora 链上社区。 "); return false; }
    return true;
  };

  const updateEngagement = (engagement: PostEngagement) => setPosts((current) => current.map((post) => post.id === engagement.post_id ? { ...post, ...engagement } : post));
  const toggle = async (post: CommunityPostSummary, action: "like" | "bookmark") => {
    if (!requireInteraction()) return;
    setBusy(`${action}:${post.id}`);
    try {
      const response = await api.post<PostEngagement>(`/community/posts/${post.id}/${action}`);
      updateEngagement(response.data);
      if (action === "like") await refreshUser();
    } catch (error) { setNotice(apiErrorMessage(error)); } finally { setBusy(null); }
  };

  const openPost = (postId: string, section?: "comments") => {
    const suffix = section ? `#${section}` : "";
    window.history.pushState({ communityDrawer: true, postId }, "", `/community/posts/${postId}${suffix}`);
    setDrawerClosing(false);
    setSelectedPostId(postId);
  };

  const closePost = useCallback(() => {
    if (!selectedPostId || drawerClosing) return;
    setDrawerClosing(true);
    closeTimer.current = setTimeout(() => {
      if (window.location.pathname.startsWith("/community/posts/")) window.history.back();
      else {
        setSelectedPostId(null);
        setDrawerClosing(false);
      }
    }, 220);
  }, [drawerClosing, selectedPostId]);

  useEffect(() => {
    if (!selectedPostId) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closePost();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [closePost, selectedPostId]);

  const requiredTags = useMemo(
    () => tasks.filter((task) => task.task_type === "content_publish" && task.participation_status === "claimed")
      .map((task) => task.required_tag)
      .filter((tag): tag is string => Boolean(tag)),
    [tasks],
  );
  const requiredTagKey = requiredTags.join("\n");
  useEffect(() => {
    if (!composer) {
      tagInjectedForOpenComposer.current = false;
      return;
    }
    if (tagInjectedForOpenComposer.current || !requiredTagKey) return;
    setDraft((current) => {
      const missingTags = requiredTags.filter((tag) => !current.body.includes(tag));
      return missingTags.length ? { ...current, body: [...missingTags, current.body].filter(Boolean).join("\n\n") } : current;
    });
    tagInjectedForOpenComposer.current = true;
  }, [composer, requiredTagKey, requiredTags]);

  const publish = async (event: FormEvent) => {
    event.preventDefault();
    const body = buildPostBody(draft.body, draft.video_url);
    if (draft.video_url.trim() && !hasYoutubeVideo(draft.video_url)) {
      setNotice("请输入有效的 YouTube 视频链接。");
      return;
    }
    setBusy("publish");
    setNotice(null);
    void NiceModal.show(GlobalProcessModal, {
      title: "AI 正在审核创作",
      message: "正在确认内容与社区相关，并排除广告、垃圾信息和无意义内容。简短、普通的真实粉丝表达不会因此被拒绝。",
      eyebrow: "COMMUNITY REVIEW",
      gifUrl: "/img/process/cyancat.gif",
    });
    try {
      const response = await api.post<CommunityPostDetail>("/community/posts", {
        ...draft,
        body,
        cover_url: draft.image_urls[0] || null,
        linked_nft_creation_id: draft.linked_nft_creation_id || null,
      });
      setDraft({ title: "", body: "", category: "creation", image_urls: [], video_url: "", linked_nft_creation_id: "" });
      setComposer(false);
      await Promise.all([reload(), refreshUser()]);
      await hideGlobalProcessModal();
      setNotice(`《${response.data.title}》已发布。`);
    } catch (error) {
      const detail = apiErrorMessage(error, "这次发布没有完成，请检查内容后重试。");
      await hideGlobalProcessModal();
      void NiceModal.show(GlobalInfoModal, {
        title: "这次发布没有完成",
        message: detail,
        tone: "error",
        eyebrow: "PUBLISH ERROR",
        confirmLabel: "返回修改",
      });
    } finally {
      setBusy(null);
    }
  };

  return (
    <main className="web3-page-shell min-h-screen pb-24 pt-28 md:pt-32">
      <div className="container">
        <nav className="community-reveal sticky top-20 z-10 flex items-center gap-4 py-2 [animation-delay:100ms]">
          <div className="flex min-w-0 flex-1 items-center gap-6 overflow-x-auto">
            {categories.map((item) => <button key={item.id} onClick={() => setCategory(item.id)} className={`shrink-0 border-b-2 px-0.5 py-3 text-sm font-semibold transition-colors ${category === item.id ? "border-accent text-white" : "border-transparent text-white/45 hover:text-white"}`}>{item.label}</button>)}
          </div>
          {user?.is_official_member && joined ? <button onClick={() => setComposer((value) => !value)} className="web3-action-button shrink-0 rounded-full px-5 py-2.5 text-sm font-semibold text-white">{composer ? "收起" : "发布创作"}</button> : <Link href={user ? "/membership/join" : "/login"} className="web3-action-button shrink-0 rounded-full px-5 py-2.5 text-center text-sm font-semibold text-white">{user ? "入会后发布" : "登录后发布"}</Link>}
        </nav>

        {notice && <div className="community-reveal mt-5 rounded-2xl border border-accent/20 bg-accent/10 px-5 py-4 text-sm font-semibold text-accent-lighter">{notice}</div>}

        {composer && <form onSubmit={publish} className="community-reveal mt-6 rounded-[2rem] border border-accent/20 bg-[#111538] p-6 text-white md:p-8">
          <div>
            <div className="grid gap-4 md:grid-cols-[1fr_150px]"><input required minLength={4} maxLength={120} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="创作标题" className="rounded-xl border-white/10 bg-white/[.06] text-white placeholder:text-white/30" /><select value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value })} className="rounded-xl border-white/10 bg-[#181d49] text-white"><option value="creation">共创</option><option value="story">故事</option><option value="music">音乐</option><option value="discussion">讨论</option></select></div>
            <MarkdownEditor value={draft.body} onChange={(body) => setDraft((current) => ({ ...current, body }))} imageUrls={draft.image_urls} onImageUrlsChange={(image_urls) => setDraft((current) => ({ ...current, image_urls }))} onImageError={setNotice} />
            <input
              type="url"
              value={draft.video_url}
              onChange={(event) => setDraft((current) => ({ ...current, video_url: event.target.value }))}
              placeholder="YouTube 视频链接，可选；上传图片会作为封面"
              className="mt-4 w-full rounded-xl border border-white/10 bg-white/[.06] px-4 py-3 text-sm text-white placeholder:text-white/30"
            />
            {myNftItems.length ? (
              <div className="mt-5 rounded-2xl border border-white/10 bg-white/[.035] p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-white">关联 NFT 产品</p>
                  {draft.linked_nft_creation_id ? <button type="button" onClick={() => setDraft((current) => ({ ...current, linked_nft_creation_id: "" }))} className="text-xs font-semibold text-white/45 hover:text-white">取消关联</button> : null}
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {myNftItems.slice(0, 6).map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setDraft((current) => ({ ...current, linked_nft_creation_id: current.linked_nft_creation_id === item.id ? "" : item.id }))}
                      className={`flex min-w-0 items-center gap-3 rounded-lg border p-3 text-left transition-colors ${draft.linked_nft_creation_id === item.id ? "border-accent bg-accent/10" : "border-white/10 bg-white/[.04] hover:border-white/25"}`}
                    >
                      <span className="block h-14 w-14 shrink-0 overflow-hidden rounded-md bg-black/30">
                        {item.image_url ? <img src={item.image_url} alt="" className="h-full w-full object-cover" /> : null}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-semibold text-white">{item.name}</span>
                        <span className="mt-1 block text-xs text-accent-lighter">{item.price_fan_tokens} FAN</span>
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
            <button disabled={busy === "publish"} className="web3-action-button mt-4 rounded-full px-7 py-3 font-semibold text-white disabled:opacity-50">{busy === "publish" ? "发布中…" : "发布创作"}</button>
          </div>
        </form>}

        <section className="mt-6 grid items-start gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {masonryColumns.map((column, columnIndex) => <div key={columnIndex} className="space-y-5">{column.map(({ post, index }) => (
            <article key={post.id} className="web3-interactive-card community-reveal mb-5 inline-block w-full break-inside-avoid overflow-hidden rounded-[1.5rem] border border-white/10 bg-[#111538] text-white" style={{ animationDelay: `${Math.min(index, 12) * 55}ms` }}>
              <Link href={`/community/posts/${post.id}`} onClick={(event) => { event.preventDefault(); openPost(post.id); }} className="group block overflow-hidden">
                {post.cover_url ? <div className="relative overflow-hidden bg-[#090c24]"><img src={post.cover_url} alt="" className="block h-auto w-full transition-opacity duration-300 group-hover:opacity-95" />{hasYoutubeVideo(post.body_preview) ? <span className="absolute left-3 top-3 rounded-full bg-black/70 px-3 py-1 text-[11px] font-semibold text-white backdrop-blur">▶ YouTube</span> : null}</div> : <div className={`flex ${index % 2 ? "min-h-72" : "min-h-52"} items-center bg-gradient-to-br from-accent/25 via-[#45BFEF]/10 to-[#111538] p-7`}><p className="font-display text-2xl font-semibold leading-relaxed text-white/90">{post.title}</p></div>}
              </Link>
              <div className="p-4">
                <span className="rounded-full bg-accent/15 px-2.5 py-1 text-[11px] font-semibold text-accent-lighter">{labels[post.category] || post.category}</span>
                <Link href={`/community/posts/${post.id}`} onClick={(event) => { event.preventDefault(); openPost(post.id); }}><h2 className="mt-3 font-display text-base font-semibold leading-6 transition-colors hover:text-accent-light">{post.title}</h2></Link>
                <p className="mt-2 line-clamp-2 text-xs leading-5 text-white/45">{post.body_preview}</p>
                <div className="mt-4 flex items-center gap-2">
                  <UserIdentityLink author={post.author} avatarClassName="h-7 w-7 rounded-full" nameClassName="text-xs text-white/55" compact />
                </div>
                <div className="mt-4 flex items-center gap-1 border-t border-white/5 pt-3">
                  <button onClick={() => void toggle(post, "like")} disabled={busy === `like:${post.id}`} aria-label="点赞创作" className={`creation-action ${post.liked ? "is-active" : ""}`}><span>{post.liked ? "♥" : "♡"}</span>{post.like_count}</button>
                  <Link href={`/community/posts/${post.id}#comments`} onClick={(event) => { event.preventDefault(); openPost(post.id, "comments"); }} className="creation-action"><span>◯</span>{post.reply_count}</Link>
                  <button onClick={() => void toggle(post, "bookmark")} disabled={busy === `bookmark:${post.id}`} aria-label="收藏创作" className={`creation-action ml-auto ${post.bookmarked ? "is-active" : ""}`}><span>{post.bookmarked ? "★" : "☆"}</span>{post.bookmark_count}</button>
                </div>
              </div>
            </article>
          ))}</div>)}
        </section>
        {!visiblePosts.length && !loadingMorePosts && !hasMorePosts && (
          <p className="mt-12 text-center text-sm text-white/40">这个分类暂时没有创作。</p>
        )}
        <div ref={loadMoreSentinel} aria-hidden="true" className="flex min-h-24 items-center justify-center">
          {loadingMorePosts ? (
            <span className="h-8 w-8 animate-spin rounded-full border-2 border-accent/20 border-t-accent" />
          ) : hasMorePosts ? (
            <span className="text-xs text-white/30">继续向下浏览</span>
          ) : posts.length > 0 ? (
            <span className="text-xs text-white/30">已经浏览完全部创作</span>
          ) : null}
        </div>
      </div>
      {selectedPostId ? (
        <div
          role="presentation"
          onMouseDown={(event) => { if (event.target === event.currentTarget) closePost(); }}
          className={`community-drawer-backdrop fixed inset-0 z-[1000] flex items-end justify-center bg-[#050619]/75 px-0 pt-5 backdrop-blur-md md:px-8 md:pt-10 ${drawerClosing ? "is-closing" : ""}`}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-label="创作详情"
            className="community-letter-drawer relative flex max-h-[calc(100dvh-1.25rem)] w-full max-w-6xl flex-col overflow-hidden rounded-t-lg bg-[#111538] shadow-[0_45px_140px_rgba(0,0,0,.72),0_0_70px_rgba(131,88,255,.16)] md:max-h-[calc(100dvh-2.5rem)]"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              onClick={closePost}
              aria-label="关闭创作详情"
              className="absolute right-4 top-4 z-20 flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-[#090b23]/85 text-2xl leading-none text-white/75 shadow-lg transition-colors hover:border-accent/50 hover:text-white"
            >
              <span aria-hidden="true" className="-translate-y-px">×</span>
            </button>
            <PostDetail postId={selectedPostId} variant="drawer" onClose={closePost} />
          </section>
        </div>
      ) : null}
    </main>
  );
}
