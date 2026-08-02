type PublicAttribute = { trait_type: string; value: string };

type ForgeAnalyzeInput = {
  conversationId?: string | null;
  templateId?: string | null;
  visualStyle: string;
  title: string;
  storySummary: string;
  description: string;
  imagePrompt: string;
  imageUrl: string;
  referenceImageUrls: string[];
  suggestedAttributes: PublicAttribute[];
  supply: number;
  priceFanTokens: number;
};

const normalizeText = (value: string, fallback: string, minimum: number, maximum: number) => {
  const trimmed = value.trim();
  const completed = trimmed.length >= minimum
    ? trimmed
    : trimmed
      ? `${trimmed}。${fallback}`
      : fallback;
  return completed.slice(0, maximum);
};

const clampInteger = (value: number, minimum: number, maximum: number) => {
  const integer = Number.isFinite(value) ? Math.round(value) : minimum;
  return Math.max(minimum, Math.min(maximum, integer));
};

export function buildForgeAnalyzePayload(input: ForgeAnalyzeInput) {
  const imageUrl = input.imageUrl.trim();
  if (!imageUrl.startsWith("http://") && !imageUrl.startsWith("https://")) {
    throw new Error("当前版本图片尚未完成托管，请重新生成或上传后再分析。");
  }
  if (imageUrl.length > 2_048) {
    throw new Error("当前版本图片托管地址无效，请重新生成或上传后再分析。");
  }

  const referenceImageUrls = Array.from(new Set(input.referenceImageUrls.map((item) => item.trim())))
    .filter((item) => (item.startsWith("http://") || item.startsWith("https://")) && item.length <= 2_048)
    .slice(0, 6);
  const suggestedAttributes = input.suggestedAttributes
    .map((item) => ({ trait_type: item.trait_type.trim().slice(0, 60), value: item.value.trim().slice(0, 120) }))
    .filter((item) => item.trait_type && item.value)
    .slice(0, 8);

  return {
    conversation_id: input.conversationId?.trim().slice(0, 80) || null,
    template_id: input.templateId?.trim().slice(0, 64) || null,
    visual_style: normalizeText(input.visualStyle, "cinematic", 2, 80),
    title: normalizeText(input.title, "未命名 NFT", 2, 100),
    story_summary: normalizeText(input.storySummary, "这是一段正在形成的粉丝 NFT 创作记忆。", 10, 1_500),
    description: normalizeText(input.description, "这件作品正在整理为可收藏的粉丝 NFT。", 10, 1_000),
    image_prompt: normalizeText(
      input.imagePrompt,
      "Preserve the complete artwork, composition, palette, materials and emotional atmosphere.",
      10,
      2_500,
    ),
    image_url: imageUrl,
    reference_image_urls: referenceImageUrls,
    suggested_attributes: suggestedAttributes,
    supply: clampInteger(input.supply, 1, 1_000),
    price_fan_tokens: clampInteger(input.priceFanTokens, 1, 1_000_000),
    forge_mode: "FOCUSED" as const,
    copyright_confirmed: false,
  };
}
