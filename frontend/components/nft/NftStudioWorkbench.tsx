"use client";

import NiceModal from "@ebay/nice-modal-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  AlertTriangle,
  Bot,
  Check,
  ChevronRight,
  FileImage,
  ImagePlus,
  Layers3,
  LoaderCircle,
  MessageSquareText,
  Palette,
  Plus,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import MarkdownEditor from "@/components/community/MarkdownEditor";
import GlobalInfoModal from "@/components/modals/GlobalInfoModal";
import GlobalProcessModal, { hideGlobalProcessModal } from "@/components/modals/GlobalProcessModal";
import NftVisualTemplateModal from "@/components/nft/NftVisualTemplateModal";
import PublishConfirmModal from "@/components/nft/PublishConfirmModal";
import { useAuth } from "@/components/providers/AuthProvider";
import { api, uploadImage } from "@/lib/api/client";
import { apiErrorMessage } from "@/lib/api/errors";
import { buildForgeAnalyzePayload, forgeStrategyTooltipText } from "@/lib/nft/forge-request";
import type {
  FanNftAiDraft,
  FanNftCreateResponse,
  NftForgeSession,
  NftFragmentBalance,
  NftAgentChatResponse,
  NftAgentToolEvent,
  NftUploadedImageAnalysis,
  NftVisualStyle,
  NftVisualTemplate,
} from "@/lib/api/types";
import styles from "@/components/nft/NftStudioWorkbench.module.css";

type ChatMessage = { id: string; role: "agent" | "user"; content: string };
type ImageVersion = {
  id: string;
  image: string;
  label: string;
  turn: number;
  name: string;
  description: string;
  imagePrompt: string;
  attributes: Array<{ trait_type: string; value: string }>;
  forge: NftForgeSession | null;
};
const forgeDimensions = [
  ["originality", "原创性"],
  ["visual_quality", "视觉质量"],
  ["fan_emotion", "粉丝情绪"],
  ["scarcity", "收藏稀缺度"],
  ["community_potential", "社群潜力"],
] as const;

const copyrightDeclaration = "我确认拥有本次提交内容的发布权，并同意 Fanora 将其作为公开 NFT metadata 发布。";
const defaultTemplateId = "concert";
const welcomeMessage = `想从哪段值得留下的记忆开始？

你可以先告诉我：
- 真实经历、喜欢的性格，或歌曲带给你的想象
- 最想留下的画面或情绪
- 想做成票根、徽章、收藏卡，还是其他周边

需要调用工具可以直接说：
- “帮我推荐一个模板”
- “把当前版本另存为模板”

故事和画面方向成熟后，我会自动生成作品；你也可以直接说“生成图片”。`;

function getMessage(error: unknown) {
  return apiErrorMessage(error, "创作节点暂时没有响应，请稍后重试。");
}

