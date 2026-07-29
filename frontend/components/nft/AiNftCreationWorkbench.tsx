"use client";

import { useRouter } from "next/navigation";
import Image from "next/image";
import { useMemo, useState } from "react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import { useOptionalAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import { apiErrorMessage } from "@/lib/api/errors";
import type { FanNftAiDraft, FanNftCreateResponse } from "@/lib/api/types";
import styles from "@/components/nft/AiNftCreationWorkbench.module.css";

type MaterialPack = {
  id: string;
  name: string;
  note: string;
  gradient: string;
  motif: string;
  palette: string[];
  elements: string[];
  forbidden: string[];
  prompt: string;
};

type VisualStyle = {
  id: string;
  name: string;
  prompt: string;
  description: string;
};

type NftImageVersion = {
  id: string;
  label: string;
  imageDataUrl: string;
  feedback: string | null;
};

const materialPacks: MaterialPack[] = [
  { id: "concert", name: "演唱会纪念系列", note: "舞台灯光、应援色与散场后的回声", gradient: "linear-gradient(135deg, #d946ef 0%, #7c3aed 48%, #172554 100%)", motif: "STAGE 01", palette: ["#D946EF", "#7C3AED", "#172554"], elements: ["舞台灯光", "应援色", "票根纹理"], forbidden: ["艺人肖像", "Logo", "可读文字"], prompt: "concert memory, stage lights, fan support color, premium music memorabilia" },
  { id: "encore", name: "Encore 返场系列", note: "安可、彩带与只属于现场的最后一首歌", gradient: "linear-gradient(135deg, #fb923c 0%, #f43f5e 48%, #581c87 100%)", motif: "ENCORE", palette: ["#FB923C", "#F43F5E", "#581C87"], elements: ["安可彩带", "逆光舞台", "最后一首歌"], forbidden: ["艺人肖像", "Logo", "可读文字"], prompt: "encore finale, falling confetti, dramatic backlight, emotional live-show finale" },
  { id: "letter", name: "粉丝来信系列", note: "手写感、票根、相册边角与私密记忆", gradient: "linear-gradient(135deg, #fbbf24 0%, #f472b6 48%, #be123c 100%)", motif: "LETTER", palette: ["#FBBF24", "#F472B6", "#BE123C"], elements: ["手写纸张", "票根边角", "相册纹理"], forbidden: ["艺人肖像", "Logo", "可读文字"], prompt: "intimate fan letter, ticket-stub collage, tactile paper texture, private memory" },
];

const refinementOptions = ["更有舞台感", "色彩更明亮", "构图更简洁", "减少人物元素", "更像纪念海报"];

const visualStyles: VisualStyle[] = [
  { id: "cinematic", name: "舞台电影感", description: "强光影与纪念海报构图", prompt: "cinematic concert light, premium music memorabilia, dramatic square collectible card" },
  { id: "collage", name: "票根拼贴", description: "手帐质感与碎片化回忆", prompt: "editorial ticket-stub collage, tactile paper texture, personal concert memory" },
  { id: "dream", name: "梦幻应援", description: "柔焦、荧光与情绪色彩", prompt: "dreamy fan-support artwork, soft glow, emotional color field, refined digital collectible" },
];

const copyrightDeclaration = "我确认拥有本次提交内容的发布权，并同意 Fanora 将其作为公开 NFT metadata 发布。";

function messageFor(error: unknown) {
  return apiErrorMessage(error, "这一步暂时没有完成，请检查网络后重试。");
}

