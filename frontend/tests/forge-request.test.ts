import assert from "node:assert/strict";
import test from "node:test";

import { buildForgeAnalyzePayload, forgeStrategyTooltipText } from "../lib/nft/forge-request";

test("forge analysis payload is normalized to the backend schema before version analysis", () => {
  const payload = buildForgeAnalyzePayload({
    conversationId: "c".repeat(90),
    templateId: "t".repeat(70),
    visualStyle: "",
    title: "画",
    storySummary: "喜欢",
    description: "纪念",
    imagePrompt: "暖光",
    imageUrl: "https://img.example/version-2.png",
    referenceImageUrls: [
      "https://img.example/1.png",
      "https://img.example/1.png",
      "https://img.example/2.png",
      "https://img.example/3.png",
      "https://img.example/4.png",
      "https://img.example/5.png",
      "https://img.example/6.png",
      "https://img.example/7.png",
    ],
    suggestedAttributes: [
      { trait_type: "情绪", value: "温暖" },
      { trait_type: "", value: "忽略" },
      ...Array.from({ length: 9 }, (_, index) => ({ trait_type: `属性${index}`, value: `值${index}` })),
    ],
    supply: 5_000,
    priceFanTokens: 0,
  });

  assert.equal(payload.conversation_id?.length, 80);
  assert.equal(payload.template_id?.length, 64);
  assert.equal(payload.visual_style, "cinematic");
  assert.ok(payload.title.length >= 2 && payload.title.length <= 100);
  assert.ok(payload.story_summary.length >= 10 && payload.story_summary.length <= 1500);
  assert.ok(payload.description.length >= 10 && payload.description.length <= 1000);
  assert.ok(payload.image_prompt.length >= 10 && payload.image_prompt.length <= 2500);
  assert.equal(payload.reference_image_urls.length, 6);
  assert.equal(new Set(payload.reference_image_urls).size, payload.reference_image_urls.length);
  assert.equal(payload.suggested_attributes.length, 8);
  assert.equal(payload.supply, 1_000);
  assert.equal(payload.price_fan_tokens, 1);
});

test("forge analysis rejects an unhosted oversized image before sending a 422 request", () => {
  assert.throws(() => buildForgeAnalyzePayload({
    visualStyle: "cinematic",
    title: "画面版本",
    storySummary: "一段完整的粉丝故事摘要，包含主体与情绪。",
    description: "一件具有完整视觉信息的粉丝 NFT 收藏品。",
    imagePrompt: "Preserve the complete composition and warm cinematic lighting.",
    imageUrl: `data:image/png;base64,${"a".repeat(3_000)}`,
    referenceImageUrls: [],
    suggestedAttributes: [],
    supply: 10,
    priceFanTokens: 10,
  }), /托管/);
});

test("forge strategy validation errors become actionable Chinese tooltip text", () => {
  assert.equal(
    forgeStrategyTooltipText("supply：Input should be less than or equal to 1000"),
    "发行数量不能超过 1000，请修改后重试。",
  );
  assert.equal(
    forgeStrategyTooltipText("price_fan_tokens：Input should be greater than or equal to 1"),
    "价格不能低于 1 FAN，请修改后重试。",
  );
});