function waitForUi(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export default function NftStudioWorkbench() {
  const router = useRouter();
  const { user, status, refreshUser } = useAuth();
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const defaultTemplateAppliedRef = useRef(false);
  const versionSelectionRequestRef = useRef(0);
  const strategyTooltipTimerRef = useRef<number | null>(null);
  const lastStrategyRequestRef = useRef<string | null>(null);
  const [templates, setTemplates] = useState<NftVisualTemplate[]>([]);
  const [visualStyles, setVisualStyles] = useState<NftVisualStyle[]>([]);
  const [templateId, setTemplateId] = useState("");
  const [styleId, setStyleId] = useState("");
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [templateLibraryLoading, setTemplateLibraryLoading] = useState(false);
  const [templateLibraryLoaded, setTemplateLibraryLoaded] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: "welcome", role: "agent", content: welcomeMessage },
  ]);
  const [input, setInput] = useState("");
  const [summary, setSummary] = useState("");
  const [missingFields, setMissingFields] = useState<string[]>(["事件或对象", "核心画面", "情绪落点"]);
  const [toolEvents, setToolEvents] = useState<NftAgentToolEvent[]>([]);
  const [imageGenerationRecommended, setImageGenerationRecommended] = useState(false);
  const [draft, setDraft] = useState<FanNftAiDraft | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [descriptionImages, setDescriptionImages] = useState<string[]>([]);
  const [price, setPrice] = useState(10);
  const [supply, setSupply] = useState(10);
  const [forgeSession, setForgeSession] = useState<NftForgeSession | null>(null);
  const [fragments, setFragments] = useState<NftFragmentBalance | null>(null);
  const [publishConfirmOpen, setPublishConfirmOpen] = useState(false);
  const [referenceImages, setReferenceImages] = useState<string[]>([]);
  const [versions, setVersions] = useState<ImageVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [busy, setBusy] = useState<"chat" | "reference" | "upload" | "strategy" | "publish" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [strategyTooltip, setStrategyTooltip] = useState<string | null>(null);

  const dismissStrategyTooltip = useCallback(() => {
    if (strategyTooltipTimerRef.current) window.clearTimeout(strategyTooltipTimerRef.current);
    strategyTooltipTimerRef.current = null;
    setStrategyTooltip(null);
  }, []);

  const showStrategyTooltip = useCallback((message: string) => {
    if (strategyTooltipTimerRef.current) window.clearTimeout(strategyTooltipTimerRef.current);
    setStrategyTooltip(message);
    strategyTooltipTimerRef.current = window.setTimeout(() => {
      setStrategyTooltip(null);
      strategyTooltipTimerRef.current = null;
    }, 6_000);
  }, []);

  useEffect(() => () => {
    if (strategyTooltipTimerRef.current) window.clearTimeout(strategyTooltipTimerRef.current);
  }, []);

  const selectedTemplate = useMemo(
    () => templates.find((item) => item.id === templateId) ?? templates[0],
    [templateId, templates],
  );
  const selectedStyle = useMemo(
    () => visualStyles.find((item) => item.id === styleId) ?? visualStyles[0],
    [styleId, visualStyles],
  );
  const selectedVersion = versions.find((item) => item.id === selectedVersionId) ?? versions.at(-1);
  const previewImage = selectedVersion?.image ?? null;

  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
    if (status === "authenticated" && user && !user.is_official_member) router.replace("/membership/join");
  }, [router, status, user]);

  const loadStudioState = useCallback(async () => {
    try {
      const [styleResponse, fragmentResponse, templateResponse] = await Promise.all([
        api.get<NftVisualStyle[]>("/nft/creations/agent/styles"),
        api.get<NftFragmentBalance>("/nft/fragments/me"),
        api.get<NftVisualTemplate[]>("/nft/creations/agent/templates"),
      ]);
      setVisualStyles(styleResponse.data);
      setFragments(fragmentResponse.data);
      setStyleId((current) => current || styleResponse.data[0]?.id || "");
      setTemplates(templateResponse.data);
      setTemplateLibraryLoaded(true);
      const defaultTemplate = templateResponse.data.find((item) => item.id === defaultTemplateId) ?? templateResponse.data[0];
      if (defaultTemplate && !defaultTemplateAppliedRef.current) {
        defaultTemplateAppliedRef.current = true;
        setTemplateId(defaultTemplate.id);
        setReferenceImages(defaultTemplate.reference_image_urls);
        setInput((current) => current || `使用视觉模板「${defaultTemplate.name}」：${defaultTemplate.prompt}`);
      }
    } catch (error) {
      setNotice(getMessage(error));
    }
  }, []);

  useEffect(() => {
    if (status === "authenticated" && user?.is_official_member) void loadStudioState();
  }, [loadStudioState, status, user?.is_official_member]);

  const openTemplateLibrary = async () => {
    if (templateLibraryLoaded) {
      setTemplateModalOpen(true);
      return;
    }
    if (templateLibraryLoading) return;
    setTemplateLibraryLoading(true);
    setNotice(null);
    try {
      const response = await api.get<NftVisualTemplate[]>("/nft/creations/agent/templates");
      setTemplates(response.data);
      setTemplateLibraryLoaded(true);
      setTemplateId((current) => current || response.data[0]?.id || defaultTemplateId);
      setTemplateModalOpen(true);
    } catch (error) {
      setNotice(apiErrorMessage(error, "视觉模板库加载失败，请稍后重试。"));
    } finally {
      setTemplateLibraryLoading(false);
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, busy]);

  const selectTemplate = (template: NftVisualTemplate) => {
    setTemplateId(template.id);
    setReferenceImages(template.reference_image_urls);
    setInput(`使用视觉模板「${template.name}」：${template.prompt}`);
    setNotice(`已使用「${template.name}」，输入框已更新为最新模板提示词，并载入 ${template.reference_image_urls.length} 张参考图。`);
  };

  const sendMessage = async (messageOverride?: string) => {
    const message = (messageOverride ?? input).trim();
    if (!message || busy) return;
    const userMessage: ChatMessage = { id: `user-${Date.now()}`, role: "user", content: message };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setBusy("chat");
    setNotice(null);
    try {
      const response = await api.post<NftAgentChatResponse>("/nft/creations/agent/chat", {
        conversation_id: conversationId,
        message,
        template_id: selectedTemplate?.id || templateId || defaultTemplateId,
        visual_style: selectedStyle?.id || styleId,
        reference_image_urls: referenceImages,
      }, { timeout: 180_000 });
      const result = response.data;
      setConversationId(result.conversation_id);
      const templateWasRecommended = result.tool_events.some(
        (event) => event.tool === "select_visual_template" && event.status === "completed",
      );
      if (templateWasRecommended) {
        setTemplateId(result.template.id);
        setReferenceImages(result.template.reference_image_urls);
      }
      if (result.saved_template) {
        setTemplates((current) => current.some((item) => item.id === result.saved_template?.id)
          ? current
          : [result.saved_template!, ...current]);
      }
      setMessages((current) => [...current, { id: `agent-${Date.now()}`, role: "agent", content: result.assistant_message }]);
      setSummary(result.story_summary);
      setMissingFields(result.missing_fields);
      setToolEvents(result.tool_events);
      setImageGenerationRecommended(result.image_generation_recommended);
      if (result.draft) {
        setDraft(result.draft);
        setName(result.draft.name);
        setDescription(result.draft.description);
        if (result.image_generated && result.draft.image_data_url) {
          const imageUrl = result.draft.image_data_url;
          const pendingVersionId = `generation-${Date.now()}`;
          setVersions((current) => [
            ...current,
            {
              id: pendingVersionId,
              image: imageUrl,
              label: `VERSION ${String(current.length + 1).padStart(2, "0")}`,
              turn: current.length + 1,
              name: result.draft!.name,
              description: result.draft!.description,
              imagePrompt: result.draft!.image_prompt,
              attributes: result.draft!.suggested_attributes,
              forge: null,
            },
          ]);
          setSelectedVersionId(pendingVersionId);
          setForgeSession(null);
          const response = await api.post<NftForgeSession>("/nft/forge/analyze", buildForgeAnalyzePayload({
            conversationId: result.conversation_id,
            templateId: result.template.id,
            visualStyle: selectedStyle?.id || styleId,
            title: result.draft.name,
            storySummary: result.story_summary,
            description: result.draft.description,
            imagePrompt: result.draft.image_prompt,
            imageUrl,
            referenceImageUrls: referenceImages,
            suggestedAttributes: result.draft.suggested_attributes,
            supply,
            priceFanTokens: price,
          }), { timeout: 120_000 });
          applyForge(response.data, pendingVersionId);
          setNotice(`作品已生成并完成五维分析，建议发行 ${response.data.supply} 份，价格 ${response.data.price_fan_tokens} FAN。`);
        } else if (result.image_generation_recommended) {
          setNotice("画面方向已经成熟，你可以继续补充细节，或直接说“生成图片”。");
        } else {
          setNotice("本轮已更新故事、名称与作品描述，画面没有重复生成。");
        }
      }
    } catch (error) {
      setNotice(getMessage(error));
    } finally {
      setBusy(null);
    }
  };

  const applyForge = useCallback((forge: NftForgeSession, pendingVersionId?: string) => {
    setForgeSession(forge);
    setSupply(forge.supply);
    setPrice(forge.price_fan_tokens);
    setFragments((current) => current ? { ...current, balance: forge.fragment_balance, stable_credits: forge.stable_credits, focused_credits: forge.focused_credits } : current);
    setVersions((current) => {
      const pendingVersion = pendingVersionId ? current.find((item) => item.id === pendingVersionId) : null;
      const withoutPending = pendingVersionId ? current.filter((item) => item.id !== pendingVersionId) : current;
      const next = [...withoutPending];
      forge.generated_versions.forEach((version) => {
        const existingIndex = next.findIndex((item) => item.id === version.id);
        const existing = existingIndex >= 0 ? next[existingIndex] : null;
        const item: ImageVersion = {
          id: version.id,
          image: version.url,
          label: existing?.label || pendingVersion?.label || `VERSION ${String(next.length + 1).padStart(2, "0")}`,
          turn: existing?.turn || pendingVersion?.turn || next.length + 1,
          name: version.name || forge.title,
          description: version.description || forge.story_summary,
          imagePrompt: version.image_prompt || forge.image_prompt,
          attributes: version.attributes || forge.suggested_attributes,
          forge,
        };
        if (existingIndex >= 0) next[existingIndex] = item;
        else next.push(item);
      });
      return next;
    });
    setSelectedVersionId(forge.selected_version_id);
    const selected = forge.generated_versions.find((item) => item.id === forge.selected_version_id) ?? forge.generated_versions.at(-1);
    if (selected) {
      setName(selected.name || forge.title);
      setDescription(selected.description || forge.story_summary);
      setDraft((current) => current ? { ...current, image_prompt: selected.image_prompt || current.image_prompt, suggested_attributes: selected.attributes || current.suggested_attributes } : current);
    }
  }, []);

  const selectVersion = async (version: ImageVersion) => {
    const requestId = ++versionSelectionRequestRef.current;
    setSelectedVersionId(version.id);
    setName(version.name);
    setDescription(version.description);
    setDraft((current) => current ? {
      ...current,
      image_prompt: version.imagePrompt,
      suggested_attributes: version.attributes,
    } : current);
    if (version.forge) {
      setForgeSession(version.forge);
      setSupply(version.forge.supply);
      setPrice(version.forge.price_fan_tokens);
      try {
        const response = await api.get<NftForgeSession>(`/nft/forge/${version.forge.id}`);
        if (requestId === versionSelectionRequestRef.current) applyForge(response.data);
      } catch (error) {
        if (requestId === versionSelectionRequestRef.current) {
          setNotice(apiErrorMessage(error, "版本状态读取失败，已保留当前本地版本。"));
        }
      }
    } else {
      setForgeSession(null);
      setNotice("这个版本尚未完成 Forge 分析，请重新生成或上传该图片后再试。");
    }
  };

  useEffect(() => {
    if (!forgeSession || busy || forgeSession.status === "FORGING" || forgeSession.status === "PUBLISHED") return;
    if (forgeSession.supply === supply && forgeSession.price_fan_tokens === price) return;
    const strategyRequestKey = `${forgeSession.id}:${supply}:${price}`;
    if (lastStrategyRequestRef.current === strategyRequestKey) return;
    const timer = window.setTimeout(async () => {
      lastStrategyRequestRef.current = strategyRequestKey;
      setBusy("strategy");
      try {
        const response = await api.patch<NftForgeSession>(`/nft/forge/${forgeSession.id}/strategy`, {
          supply,
          price_fan_tokens: price,
          forge_mode: forgeSession.forge_mode,
        });
        applyForge(response.data);
      } catch (error) {
        showStrategyTooltip(forgeStrategyTooltipText(apiErrorMessage(error, "发行参数更新失败，请检查发行数量和价格。")));
      } finally {
        setBusy(null);
      }
    }, 450);
    return () => window.clearTimeout(timer);
  }, [applyForge, busy, forgeSession, price, showStrategyTooltip, supply]);

  const uploadReferences = async (files: FileList | null) => {
    const selected = Array.from(files || []);
    if (!selected.length) return;
    if (referenceImages.length + selected.length > 6) { setNotice("最多使用 6 张参考图。"); return; }
    setBusy("reference");
    setNotice(null);
    try {
      const urls = await Promise.all(selected.map((file) => uploadImage(file)));
      setReferenceImages((current) => [...current, ...urls]);
      setNotice("参考图已上传，并会用于下一轮生成。");
    } catch (error) {
      setNotice(apiErrorMessage(error, "参考图上传失败。"));
    } finally {
      setBusy(null);
    }
  };

  const uploadCabinetImage = async (files: FileList | null) => {
    const file = files?.[0];
    if (!file || busy) return;
    if (!selectedStyle) {
      setNotice("请先等待视觉风格加载完成。");
      return;
    }
    setBusy("upload");
    setNotice("正在上传图片到 NFT 展厅…");
    let pendingVersionId: string | null = null;
    try {
      const imageUrl = await uploadImage(file);
      pendingVersionId = `upload-${Date.now()}`;
      setVersions((current) => [
        ...current,
        {
          id: pendingVersionId!,
          image: imageUrl,
          label: `UPLOAD ${String(current.length + 1).padStart(2, "0")}`,
          turn: current.length + 1,
          name: "AI 正在命名",
          description: "图片已进入版本柜，正在进行视觉理解与五维分析。",
          imagePrompt: "Analyze the uploaded NFT artwork as the visual source of truth.",
          attributes: [{ trait_type: "来源", value: "创作者上传" }],
          forge: null,
        },
      ]);
      setSelectedVersionId(pendingVersionId);
      setForgeSession(null);
      setName("AI 正在命名");
      setDescription("图片已进入版本柜，正在进行视觉理解与五维分析。");
      setReferenceImages((current) => [imageUrl, ...current.filter((item) => item !== imageUrl)].slice(0, 6));
      setNotice("图片已显示在 NFT 展厅，AI 正在生成名称、描述并分析五维评分…");

      const metadataResponse = await api.post<NftUploadedImageAnalysis>(
        "/nft/creations/agent/analyze-upload",
        {
          image_url: imageUrl,
          template_id: selectedTemplate?.id || templateId || defaultTemplateId,
          visual_style: selectedStyle.id,
        },
        { timeout: 120_000 },
      );
      const metadata = metadataResponse.data;
      const uploadedDraft: FanNftAiDraft = {
        name: metadata.name,
        description: metadata.description,
        theme: metadata.theme,
        image_prompt: metadata.image_prompt,
        suggested_attributes: metadata.suggested_attributes,
        image_data_url: imageUrl,
        metadata_source: metadata.metadata_source,
        image_source: "not_requested",
        degraded: metadata.degraded,
        image_error: null,
        prompt_version: metadata.prompt_version,
      };
      setDraft(uploadedDraft);
      setName(metadata.name);
      setDescription(metadata.description);
      setSummary(metadata.story_summary);
      setMissingFields([]);
      setImageGenerationRecommended(false);
      setVersions((current) => current.map((version) => version.id === pendingVersionId ? {
        ...version,
        name: metadata.name,
        description: metadata.description,
        imagePrompt: metadata.image_prompt,
        attributes: metadata.suggested_attributes,
      } : version));
      setMessages((current) => [...current, {
        id: `agent-upload-${Date.now()}`,
        role: "agent",
        content: `已识别上传图片并命名为「${metadata.name}」。正在完成五维评分、建议发行量和 FAN 价格。`,
      }]);
      setToolEvents([
        {
          tool: "analyze_uploaded_nft_image",
          status: metadata.degraded ? "degraded" : "completed",
          summary: metadata.degraded ? "视觉模型暂不可用，已使用规则生成基础 metadata" : "视觉模型已生成名称、描述和作品提示词",
        },
      ]);

      const forgeReferences = [imageUrl, ...referenceImages.filter((item) => item !== imageUrl)].slice(0, 6);
      const forgeResponse = await api.post<NftForgeSession>("/nft/forge/analyze", buildForgeAnalyzePayload({
        conversationId,
        templateId: selectedTemplate?.id || templateId || defaultTemplateId,
        visualStyle: selectedStyle.id,
        title: metadata.name,
        storySummary: metadata.story_summary,
        description: metadata.description,
        imagePrompt: metadata.image_prompt,
        imageUrl,
        referenceImageUrls: forgeReferences,
        suggestedAttributes: metadata.suggested_attributes,
        supply,
        priceFanTokens: price,
      }), { timeout: 120_000 });
      applyForge(forgeResponse.data, pendingVersionId);
      setToolEvents((current) => [...current, {
        tool: "analyze_memory_forge",
        status: "completed",
        summary: "已根据上传图片完成 AI 五维评分和发行建议",
      }]);
      setNotice(`「${metadata.name}」已完成分析：建议发行 ${forgeResponse.data.supply} 份，价格 ${forgeResponse.data.price_fan_tokens} FAN。`);
    } catch (error) {
      setNotice(apiErrorMessage(error, pendingVersionId
        ? "图片已保存在版本柜，但 AI 分析暂时失败，请稍后重试。"
        : "图片上传失败，请稍后重试。"));
    } finally {
      setBusy(null);
    }
  };

  const publish = async () => {
    if (!previewImage || !draft || !forgeSession || busy) return;
    const artifactName = name.trim() || draft.name || "Fanora NFT";
    setPublishConfirmOpen(false);
    setBusy("publish");
    setNotice(null);
    void NiceModal.show(GlobalProcessModal, {
      title: "正在发布并铸造 NFT",
      message: "发行判定已提交，正在扣除 FAN、写入 IPFS，并连接 Monad 完成 NFT 铸造。",
      eyebrow: "MONAD TRANSACTION",
      gifUrl: null,
      phase: "processing",
      progressKind: "publish",
      artifactName,
      imageUrl: previewImage,
    });
    try {
      let preparedForge = forgeSession;
      if (preparedForge.supply !== supply || preparedForge.price_fan_tokens !== price) {
        try {
          const strategy = await api.patch<NftForgeSession>(`/nft/forge/${preparedForge.id}/strategy`, {
            supply,
            price_fan_tokens: price,
            forge_mode: preparedForge.forge_mode,
          });
          preparedForge = strategy.data;
          applyForge(preparedForge);
        } catch (error) {
          await hideGlobalProcessModal().catch(() => undefined);
          setBusy(null);
          showStrategyTooltip(forgeStrategyTooltipText(apiErrorMessage(error, "发行参数更新失败，请检查发行数量和价格。")));
          return;
        }
      }
      const endpoint = preparedForge.latest_attempt ? "retry" : "start";
      const forgeResponse = await api.post<NftForgeSession>(`/nft/forge/${preparedForge.id}/${endpoint}`, {
        idempotency_key: `publish:${preparedForge.id}:${Date.now()}`,
        use_fragment_credit: false,
      });
      applyForge(forgeResponse.data);
      void refreshUser().catch(() => undefined);
      if (forgeResponse.data.status === "FAILED" || forgeResponse.data.status === "ERROR") {
        await hideGlobalProcessModal().catch(() => undefined);
        setBusy(null);
        const isFailed = forgeResponse.data.status === "FAILED";
        void NiceModal.show(GlobalInfoModal, {
          title: isFailed ? "NFT 发行判定未通过" : "NFT 发行处理异常",
          message: isFailed
            ? `作品和故事已保留，并获得 1 个 Memory Fragment。当前共有 ${forgeResponse.data.fragment_balance} 个 Fragment，可以调整发行参数后再次尝试。`
            : `本次没有计为发行失败，费用已自动恢复，作品仍保留在创作台。${forgeResponse.data.latest_attempt?.error_message ? `\n${forgeResponse.data.latest_attempt.error_message}` : ""}`,
          tone: isFailed ? "warning" : "error",
          eyebrow: isFailed ? "FORGE FAILED" : "PUBLISH ERROR",
          confirmLabel: "返回作品",
        });
        return;
      }
      const response = await api.post<FanNftCreateResponse>("/nft/creations", {
        forge_session_id: forgeResponse.data.id,
        name: name.trim(),
        description: description.trim(),
        theme: selectedTemplate?.name ?? draft.theme,
        price_fan_tokens: price,
        max_supply: supply,
        public_attributes: draft.suggested_attributes,
        copyright_declaration: copyrightDeclaration,
        image_data_url: previewImage,
        story_image_urls: descriptionImages,
      });
      void refreshUser().catch(() => undefined);
      void NiceModal.show(GlobalProcessModal, {
        title: "NFT 已完成铸造",
        message: "图片与 metadata 已写入 IPFS，Monad 已确认限量 NFT 创建交易。",
        eyebrow: "MONAD TRANSACTION",
        gifUrl: null,
        phase: "complete",
        progressKind: "publish",
        artifactName: response.data.listing.name,
        imageUrl: response.data.listing.image_url || previewImage,
      });
      await waitForUi(1200);
      await hideGlobalProcessModal().catch(() => undefined);
      setBusy(null);
      await NiceModal.show(GlobalInfoModal, {
        title: `${response.data.listing.name} 铸造成功`,
        message: "图片与 metadata 已写入 IPFS，限量 NFT 已在 Monad 完成创建并进入 NFT Gallery。",
        tone: "success",
        eyebrow: "NFT MINTED",
        imageUrl: response.data.listing.image_url || previewImage,
        imageAlt: response.data.listing.name,
        celebrate: true,
        celebrationDurationMs: 4_000,
        actionLabel: "查看链上 NFT",
        actionUrl: response.data.listing.explorer_url,
        confirmLabel: "进入 NFT Gallery",
      });
      router.push("/collections");
    } catch (error) {
      await hideGlobalProcessModal().catch(() => undefined);
      setBusy(null);
      void NiceModal.show(GlobalInfoModal, {
        title: "NFT 发布没有完成",
        message: getMessage(error),
        tone: "error",
        eyebrow: "PUBLISH ERROR",
        confirmLabel: "返回创作台重试",
      });
    }
  };

  const resetSession = () => {
    setConversationId(null);
    setMessages([{ id: `welcome-${Date.now()}`, role: "agent", content: welcomeMessage }]);
    setSummary(""); setDraft(null); setName(""); setDescription(""); setDescriptionImages([]); setVersions([]); setSelectedVersionId(null); setImageGenerationRecommended(false); setForgeSession(null); setPublishConfirmOpen(false);
  };

  if (status !== "authenticated" || !user?.is_official_member) {
    return <main className={styles.loading}><LoaderCircle className="h-7 w-7 animate-spin" /> 正在校验创作者身份</main>;
  }

  return (
    <main className={styles.stage}>
      <video ref={videoRef} className={styles.videoBackground} autoPlay muted loop playsInline preload="auto" aria-hidden="true" onCanPlay={() => void videoRef.current?.play()} onEnded={() => { if (videoRef.current) { videoRef.current.currentTime = 0; void videoRef.current.play(); } }}><source src="https://fanora-1251127085.cos.ap-guangzhou.myqcloud.com/bg.mp4" type="video/mp4" /></video>
      <div className={styles.videoOverlay} aria-hidden="true" />
      <div className={styles.grid} aria-hidden="true" />
      <div className={styles.scanlines} aria-hidden="true" />

      <header className={styles.hudHeader}>
        <button type="button" onClick={() => router.push("/collections")} className={styles.iconButton} title="返回 Gallery"><ArrowLeft /></button>
        <div className="min-w-0"><p>FANORA CORE // MEMORY SYNTHESIS</p><h1 className={styles.typewriter}>让每一轮对话，都让作品更接近你心中的记忆。</h1></div>
        <div className={styles.headerStatus}><span><i /> AGENT ONLINE</span><span className={styles.fragmentHud}>FRAGMENT {fragments?.balance ?? 0}</span><FanTokenAmount amount={user.fan_token_balance} showSymbol /></div>
      </header>

      {notice ? <div role="status" className={styles.notice}>{notice}<button type="button" onClick={() => setNotice(null)} aria-label="关闭提示"><X /></button></div> : null}

      <div className={styles.workspace}>
        <aside className={styles.leftSidebar}>
          <div className={styles.panelHeader}><span><Layers3 /> 灵感配置</span><small>ASSET NODE</small></div>
          <button type="button" className={styles.templateSelector} onClick={() => void openTemplateLibrary()} disabled={templateLibraryLoading}>
            {selectedTemplate ? <span className={styles.selectedTemplateImage}><Image src={selectedTemplate.preview_image_url} alt={selectedTemplate.name} fill sizes="72px" className="object-cover" /></span> : <span className={styles.selectedTemplateImage}><ImagePlus /></span>}
            <span><small>视觉模板库</small><strong>{templateLibraryLoading ? "模板加载中" : selectedTemplate?.name || "选择模板"}</strong><em>{selectedTemplate?.description || "点击后加载模板和参考图"}</em></span>{templateLibraryLoading ? <LoaderCircle className="animate-spin" /> : <ChevronRight />}
          </button>
          <button type="button" className={styles.manageTemplates} onClick={() => void openTemplateLibrary()} disabled={templateLibraryLoading}>{templateLibraryLoading ? <LoaderCircle className="animate-spin" /> : <Plus />} 浏览或新建视觉模板</button>

          <p className={styles.sectionLabel}><Palette /> 视觉风格</p>
          <div className={styles.styleList}>{visualStyles.map((item) => <button key={item.id} type="button" onClick={() => setStyleId(item.id)} className={styleId === item.id ? styles.styleActive : ""}><strong>{item.name}</strong><span>{item.description}</span></button>)}</div>

          <div className={styles.referenceHeader}><span><FileImage /> 参考图</span><label><ImagePlus /> 添加<input type="file" accept="image/jpeg,image/png,image/webp,image/gif" multiple onChange={(event) => void uploadReferences(event.target.files)} /></label></div>
          <div className={styles.referenceStrip}>{referenceImages.map((url, index) => <div key={`${url}-${index}`}><Image src={url} alt={`参考图 ${index + 1}`} fill sizes="58px" className="object-cover" /><button type="button" aria-label={`移除参考图 ${index + 1}`} onClick={() => setReferenceImages((current) => current.filter((_, itemIndex) => itemIndex !== index))}><X /></button></div>)}{!referenceImages.length ? <span>下一轮可加入最多 6 张参考图</span> : null}</div>

          <div className={styles.sessionInfo}><span>当前会话<strong>{conversationId ? conversationId.slice(0, 8) : "等待输入"}</strong></span><button type="button" onClick={resetSession}>新建</button></div>
          <div className={styles.toolLog}><p>TOOL TRACE</p>{toolEvents.length ? toolEvents.map((event, index) => <div key={`${event.tool}-${index}`}><Check /><span>{event.tool}<small>{event.summary}</small></span></div>) : <span>Agent 会按故事状态调用模板、保存和图片生成工具</span>}</div>
        </aside>

        <section className={styles.agentPanel}>
          <div className={styles.panelHeader}><span><Bot /> STORY & ART AGENT</span><small>AI 共创、记忆成长、作品进化</small></div>
          <div className={styles.chatStream}>{messages.map((message) => <div key={message.id} className={message.role === "agent" ? styles.agentMessage : styles.userMessage}><span>{message.role === "agent" ? <Image src="/img/agent/bot.webp" alt="Fanora Agent" width={22} height={22} className={styles.agentAvatar} /> : <MessageSquareText />}</span><p>{message.content}</p></div>)}{busy === "chat" ? <div className={styles.agentMessage}><span><Image src="/img/agent/bot.webp" alt="Fanora Agent" width={22} height={22} className={styles.agentAvatar} /></span><p className={styles.thinking}>正在理解本轮变化并更新作品状态<i /><i /><i /></p></div> : null}<div ref={chatEndRef} /></div>
          {summary ? <div className={styles.storyState}><strong>当前故事状态</strong><p>{summary}</p></div> : null}
          <div className={styles.stateBar}><span>STATE</span>{missingFields.length ? missingFields.map((field) => <i key={field}>{field}</i>) : <i className={styles.readyState}><Check /> STORY LOCKED</i>}</div>
          <div className={styles.composer}><textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void sendMessage(); } }} placeholder="描述故事，或继续要求修改名称、画面、风格、材质和作品描述…" /><button type="button" onClick={() => void sendMessage()} disabled={!input.trim() || Boolean(busy)} title="发送给 Agent">{busy === "chat" ? <LoaderCircle className="animate-spin" /> : <Send />}</button></div>
          <p className={styles.sendHint}>{imageGenerationRecommended ? "画面方向已成熟，Agent 会在合适时生成；也可直接说“生成图片”。" : "继续讲故事或调整画面，Agent 不会重复生成没有变化的图片。"}</p>
        </section>

        <section className={styles.galleryPanel}>
          <div className={styles.panelHeader}><span><Sparkles /> NFT 展厅</span><small>LIVE PREVIEW</small></div>
          <div className={styles.cardWall}><div className={styles.ghostCardA} /><div className={styles.ghostCardB} /><div className={styles.nftCard}><span className={styles.photonA} /><span className={styles.photonB} />{previewImage ? <Image src={previewImage} alt={name || "NFT 作品预览"} fill unoptimized sizes="240px" className={styles.previewArtwork} /> : <div className={styles.emptyArtwork}><Sparkles /><strong>等待作品显影</strong><span>故事和画面方向成熟后，Agent 会自动生成作品</span></div>}<div className={styles.lightScan} /></div></div>
          <div className={styles.collectionShelf}><div className={styles.cabinetHeader}><span>VERSION CABINET · {versions.length} VERSIONS</span><label className={styles.cabinetUpload}>{busy === "upload" ? <LoaderCircle className="animate-spin" /> : <ImagePlus />}<b>{busy === "upload" ? "AI 分析中" : "上传图片"}</b><input type="file" accept="image/jpeg,image/png,image/webp" disabled={Boolean(busy)} onChange={(event) => { void uploadCabinetImage(event.target.files); event.currentTarget.value = ""; }} /></label></div><div className={styles.cabinetVersions}>{versions.length ? versions.map((version) => <button key={version.id} type="button" onClick={() => void selectVersion(version)} className={selectedVersion?.id === version.id ? styles.versionActive : ""}><Image src={version.image} alt={version.label} fill unoptimized className="object-cover" /><em>{version.label}</em></button>) : <i>上传图片或让 Agent 生图，每个结果都会保存在这里</i>}</div></div>
          <div className={styles.metadataForm}>
            <label>NFT 名称<input value={name} onChange={(event) => setName(event.target.value)} placeholder="每轮由 Agent 优化，可继续编辑" /></label>
            <label className={styles.descriptionEditor}>作品描述<MarkdownEditor value={description} onChange={setDescription} maxLength={1000} imageUrls={descriptionImages} onImageUrlsChange={setDescriptionImages} onImageError={setNotice} compact /></label>
            <div className={styles.strategyFields}>
              {strategyTooltip ? <div role="alert" className={styles.strategyTooltip}><AlertTriangle /><span>{strategyTooltip}</span><button type="button" onClick={dismissStrategyTooltip} aria-label="关闭发行参数错误提示"><X /></button><i aria-hidden="true" /></div> : null}
              <label>发行数量<input type="number" min={1} max={1000} value={supply} onChange={(event) => { dismissStrategyTooltip(); setSupply(Number(event.target.value)); }} /></label>
              <label>价格 FAN<input type="number" min={1} max={1000000} value={price} onChange={(event) => { dismissStrategyTooltip(); setPrice(Number(event.target.value)); }} /></label>
            </div>
          </div>
          {forgeSession ? <div className={styles.memoryForgeSummary}>
            <div><span>MEMORY FORGE</span><strong>AI 五维分析</strong></div>
            <div className={styles.forgeDimensionList}>
              {forgeDimensions.map(([key, label]) => {
                const score = Math.max(0, Math.min(100, forgeSession.analysis.dimensions[key] ?? 0));
                return <div key={key} className={styles.forgeDimension}>
                  <div className={styles.forgeDimensionMeta}><span>{label}</span><strong>{score}</strong></div>
                  <div className={styles.forgeDimensionTrack} role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={score}><i style={{ width: `${score}%` }} /></div>
                </div>;
              })}
            </div>
            <dl>
              <div><dt>RareScore</dt><dd>{forgeSession.analysis.rare_score}</dd></div>
              <div><dt>建议发行</dt><dd>{forgeSession.analysis.recommend_supply.default} 份</dd></div>
              <div><dt>建议价格</dt><dd>{forgeSession.analysis.recommend_price.default} FAN</dd></div>
              <div><dt>发行成功率</dt><dd>{Math.round(forgeSession.probability.success_rate)}%</dd></div>
              <div><dt>判定消耗</dt><dd>{forgeSession.probability.fan_cost} FAN</dd></div>
              <div><dt>Fragment</dt><dd>{forgeSession.fragment_balance}</dd></div>
            </dl>
          </div> : null}
          <div className={styles.publishSummary}><span>发行判定通过后写入 IPFS 与 Monad</span><span>发布费 100 FAN</span><span>发行失败获得 1 Fragment</span></div>
          <button type="button" className={styles.publishButton} disabled={!previewImage || !name.trim() || !description.trim() || !forgeSession?.selected_version_id || !["ANALYZED", "FAILED", "ERROR"].includes(forgeSession.status) || Boolean(busy)} onClick={() => setPublishConfirmOpen(true)}>{busy === "publish" ? <><LoaderCircle className="animate-spin" /> 正在确认发行结果</> : <><Check /> 确认并发布 NFT</>}</button>
        </section>
      </div>

      <NftVisualTemplateModal open={templateModalOpen} templates={templates} selectedId={templateId} onClose={() => setTemplateModalOpen(false)} onSelect={selectTemplate} onCreated={(template) => setTemplates((current) => [template, ...current])} />
      <PublishConfirmModal
        open={publishConfirmOpen}
        successRate={Math.round(forgeSession?.probability.success_rate ?? 0)}
        forgeCost={forgeSession?.probability.fan_cost ?? 0}
        busy={busy === "publish"}
        onClose={() => setPublishConfirmOpen(false)}
        onConfirm={() => void publish()}
      />
    </main>
  );
}