export default function AiNftCreationWorkbench({ demoMode = false }: { demoMode?: boolean }) {
  const router = useRouter();
  const auth = useOptionalAuth();
  const user = auth?.user ?? null;
  const [materialId, setMaterialId] = useState("concert");
  const [styleId, setStyleId] = useState("cinematic");
  const [story, setStory] = useState("");
  const [draft, setDraft] = useState<FanNftAiDraft | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [supply, setSupply] = useState(10);
  const [price, setPrice] = useState(10);
  const [referenceImageDataUrl, setReferenceImageDataUrl] = useState<string | null>(null);
  const [versions, setVersions] = useState<NftImageVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [selectedRefinements, setSelectedRefinements] = useState<string[]>([]);
  const [refinementNote, setRefinementNote] = useState("");
  const [phase, setPhase] = useState<"collecting" | "briefing" | "brief_ready" | "generating" | "draft_ready" | "publishing">("collecting");
  const [notice, setNotice] = useState<string | null>(null);

  const material = useMemo(() => materialPacks.find((item) => item.id === materialId) ?? materialPacks[0], [materialId]);
  const style = useMemo(() => visualStyles.find((item) => item.id === styleId) ?? visualStyles[0], [styleId]);
  const canCreateBrief = story.trim().length >= 10 && phase !== "briefing" && phase !== "generating" && phase !== "publishing";
  const selectedVersion = versions.find((version) => version.id === selectedVersionId) ?? versions.at(-1);
  const previewImage = selectedVersion?.imageDataUrl ?? draft?.image_data_url ?? null;

  const selectReferenceImage = (file: File | undefined) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setNotice("请上传 PNG、JPG 或 WebP 图片。");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setNotice("参考图请控制在 5MB 以内。");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setReferenceImageDataUrl(typeof reader.result === "string" ? reader.result : null);
      setNotice("已添加自定义参考图，AI 会把它作为视觉参考。");
    };
    reader.readAsDataURL(file);
  };

  const createBrief = async () => {
    if (!canCreateBrief) {
      setNotice("请先写下至少 10 个字的粉丝故事，再生成草稿。");
      return;
    }
    if (!user && !demoMode) {
      router.push("/login");
      return;
    }
    setPhase("briefing");
    setNotice(null);
    try {
      const response = await api.post<FanNftAiDraft>(demoMode ? "/nft/creations/demo/ai-draft" : "/nft/creations/ai-draft", {
        theme: material.name,
        story: story.trim(),
        preferred_name: name.trim() || null,
        visual_style: style.prompt,
        reference_notes: `${material.note}。只使用官方素材包的情绪与配色边界；不得出现 Logo、水印或可读文字。`,
        reference_image_data_url: referenceImageDataUrl,
        generate_image: false,
      });
      const result = response.data;
      setDraft(result);
      setName(result.name);
      setDescription(result.description);
      setPhase("brief_ready");
      setNotice("NFT Brief 已生成。确认内容后，再使用它生成 NFT 图片。");
    } catch (error) {
      setPhase("collecting");
      setNotice(messageFor(error));
    }
  };

  const generateImage = async (feedback?: string) => {
    if (!draft) {
      setNotice("请先确认故事并生成 NFT Brief。");
      return;
    }
    setPhase("generating");
    setNotice(null);
    try {
      const iterationImage = feedback ? selectedVersion?.imageDataUrl ?? null : null;
      const response = await api.post<FanNftAiDraft>(demoMode ? "/nft/creations/demo/ai-draft" : "/nft/creations/ai-draft", {
        theme: material.name,
        story: story.trim(),
        preferred_name: name.trim() || draft.name,
        visual_style: style.prompt,
        reference_notes: `${material.note}。官方视觉元素：${material.elements.join("、")}。禁止：${material.forbidden.join("、")}。${feedback ? `本轮微调：保留上一版中的演唱会舞台、观众、主光源和整体构图；仅调整：${feedback}。` : "首轮生成：制作一张方形、可收藏的 NFT 视觉草稿。"}。不得出现 Logo、水印或可读文字。`,
        reference_image_data_url: iterationImage ? null : referenceImageDataUrl,
        iteration_image_data_url: iterationImage,
        generate_image: true,
      });
      const result = response.data;
      setDraft(result);
      setName(result.name);
      setDescription(result.description);
      setPhase("draft_ready");
      if (result.image_data_url) {
        setVersions((current) => {
          const next = { id: `v${current.length + 1}`, label: `v${current.length + 1}`, imageDataUrl: result.image_data_url!, feedback: feedback ?? null };
          setSelectedVersionId(next.id);
          return [...current, next];
        });
        setSelectedRefinements([]);
        setRefinementNote("");
      }
      setNotice(result.image_data_url ? "NFT 图片已生成。确认发行信息后即可发布。" : (result.image_error || "图片服务暂不可用；请稍后重试。"));
    } catch (error) {
      setPhase("brief_ready");
      setNotice(messageFor(error));
    }
  };

  const refineImage = async () => {
    const feedback = [...selectedRefinements, refinementNote.trim()].filter(Boolean).join("；");
    if (!feedback) {
      setNotice("选择一个调整方向，或写下想修改的内容。");
      return;
    }
    await generateImage(feedback);
  };

  const publish = async () => {
    if (!previewImage) {
      setNotice("需要先生成一张 NFT 图片，才能确认发布。");
      return;
    }
    if (demoMode) {
      setNotice("演示版已确认 NFT 预览：正式发布、扣除 FAN 与链上铸造会在连接钱包后执行。");
      return;
    }
    setPhase("publishing");
    setNotice(null);
    try {
      const response = await api.post<FanNftCreateResponse>("/nft/creations", {
        name: name.trim(),
        description: description.trim(),
        theme: material.name,
        price_fan_tokens: price,
        max_supply: supply,
        public_attributes: draft.suggested_attributes,
        copyright_declaration: copyrightDeclaration,
        image_data_url: previewImage,
        story_image_urls: [],
      });
      await auth?.refreshUser();
      router.replace(`/item/${response.data.listing.id}`);
    } catch (error) {
      setPhase("draft_ready");
      setNotice(messageFor(error));
    }
  };

  return (
    <main className={`${styles.stage} min-h-screen pb-16 pt-24 text-jacarta-700 transition-colors dark:text-white md:pt-28`}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <header className="mb-7 flex flex-col gap-4 border-b border-jacarta-100 pb-6 dark:border-white/10 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.24em] text-fuchsia-300">Fanora / co-create</p>
            <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">把这一刻，做成你持有的纪念</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-jacarta-500 dark:text-white/60">选择官方素材与视觉风格，讲述一段粉丝故事。AI 只负责创作草稿；发布与链上记录会在你的确认后执行。</p>
          </div>
          <div className="rounded-2xl border border-fuchsia-300/20 bg-fuchsia-300/10 px-4 py-3 text-sm">
            <span className="block text-xs text-jacarta-500 dark:text-white/50">可用贡献</span>
            <FanTokenAmount amount={user?.fan_token_balance ?? 0} showSymbol className="mt-1 text-lg font-semibold text-fuchsia-200" />
          </div>
        </header>

        {notice ? <div role="status" className="mb-6 rounded-xl border border-jacarta-100 bg-white px-4 py-3 text-sm text-jacarta-600 shadow-sm dark:border-white/10 dark:bg-white/[0.06] dark:text-white/80">{notice}</div> : null}

        <div className="grid items-stretch gap-5 lg:grid-cols-[0.9fr_1fr_1.1fr]">
          <section className="rounded-2xl border border-jacarta-100 p-5 shadow-sm dark:border-white/10 lg:flex lg:h-full lg:flex-col">
            <div className="mb-6 flex items-center justify-between">
              <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-jacarta-400 dark:text-white/45">01 / Story</p><h2 className="mt-1 text-lg font-semibold">和 Agent 说说这段故事</h2></div>
              <span className="rounded-full bg-fuchsia-300/15 px-3 py-1 text-xs text-fuchsia-200">创作对话</span>
            </div>
            <div className="space-y-4">
              <div className="max-w-[92%] rounded-2xl rounded-tl-sm bg-[#f0edff] p-4 text-sm leading-6 text-[#483c72] dark:bg-white/10 dark:text-white/80">想留住哪一个瞬间？可以是演唱会、一次应援，或一个只属于你自己的情绪。</div>
              <div className="ml-auto max-w-[92%] rounded-2xl rounded-tr-sm bg-fuchsia-100 p-4 text-sm leading-6 text-[#44247e] shadow-[0_8px_22px_rgba(105,67,210,0.12)] dark:bg-[#6943d2] dark:text-white dark:shadow-[0_8px_22px_rgba(105,67,210,0.25)]">在下方写下故事。确认生成后，我会将它整理为可编辑的 NFT Brief。</div>
            </div>
            <label className="mt-6 block text-sm font-medium" htmlFor="fan-story">你的故事</label>
            <textarea id="fan-story" value={story} onChange={(event) => { setStory(event.target.value); if (draft) { setDraft(null); setVersions([]); setSelectedVersionId(null); setPhase("collecting"); } }} placeholder="例如：散场时大家还在合唱，我第一次觉得自己真的属于这个共同体。" style={{ colorScheme: "light" }} className="mt-2 min-h-40 w-full resize-y rounded-xl border border-[#e1daf7] bg-[#fbfaff] p-3 text-sm leading-6 text-jacarta-700 caret-fuchsia-500 outline-none placeholder:text-jacarta-400 focus:border-fuchsia-300 focus:ring-2 focus:ring-fuchsia-300/20 dark:border-white/10 dark:bg-[#0a0a13] dark:text-white dark:caret-fuchsia-200 dark:placeholder:text-white/30" />
            <div className="mt-2 flex justify-between text-xs text-jacarta-400 dark:text-white/40"><span>Agent 会将你的描述整理成 NFT Brief。</span><span>{story.trim().length} / 10</span></div>
            <button type="button" onClick={() => void createBrief()} disabled={!canCreateBrief} className={`${styles.primaryAction} mt-4 w-full rounded-xl px-4 py-3 text-sm font-bold text-white`}>{phase === "briefing" ? "Agent 正在整理 NFT Brief…" : "确认故事，生成 NFT Brief"}</button>
            {draft ? <section className="mt-5 rounded-xl border border-fuchsia-200/70 bg-fuchsia-50 p-4 dark:border-fuchsia-300/20 dark:bg-[#252039]"><div className="flex items-center justify-between"><p className="text-xs font-bold uppercase tracking-[0.18em] text-fuchsia-600 dark:text-fuchsia-200">NFT Brief</p><span className="text-[11px] text-jacarta-500 dark:text-white/55">可继续编辑</span></div><p className="mt-3 text-sm font-semibold text-jacarta-700 dark:text-white">{name || draft.name}</p><p className="mt-1 text-sm leading-6 text-jacarta-500 dark:text-white/70">{description || draft.description}</p><div className="mt-3 flex flex-wrap gap-2">{draft.suggested_attributes.slice(0, 3).map((attribute) => <span key={`${attribute.trait_type}-${attribute.value}`} className="rounded-full bg-white px-2.5 py-1 text-[11px] text-jacarta-500 shadow-sm dark:bg-white/10 dark:text-white/70">{attribute.trait_type}: {attribute.value}</span>)}</div></section> : null}
          </section>

          <section className="rounded-2xl border border-jacarta-100 p-5 shadow-sm dark:border-white/10 lg:flex lg:h-full lg:flex-col">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-jacarta-400 dark:text-white/45">02 / Material direction</p>
            <h2 className="mt-1 text-lg font-semibold">给作品一条官方视觉边界</h2>
            <div className="mt-5 space-y-3">
              {materialPacks.map((item) => <button key={item.id} type="button" onClick={() => setMaterialId(item.id)} className={`group flex w-full items-center gap-3 rounded-xl border p-3 text-left transition ${materialId === item.id ? "border-fuchsia-300 bg-fuchsia-300/10" : "border-jacarta-100 hover:border-jacarta-300 dark:border-white/10 dark:hover:border-white/30"}`}>
                <span style={{ background: item.gradient }} className="flex h-12 w-12 shrink-0 items-end rounded-lg p-1 text-[8px] font-bold tracking-wider text-white/90 shadow-sm">{item.motif}</span>
                <span><span className="block text-sm font-semibold">{item.name}</span><span className="mt-0.5 block text-xs leading-5 text-jacarta-500 dark:text-white/50">{item.note}</span></span>
              </button>)}
            </div>
            <div className="mt-4 rounded-xl border border-jacarta-100 bg-white/65 p-3 dark:border-white/10 dark:bg-white/[0.04]">
              <div className="flex items-center justify-between"><p className="text-xs font-bold uppercase tracking-[0.14em] text-jacarta-500 dark:text-white/60">素材包规则</p><div className="flex gap-1.5">{material.palette.map((color) => <span key={color} title={color} style={{ backgroundColor: color }} className="h-4 w-4 rounded-full border border-white/60 shadow-sm" />)}</div></div>
              <p className="mt-3 text-xs font-semibold text-jacarta-600 dark:text-white/80">会使用：{material.elements.join(" · ")}</p>
              <p className="mt-1 text-xs text-jacarta-500 dark:text-white/55">不会生成：{material.forbidden.join(" · ")}</p>
            </div>
            <h3 className="mt-6 text-sm font-semibold">视觉风格</h3>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {visualStyles.map((item) => <button key={item.id} type="button" onClick={() => setStyleId(item.id)} className={`min-h-24 rounded-xl border p-3 text-left transition ${styleId === item.id ? "border-fuchsia-300 bg-fuchsia-300/10" : "border-jacarta-100 hover:border-jacarta-300 dark:border-white/10 dark:hover:border-white/30"}`}><span className="block text-xs font-semibold">{item.name}</span><span className="mt-2 block text-[11px] leading-4 text-jacarta-500 dark:text-white/50">{item.description}</span></button>)}
            </div>
            <div className="mt-6 rounded-xl border border-[#e1daf7] bg-[#f0edff] p-3 text-xs leading-5 text-[#514573] dark:border-white/10 dark:bg-[#292835] dark:text-white/80">
              <div className="flex items-center justify-between gap-3"><span>自定义参考图（可选）</span>{referenceImageDataUrl ? <button type="button" onClick={() => setReferenceImageDataUrl(null)} className="text-fuchsia-600 underline underline-offset-2 dark:text-fuchsia-200">移除</button> : null}</div>
              <p className="mt-1">上传海报、现场照片或情绪参考图；AI 会结合官方素材包生成，不会把原图直接发布。</p>
              <label className="mt-3 flex cursor-pointer items-center justify-center rounded-lg border border-dashed border-[#8b7cb5] bg-white/70 px-3 py-2 text-sm font-semibold text-[#5535a2] transition hover:bg-white dark:border-fuchsia-200/40 dark:bg-white/10 dark:text-fuchsia-100">
                <input type="file" accept="image/png,image/jpeg,image/webp" className="sr-only" onChange={(event) => selectReferenceImage(event.target.files?.[0])} />
                {referenceImageDataUrl ? "更换参考图" : "上传参考图"}
              </label>
              {referenceImageDataUrl ? <div className="relative mt-3 aspect-[16/7] overflow-hidden rounded-lg border border-white/40"><Image src={referenceImageDataUrl} alt="自定义参考图预览" fill unoptimized className="object-cover" /></div> : null}
            </div>
            {phase === "brief_ready" || phase === "generating" ? <button type="button" onClick={() => void generateImage()} disabled={phase === "generating"} className={`${styles.primaryAction} mt-4 w-full rounded-xl px-4 py-3 text-sm font-bold text-white`}>{phase === "generating" ? "AI 正在生成 NFT 图片…" : "使用 NFT Brief 生成图片 · 10 FAN"}</button> : <button type="button" disabled className={`${styles.primaryAction} mt-4 w-full rounded-xl px-4 py-3 text-sm font-bold text-white`}>使用 NFT Brief 生成图片 · 10 FAN</button>}
            {versions.length > 0 ? <section className="mt-5 border-t border-jacarta-100 pt-5 dark:border-white/10">
              <div className="flex items-center justify-between"><div><p className="text-sm font-semibold">不满意？让 Agent 微调</p><p className="mt-1 text-xs text-jacarta-500 dark:text-white/55">保留故事、素材包和风格，只调整你指定的部分。</p></div><span className="text-xs font-semibold text-fuchsia-600 dark:text-fuchsia-200">下一版 · 10 FAN</span></div>
              <div className="mt-3 flex flex-wrap gap-2">{refinementOptions.map((option) => <button key={option} type="button" onClick={() => setSelectedRefinements((current) => current.includes(option) ? current.filter((item) => item !== option) : [...current, option])} className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${selectedRefinements.includes(option) ? "border-fuchsia-400 bg-fuchsia-100 text-fuchsia-700 dark:border-fuchsia-300 dark:bg-fuchsia-300/15 dark:text-fuchsia-100" : "border-jacarta-100 text-jacarta-500 hover:border-fuchsia-300 dark:border-white/15 dark:text-white/65"}`}>{option}</button>)}</div>
              <textarea value={refinementNote} onChange={(event) => setRefinementNote(event.target.value)} placeholder="例如：保留紫色灯光，但让票根和散场的情绪更明显。" className="mt-3 min-h-20 w-full resize-y rounded-lg border border-[#e1daf7] bg-[#fbfaff] p-3 text-sm leading-5 text-jacarta-700 outline-none placeholder:text-jacarta-400 focus:border-fuchsia-300 dark:border-white/10 dark:bg-[#0a0a13] dark:text-white dark:placeholder:text-white/35" />
              <button type="button" onClick={() => void refineImage()} disabled={phase === "generating"} className={`${styles.primaryAction} mt-3 w-full rounded-xl px-4 py-3 text-sm font-bold text-white`}>{phase === "generating" ? "Agent 正在生成新版本…" : "根据反馈生成下一版 · 10 FAN"}</button>
            </section> : null}
          </section>

          <aside className="rounded-2xl border border-[#ddd9ef] p-5 shadow-[0_18px_50px_rgba(76,55,148,0.12)] dark:border-white/10 dark:shadow-none lg:flex lg:h-full lg:flex-col">
            <div className="flex items-start justify-between"><div><p className="text-xs font-bold uppercase tracking-[0.18em] text-fuchsia-500 dark:text-fuchsia-200/70">03 / NFT preview</p><h2 className="mt-1 text-lg font-semibold">确认你将要发布的内容</h2></div><span className="rounded-full border border-jacarta-100 px-2.5 py-1 text-[11px] text-jacarta-500 dark:border-white/10 dark:text-white/70">{phase === "briefing" ? "正在整理 Brief" : phase === "brief_ready" ? "Brief 已就绪" : phase === "draft_ready" ? "图片已就绪" : phase === "generating" ? "正在生图" : phase === "publishing" ? "正在发布" : "等待创作"}</span></div>
            <div style={{ background: material.gradient }} className="relative mt-5 aspect-square overflow-hidden rounded-2xl border border-white/10">
              {previewImage ? <Image src={previewImage} alt={name || "AI NFT 草稿"} fill unoptimized className="object-cover" /> : <><div aria-hidden="true" className="absolute inset-0 bg-[#14121e]/70" /><div className="relative z-10 flex h-full flex-col justify-between p-5"><span className="w-fit rounded-full bg-black/45 px-3 py-1.5 text-xs font-bold tracking-[0.2em] text-white shadow-sm">FANORA EDITION</span><span className="max-w-48 font-display text-3xl font-semibold leading-tight text-white drop-shadow-sm">你的故事，会在这里显影。</span><span className="text-sm text-white/90">{style.name}</span></div></>}
            </div>
            {versions.length > 0 ? <div className="mt-4"><div className="mb-2 flex items-center justify-between"><p className="text-xs font-bold uppercase tracking-[0.16em] text-jacarta-500 dark:text-white/60">选择发布版本</p><span className="text-xs text-jacarta-400 dark:text-white/45">{versions.length} 个版本</span></div><div className="flex gap-2 overflow-x-auto pb-1">{versions.map((version) => <button key={version.id} type="button" onClick={() => setSelectedVersionId(version.id)} className={`shrink-0 rounded-lg border px-3 py-2 text-left text-xs transition ${selectedVersion?.id === version.id ? "border-fuchsia-400 bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-300/15 dark:text-fuchsia-100" : "border-jacarta-100 text-jacarta-500 dark:border-white/15 dark:text-white/65"}`}><span className="block font-bold">{version.label} {selectedVersion?.id === version.id ? "· 用于发布" : ""}</span><span className="mt-1 block max-w-28 truncate text-[11px] opacity-75">{version.feedback || "首轮草稿"}</span></button>)}</div></div> : null}
            <div className="mt-5 space-y-3">
              <label className="block text-xs font-semibold text-jacarta-500 dark:text-white/70" htmlFor="nft-name">NFT 名称<input id="nft-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="生成后可修改" className="mt-1.5 w-full rounded-lg border border-[#e1daf7] bg-[#fbfaff] px-3 py-2.5 text-sm text-jacarta-700 outline-none placeholder:text-jacarta-400 focus:border-fuchsia-300 dark:border-white/10 dark:bg-[#0a0a13] dark:text-white dark:placeholder:text-white/35" /></label>
              <label className="block text-xs font-semibold text-jacarta-500 dark:text-white/70" htmlFor="nft-description">作品描述<textarea id="nft-description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="生成后可修改" className="mt-1.5 min-h-20 w-full resize-y rounded-lg border border-[#e1daf7] bg-[#fbfaff] px-3 py-2.5 text-sm leading-5 text-jacarta-700 outline-none placeholder:text-jacarta-400 focus:border-fuchsia-300 dark:border-white/10 dark:bg-[#0a0a13] dark:text-white dark:placeholder:text-white/35" /></label>
              <div className="grid grid-cols-2 gap-3"><label className="text-xs font-semibold text-jacarta-500 dark:text-white/70">发行量<input type="number" min="1" max="1000" value={supply} onChange={(event) => setSupply(Number(event.target.value))} className="mt-1.5 w-full rounded-lg border border-[#e1daf7] bg-[#fbfaff] px-3 py-2.5 text-sm text-jacarta-700 outline-none focus:border-fuchsia-300 dark:border-white/10 dark:bg-[#0a0a13] dark:text-white" /></label><label className="text-xs font-semibold text-jacarta-500 dark:text-white/70">单价 / FAN<input type="number" min="1" value={price} onChange={(event) => setPrice(Number(event.target.value))} className="mt-1.5 w-full rounded-lg border border-[#e1daf7] bg-[#fbfaff] px-3 py-2.5 text-sm text-jacarta-700 outline-none focus:border-fuchsia-300 dark:border-white/10 dark:bg-[#0a0a13] dark:text-white" /></label></div>
            </div>
            {draft?.suggested_attributes.length ? <div className="mt-4 flex flex-wrap gap-2">{draft.suggested_attributes.map((attribute) => <span key={`${attribute.trait_type}-${attribute.value}`} className="rounded-full border border-jacarta-100 px-2.5 py-1 text-[11px] text-jacarta-500 dark:border-white/10 dark:text-white/70">{attribute.trait_type}: {attribute.value}</span>)}</div> : null}
            <div className="mt-5 border-t border-jacarta-100 pt-4 dark:border-white/10"><div className="flex items-center justify-between text-sm"><span className="text-jacarta-500 dark:text-white/70">本次生成</span><span className="font-semibold text-fuchsia-600 dark:text-fuchsia-200">10 FAN</span></div><p className="mt-2 text-xs leading-5 text-jacarta-500 dark:text-white/65">首次体验免费；后续生成、退款与每日次数限制将在结算服务接入后生效。</p></div>
            {phase === "draft_ready" ? <button type="button" onClick={() => void publish()} disabled={!previewImage || !name.trim() || !description.trim()} className={`${styles.primaryAction} mt-5 w-full rounded-xl px-4 py-3 text-sm font-bold text-white`}>确认并发布限量 NFT</button> : <button type="button" disabled className={`${styles.primaryAction} mt-5 w-full rounded-xl px-4 py-3 text-sm font-bold text-white`}>图片生成后，即可确认并发布</button>}
          </aside>
        </div>
      </div>
    </main>
  );
}
