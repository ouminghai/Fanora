import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(
  new URL("../components/collection/CollectionDashboard.tsx", import.meta.url),
  "utf8",
);
const collectionDashboardStyleSource = readFileSync(
  new URL("../components/collection/CollectionDashboard.module.css", import.meta.url),
  "utf8",
);
const transactionProgressSource = readFileSync(
  new URL("../components/nft/ChainTransactionProgress.tsx", import.meta.url),
  "utf8",
);
const globalInfoModalSource = readFileSync(
  new URL("../components/modals/GlobalInfoModal.tsx", import.meta.url),
  "utf8",
);
const globalProcessModalSource = readFileSync(
  new URL("../components/modals/GlobalProcessModal.tsx", import.meta.url),
  "utf8",
);
const styleSource = readFileSync(new URL("../public/styles/style.css", import.meta.url), "utf8");
const profileSource = readFileSync(
  new URL("../components/profile/ProfileDashboard.tsx", import.meta.url),
  "utf8",
);
const collectionProfileSource = readFileSync(
  new URL("../components/collection/CollectionProfilePanel.tsx", import.meta.url),
  "utf8",
);
const collectionProfileStyleSource = readFileSync(
  new URL("../components/collection/CollectionProfilePanel.module.css", import.meta.url),
  "utf8",
);
const profileRouteSource = readFileSync(new URL("../app/profile/page.tsx", import.meta.url), "utf8");

test("collection profile status badge does not apply absolute positioning to the avatar root", () => {
  assert.match(collectionProfileSource, /className=\{styles\.avatarStatusBadge\}/);
  assert.match(collectionProfileStyleSource, /\.avatarStatusBadge\s*\{[^}]*position:\s*absolute[^}]*\}/);
  assert.doesNotMatch(collectionProfileStyleSource, /\.profileAvatar\s*>\s*span\s*\{/);
});

test("profile editing does not expose a separate avatar upload button", () => {
  assert.doesNotMatch(profileSource, /selectAvatar/);
  assert.doesNotMatch(profileSource, /选择图片（最大 1 MB）/);
  assert.match(profileSource, /avatar_url: user\.avatar_url \|\| ""/);
});

test("collection uses the Cyber Identity passport and asset tabs without loading the fan profile", () => {
  assert.match(source, /src="\/video\/bg\.mp4"/);
  assert.match(source, /autoPlay muted loop playsInline preload="auto"/);
  assert.match(source, /onCanPlay=\{\(\) => void videoRef\.current\?\.play\(\)\}/);
  assert.match(source, /const backgroundLayers =/);
  assert.match(source, /styles\.loadingScreen[\s\S]*\{backgroundLayers\}/);
  assert.match(source, /className=\{styles\.videoBackground\}/);
  assert.match(source, /className=\{styles\.videoOverlay\}/);
  assert.match(source, /className=\{styles\.videoGrid\}/);
  assert.match(source, /className=\{styles\.videoScanlines\}/);
  assert.match(collectionDashboardStyleSource, /\.videoBackground\s*\{[^}]*opacity:\s*0\.56[^}]*filter:\s*saturate\(0\.95\) hue-rotate\(8deg\)/);
  assert.match(collectionDashboardStyleSource, /\.videoGrid\s*\{[^}]*opacity:\s*0\.24/);
  assert.match(collectionDashboardStyleSource, /\.videoScanlines\s*\{[^}]*opacity:\s*0\.12/);
  assert.match(source, /CYBER IDENTITY \/\/ FANORA PROTOCOL/);
  assert.match(source, /Fanora Identity Awakening/);
  assert.match(source, /ON-CHAIN PASSPORT/);
  assert.match(source, /NFT BADGE HOLOGRAM/);
  assert.match(source, /IDENTITY BLOCK STREAM/);
  assert.match(source, /api\.get<MembershipLevel\[]>\("\/membership-levels"\)/);
  assert.match(source, /levelProgressLabel/);
  assert.match(source, /还需 \$\{neededFan\.toLocaleString\("en-US"\)\} FAN/);
  assert.match(source, /key=\{activeTab\}/);
  assert.match(source, /<CollectibleCard/);
  assert.match(source, /key=\{item\.token_type_id\}/);
  assert.match(source, /item=\{item\}/);
  assert.match(source, /index=\{index\}/);
  assert.match(source, /animationDelay: `\$\{Math\.min\(index, 12\) \* 55\}ms`/);
  assert.match(source, /链上身份/);
  assert.match(source, /我的收藏/);
  assert.match(source, /身份资料/);
  assert.match(source, /<CollectionProfilePanel onSaved=\{refreshCollectionAfterProfileSave\}/);
  assert.match(collectionProfileSource, /api\.patch<FanoraUser>\("\/users\/me"/);
  assert.match(collectionProfileSource, /系统会自动更新链上卡面/);
  assert.doesNotMatch(collectionProfileSource, /\/profile\/me/);
  assert.match(profileRouteSource, /redirect\("\/collection\?tab=profile"\)/);
  assert.doesNotMatch(source, /徽章申请/);
  assert.doesNotMatch(source, /\/nft\/applications/);
  assert.doesNotMatch(source, /FanProfileAnalysis/);
  assert.doesNotMatch(source, /FanProfileSummary/);
  assert.doesNotMatch(source, /api\.get.*\("\/profile\/me"\)/);
});

test("collection keeps identity synchronization and on-chain links", () => {
  assert.match(source, /\/nft\/identity\/sync/);
  assert.match(source, /api\.get<MyCollection>\("\/nft\/me"\)/);
  assert.match(source, /initializedUserRef\.current === user\.id/);
  assert.match(source, /!user\.is_official_member/);
  assert.match(source, /functionName: "identityTokenOf"/);
  assert.match(source, /functionName: "ownerOf"/);
  assert.match(source, /Monad 链上已验证/);
  assert.match(source, /api\.get<MyCollection>\("\/nft\/me"\)/);
  assert.match(source, /refreshUser\(\)/);
  assert.match(source, /identity\?\.metadata_version/);
  assert.match(source, /IPFS 身份档案/);
  assert.match(source, /铸造交易/);
  assert.match(source, /确认区块/);
  assert.match(source, /https:\/\/testnet\.monadvision\.com\/nft\/\$\{identity\.contract_address\}\/\$\{visibleTokenId\}\?tab=Overview/);
  assert.match(source, /在 MonadVision 查看 NFT/);
  assert.match(source, /const identityExplorerUrl = membershipNftExplorerUrl\(identity, chainTokenId\)/);
  assert.match(source, /href=\{identityExplorerUrl\}[\s\S]*身份已在 Monad 验证<ExternalLink \/>/);
  assert.match(source, /fan_nft_creation_id/);
  assert.match(source, /\/item\/\$\{item\.fan_nft_creation_id\}/);
  assert.match(source, /查看链上资产/);
  assert.match(source, /https:\/\/testnet\.monadexplorer\.com\/tx\/\$\{identity\.mint_operation\.transaction_hash\}/);
  assert.match(source, /FanoraMembership/);
  assert.match(source, /可用 FAN/);
  assert.match(source, /累计 FAN/);
  assert.match(source, /user\.fan_token_balance/);
  assert.match(source, /user\.fan_token_lifetime_earned/);
  assert.match(source, /累计获得 FAN 确认会员等级/);
});

test("collection keeps profile editing available while redirecting inactive members from asset tabs", () => {
  const routeGuard = source.slice(
    source.indexOf('if (status === "anonymous"'),
    source.indexOf("const identity = collection?.identity"),
  );
  assert.match(routeGuard, /requestedTab !== "profile"/);
  assert.match(routeGuard, /if \(!user\.is_official_member && requestedTab !== "profile"\) \{\s*router\.replace\("\/membership\/join"\);\s*return;/);
  assert.ok(routeGuard.indexOf('router.replace("/membership/join")') < routeGuard.indexOf("void load()"));
});

test("collection automatically creates, refreshes, reveals, and downloads a free membership card", () => {
  assert.match(source, /\/nft\/identity\/card\/refresh/);
  assert.match(source, /\/nft\/identity\/card/);
  assert.match(source, /制作会员证/);
  assert.match(source, /无需消耗 FAN/);
  assert.match(source, /autoCardSyncKeyRef/);
  assert.match(source, /identity\?\.is_member_card && !identity\.card_needs_refresh/);
  assert.match(source, /\/img\/membercard\/membercard\.jpg/);
  assert.match(source, /membership-card-stage/);
  assert.match(source, /progressKind: "member-card"/);
  assert.match(source, /const MEMBER_CARD_CELEBRATION_MS = 4_000/);
  assert.match(source, /imageUrl: completedIdentity\?\.image_url/);
  assert.match(source, /celebrate: response\.data\.changed/);
  assert.match(source, /celebrationDurationMs: MEMBER_CARD_CELEBRATION_MS/);
  assert.match(transactionProgressSource, /"member-card": \["验证会员身份"/);
  assert.doesNotMatch(transactionProgressSource, /"member-card": \["扣除 FAN"/);
  assert.match(source, /downloadMembershipCard/);
  assert.match(source, /会员等级已更新，点击卡面刷新会员证/);
  const autoCardSyncBlock = source.slice(source.indexOf("const syncKey = ["), source.indexOf("].join", source.indexOf("const syncKey = [")));
  assert.doesNotMatch(autoCardSyncBlock, /fan_token_lifetime_earned/);
  assert.match(autoCardSyncBlock, /user\.display_name/);
  assert.match(autoCardSyncBlock, /user\.username/);
});

test("owned collection NFTs can be selected as the current profile avatar", () => {
  assert.match(source, /function CollectibleCard/);
  assert.match(source, /设为头像/);
  assert.match(source, /当前头像/);
  assert.match(source, /avatarBusyTokenId/);
  assert.match(source, /setCollectibleAvatar/);
  assert.match(source, /\/nft\/collectibles\/\$\{item\.token_type_id\}\/avatar/);
  assert.match(source, /user\.avatar_url === item\.image_url/);
});

test("Gallery routes NFT creation to the stateful Agent studio", () => {
  const marketSource = readFileSync(
    new URL("../components/nft/FanNftMarket.tsx", import.meta.url),
    "utf8",
  );
  const createPageSource = readFileSync(
    new URL("../app/collections/create/page.tsx", import.meta.url),
    "utf8",
  );
  const studioSource = readFileSync(new URL("../components/nft/NftStudioWorkbench.tsx", import.meta.url), "utf8");
  const studioStyleSource = readFileSync(
    new URL("../components/nft/NftStudioWorkbench.module.css", import.meta.url),
    "utf8",
  );
  const templateModalSource = readFileSync(
    new URL("../components/nft/NftVisualTemplateModal.tsx", import.meta.url),
    "utf8",
  );
  const templateModalStyles = readFileSync(
    new URL("../components/nft/NftVisualTemplateModal.module.css", import.meta.url),
    "utf8",
  );
  const publishConfirmModalSource = readFileSync(
    new URL("../components/nft/PublishConfirmModal.tsx", import.meta.url),
    "utf8",
  );

  assert.match(marketSource, /href="\/collections\/create"/);
  assert.match(marketSource, /创造 NFT/);
  assert.doesNotMatch(marketSource, /setPublishOpen\(true\)/);
  assert.match(createPageSource, /<NftStudioWorkbench/);
  assert.match(studioSource, /\/nft\/creations\/agent\/chat/);
  assert.match(studioSource, /\/nft\/creations\/agent\/templates/);
  assert.match(studioSource, /\/nft\/creations\/agent\/styles/);
  assert.match(studioSource, /conversation_id: conversationId/);
  assert.match(studioSource, /reference_image_urls: referenceImages/);
  assert.match(studioSource, /result\.template\.id/);
  assert.match(studioSource, /result\.saved_template/);
  assert.match(studioSource, /帮我推荐一个模板/);
  assert.match(studioSource, /把当前版本另存为模板/);
  assert.match(studioSource, /故事和画面方向成熟后，我会自动生成作品/);
  assert.match(studioSource, /imageGenerationRecommended/);
  assert.match(studioSource, /\/nft\/forge\/analyze/);
  assert.match(studioSource, /\/nft\/forge\/\$\{preparedForge\.id\}\/\$\{endpoint\}/);
  assert.doesNotMatch(studioSource, /<ForgeStrategyPanel/);
  assert.doesNotMatch(studioSource, /<ForgeResultModal/);
  assert.match(studioSource, /<PublishConfirmModal/);
  assert.doesNotMatch(studioSource, /window\.confirm/);
  assert.match(studioSource, /NiceModal\.show\(GlobalProcessModal/);
  assert.match(studioSource, /progressKind: "publish"/);
  assert.match(studioSource, /phase: "processing"/);
  assert.match(studioSource, /phase: "complete"/);
  assert.match(studioSource, /NiceModal\.show\(GlobalInfoModal/);
  assert.match(studioSource, /eyebrow: "NFT MINTED"/);
  assert.match(studioSource, /celebrate: true/);
  assert.match(studioSource, /celebrationDurationMs: 4_000/);
  assert.match(studioSource, /router\.push\("\/collections"\)/);
  assert.doesNotMatch(studioSource, /router\.push\(`\/item\//);
  assert.match(studioSource, /NFT 发行判定未通过/);
  assert.match(studioSource, /返回创作台重试/);
  assert.match(publishConfirmModalSource, /role="dialog"/);
  assert.match(publishConfirmModalSource, /aria-modal="true"/);
  assert.match(publishConfirmModalSource, /确认发行这件作品/);
  assert.match(publishConfirmModalSource, /本次判定消耗/);
  assert.match(publishConfirmModalSource, /获得 1 个 Memory Fragment/);
  assert.doesNotMatch(studioSource, /sendMessage\("生成图片"\)/);
  assert.match(studioSource, /NFT 展厅/);
  assert.match(studioSource, /VERSION CABINET/);
  assert.match(studioSource, /uploadCabinetImage/);
  assert.match(studioSource, /上传图片/);
  assert.match(studioSource, /\/nft\/creations\/agent\/analyze-upload/);
  const selectVersionRequestBlock = studioSource.slice(
    studioSource.indexOf("const selectVersion"),
    studioSource.indexOf("useEffect(() => {", studioSource.indexOf("const selectVersion")),
  );
  assert.match(selectVersionRequestBlock, /api\.get<NftForgeSession>\(`\/nft\/forge\/\$\{version\.forge\.id\}`\)/);
  assert.doesNotMatch(selectVersionRequestBlock, /forge\/analyze|\/strategy/);
  assert.match(studioSource, /setSelectedVersionId\(pendingVersionId\)/);
  assert.ok(
    studioSource.indexOf("setSelectedVersionId(pendingVersionId)")
      < studioSource.indexOf('api.post<NftUploadedImageAnalysis>('),
  );
  assert.match(studioSource, /AI 五维评分和发行建议/);
  assert.match(studioSource, /TOOL TRACE/);
  assert.match(studioSource, />STATE</);
  assert.match(studioSource, /src="\/video\/bg\.mp4"/);
  assert.match(studioSource, /<NftVisualTemplateModal/);
  const loadStudioStateBlock = studioSource.slice(
    studioSource.indexOf("const loadStudioState"),
    studioSource.indexOf("const openTemplateLibrary"),
  );
  const openTemplateLibraryBlock = studioSource.slice(
    studioSource.indexOf("const openTemplateLibrary"),
    studioSource.indexOf("const selectTemplate"),
  );
  assert.doesNotMatch(loadStudioStateBlock, /\/nft\/creations\/agent\/templates/);
  assert.match(openTemplateLibraryBlock, /\/nft\/creations\/agent\/templates/);
  assert.match(studioSource, /defaultTemplateId = "concert"/);
  assert.match(studioSource, /点击后加载模板和参考图/);
  assert.match(templateModalSource, /resetCreateForm\(\)/);
  assert.match(templateModalSource, /className=\{styles\.referenceUpload\}/);
  assert.match(studioSource, /<MarkdownEditor/);
  assert.match(studioSource, /story_image_urls: descriptionImages/);
  assert.match(studioSource, /Agent 会按故事状态调用模板、保存和图片生成工具/);
  assert.match(studioSource, /result\.image_generated && result\.draft\.image_data_url/);
  assert.match(studioSource, /MEMORY FORGE/);
  assert.match(studioSource, /发行成功率/);
  assert.match(studioSource, /strategyTooltip/);
  assert.match(studioSource, /role="alert"/);
  assert.match(studioSource, /关闭发行参数错误提示/);
  assert.match(studioSource, /forgeStrategyTooltipText\(apiErrorMessage\(error/);
  assert.match(studioStyleSource, /\.strategyTooltip\s*\{/);
  const strategySyncBlock = studioSource.slice(
    studioSource.indexOf("useEffect(() => {", studioSource.indexOf("const selectVersion")),
    studioSource.indexOf("const uploadReferences"),
  );
  assert.match(studioSource, /const lastStrategyRequestRef = useRef<string \| null>\(null\)/);
  assert.match(strategySyncBlock, /lastStrategyRequestRef\.current === strategyRequestKey/);
  assert.match(strategySyncBlock, /lastStrategyRequestRef\.current = strategyRequestKey/);
  assert.doesNotMatch(studioSource, /Perfect/);
  const selectTemplateBlock = studioSource.slice(
    studioSource.indexOf("const selectTemplate"),
    studioSource.indexOf("const sendMessage"),
  );
  assert.match(selectTemplateBlock, /setInput\(`使用视觉模板「\$\{template\.name\}」：\$\{template\.prompt\}`\)/);
  assert.doesNotMatch(selectTemplateBlock, /setInput\(\(current\)/);
  assert.ok(
    studioSource.indexOf(`/nft/forge/${"${preparedForge.id}"}/${"${endpoint}"}`)
      < studioSource.indexOf('api.post<FanNftCreateResponse>("/nft/creations"'),
  );

  assert.match(templateModalSource, /视觉模板库/);
  assert.match(templateModalSource, /从 Post 选择/);
  assert.match(templateModalSource, /从 NFT 选择/);
  assert.match(templateModalSource, /PAGE_SIZE = 6/);
  assert.match(templateModalSource, /POST_PAGE_SIZE = 8/);
  assert.match(templateModalSource, /pageItems\(posts, POST_PAGE_SIZE\)/);
  assert.match(templateModalSource, /total=\{posts\.length\} pageSize=\{POST_PAGE_SIZE\}/);
  assert.match(templateModalSource, /\/nft\/me\/creations/);
  assert.match(templateModalSource, /\/nft\/me/);
  assert.match(templateModalSource, /\/community\/posts\?limit=50&sort=latest/);
  assert.match(templateModalSource, /reference_image_urls: referenceUrls/);
  assert.match(templateModalSource, /source_post_id: selectedPost\?\.id/);
  assert.match(templateModalSource, /uploadImage\(file\)/);
  assert.match(templateModalSource, /preview_image_url/);
  assert.equal((templateModalSource.match(/className=\{styles\.masonryGrid\}/g) ?? []).length, 3);
  assert.equal((templateModalSource.match(/<MasonryImage /g) ?? []).length, 3);
  assert.match(templateModalStyles, /\.masonryGrid\{column-count:3/);
  assert.match(templateModalStyles, /\.masonryImage\{display:block;width:100%;height:auto;object-fit:contain\}/);
  assert.doesNotMatch(templateModalStyles, /\.postImage\{[^}]*aspect-ratio/);
});

test("fan NFT marketplace has category tabs", () => {
  const marketSource = readFileSync(
    new URL("../components/nft/FanNftMarket.tsx", import.meta.url),
    "utf8",
  );

  assert.match(marketSource, /type NftCategory/);
  assert.match(marketSource, /web3-page-shell min-h-screen pb-24 pt-28 md:pt-32/);
  assert.match(marketSource, /variant === "drawer" \? "mx-auto max-w-7xl px-5 pt-16 md:px-8 md:pt-14" : "mx-auto max-w-7xl px-5 pt-12"/);
  assert.match(marketSource, /h-8 w-8 animate-spin rounded-full border-2 border-accent\/20 border-t-accent/);
  assert.match(marketSource, /community-reveal overflow-hidden/);
  assert.match(marketSource, /animationDelay: `\$\{Math\.min\(index, 12\) \* 55\}ms`/);
  assert.match(marketSource, /推荐/);
  assert.match(marketSource, /共创/);
  assert.match(marketSource, /故事/);
  assert.match(marketSource, /音乐/);
  assert.match(marketSource, /讨论/);
  assert.match(marketSource, /我的收藏/);
  assert.match(marketSource, /itemMatchesCategory/);
  assert.match(marketSource, /aria-label="NFT 分类"/);
  assert.match(marketSource, /border-b-2 px-0\.5 py-3/);
  assert.match(marketSource, /web3-action-button shrink-0 rounded-full/);
  assert.match(marketSource, /ON-CHAIN EXHIBITION HALL/);
  assert.match(marketSource, /COLLECTION CABINET/);
  assert.match(marketSource, /Gallery 链路状态/);
  assert.match(marketSource, /styles\.cardWall/);
  assert.match(marketSource, /styles\.cardScan/);
  assert.match(marketSource, /styles\.authorLine/);
  assert.match(marketSource, /styles\.authorLevel/);
  assert.doesNotMatch(marketSource, /ml-11 text-xs text-jacarta-400/);
  assert.match(marketSource, /function NftCard/);
  assert.match(marketSource, /onLike: \(item: FanNftListing\) => void/);
  assert.match(marketSource, /onOpen: \(item: FanNftListing\) => void/);
  assert.match(marketSource, /aria-label=\{item\.liked \? "取消点赞 NFT" : "点赞 NFT"\}/);
  assert.match(marketSource, /api\.post<FanNftEngagement>\(`\/nft\/creations\/\$\{target\.id\}\/like`\)/);
  assert.equal(marketSource.includes(">查看</Link>"), false);
  assert.doesNotMatch(marketSource, /Fanora NFT Market/);
});

test("collections opens NFT details in a history-backed bottom drawer", () => {
  const marketSource = readFileSync(
    new URL("../components/nft/FanNftMarket.tsx", import.meta.url),
    "utf8",
  );

  assert.match(marketSource, /window\.history\.pushState\(\{ nftDrawer: true, itemId: target\.id \}/);
  assert.match(marketSource, /`\/item\/\$\{target\.id\}`/);
  assert.match(marketSource, /aria-label="NFT 详情"/);
  assert.match(marketSource, /backdrop-blur-md/);
  assert.match(marketSource, /min-h-\[95dvh\]/);
  assert.match(marketSource, /<FanNftMarket mode="item" itemId=\{selectedItemId\} variant="drawer"/);
  assert.match(marketSource, /window\.history\.back\(\)/);
  assert.match(marketSource, /event\.currentTarget\.blur\(\)/);
  assert.match(marketSource, /useLayoutEffect/);
  assert.match(marketSource, /drawerScrollRef\.current\.scrollTop = 0/);
});

test("NFT Gallery loads 50 items per page near the bottom", () => {
  const marketSource = readFileSync(
    new URL("../components/nft/FanNftMarket.tsx", import.meta.url),
    "utf8",
  );

  assert.match(marketSource, /const NFT_PAGE_SIZE = 50/);
  assert.match(marketSource, /limit=\$\{NFT_PAGE_SIZE\}&offset=\$\{offset\}/);
  assert.match(marketSource, /IntersectionObserver/);
  assert.match(marketSource, /rootMargin: "600px 0px"/);
  assert.match(marketSource, /loadingItems\.current/);
  assert.match(marketSource, /loadMoreSentinel/);
  assert.match(marketSource, /已经浏览完全部 NFT/);
});

test("item detail image uses height-matched PhotoSwipe preview", () => {
  const marketSource = readFileSync(
    new URL("../components/nft/FanNftMarket.tsx", import.meta.url),
    "utf8",
  );

  assert.match(marketSource, /react-photoswipe-gallery/);
  assert.match(marketSource, /<Gallery options=\{itemImageGalleryOptions\} withCaption>/);
  assert.match(marketSource, /<Item<HTMLButtonElement>/);
  assert.match(marketSource, /showHideAnimationType: "fade"/);
  assert.match(marketSource, /md:items-stretch/);
  assert.match(marketSource, /h-full min-h-\[400px\] w-full/);
  assert.match(marketSource, /onClick=\{open\}/);
  assert.match(marketSource, /返回 Gallery/);
  assert.match(marketSource, /router\.back\(\)/);
  assert.match(marketSource, /mode === "item" && item && !loading \? \(\s*<div className="community-reveal">/);
});

test("fan NFT details render markdown story and extracted image gallery", () => {
  const marketSource = readFileSync(
    new URL("../components/nft/FanNftMarket.tsx", import.meta.url),
    "utf8",
  );

  assert.match(marketSource, /import MarkdownContent/);
  assert.match(marketSource, /import ImageGallery/);
  assert.match(marketSource, /function extractMarkdownImageUrls/);
  assert.match(marketSource, /function stripMarkdown/);
  assert.match(marketSource, /<MarkdownContent content=\{item\.description\}/);
  assert.match(marketSource, /item\.story_image_urls/);
  assert.match(marketSource, /<ImageGallery images=\{storyImages\}/);
});

test("NFT surfaces use restrained pointer tilt and selective verified highlights", () => {
  const marketSource = readFileSync(
    new URL("../components/nft/FanNftMarket.tsx", import.meta.url),
    "utf8",
  );
  const collectionSource = readFileSync(
    new URL("../components/collection/CollectionDashboard.tsx", import.meta.url),
    "utf8",
  );
  const motionSource = readFileSync(
    new URL("../components/nft/nftMotion.ts", import.meta.url),
    "utf8",
  );

  assert.match(motionSource, /\(\(x - 0\.5\) \* 6\)/);
  assert.match(motionSource, /--nft-glare-opacity/);
  assert.match(marketSource, /nft-tilt-surface/);
  assert.match(marketSource, /selected=\{selectedItemId === entry\.id\}/);
  assert.match(marketSource, /verified=\{Boolean\(item\.contract_address/);
  assert.match(collectionSource, /chainVerified \? "nft-flow-border"/);
  assert.match(collectionSource, /confirmed \? "nft-flow-border/);
});

test("chain transactions connect nodes and resolve into NFT or identity artifacts", () => {
  const marketSource = readFileSync(new URL("../components/nft/FanNftMarket.tsx", import.meta.url), "utf8");
  const collectionSource = readFileSync(new URL("../components/collection/CollectionDashboard.tsx", import.meta.url), "utf8");
  const progressSource = readFileSync(new URL("../components/nft/ChainTransactionProgress.tsx", import.meta.url), "utf8");

  assert.match(progressSource, /提交发布.*写入 IPFS.*合约铸造.*链上确认/);
  assert.match(progressSource, /const STEP_INTERVAL_MS = 1_000/);
  assert.match(progressSource, /}, STEP_INTERVAL_MS\);/);
  assert.match(progressSource, /chain-transaction-link/);
  assert.match(progressSource, /chain-transaction-artifact/);
  assert.match(marketSource, /progressKind: "publish"/);
  assert.match(marketSource, /progressKind: "mint"/);
  assert.match(marketSource, /await hideGlobalProcessModal\(\)/);
  assert.match(marketSource, /celebrate: true/);
  assert.match(marketSource, /celebrationDurationMs: 4_000/);
  assert.doesNotMatch(marketSource, /<ChainTransactionProgress/);
  assert.match(collectionSource, /progressKind: "identity"/);
  assert.match(collectionSource, /progressKind: "member-card"/);
  assert.match(collectionSource, /NiceModal\.show\(GlobalInfoModal/);
  assert.doesNotMatch(collectionSource, /<ChainTransactionProgress/);
});

test("global process modal close cannot deadlock the success flow", () => {
  const hideBlock = globalProcessModalSource.slice(
    globalProcessModalSource.indexOf("export async function hideGlobalProcessModal"),
    globalProcessModalSource.indexOf("export default GlobalProcessModal"),
  );
  assert.doesNotMatch(hideBlock, /await NiceModal\.hide/);
  assert.match(hideBlock, /void NiceModal\.hide/);
  assert.match(hideBlock, /await new Promise/);
  assert.match(hideBlock, /NiceModal\.remove/);
});

test("NFT success modals are not delayed by profile refreshes", () => {
  const marketSource = readFileSync(new URL("../components/nft/FanNftMarket.tsx", import.meta.url), "utf8");
  const publishStart = marketSource.indexOf('api.post<FanNftCreateResponse>("/nft/creations"');
  const purchaseStart = marketSource.indexOf("api.post<FanNftPurchaseResponse>");
  const publishBlock = marketSource.slice(publishStart, marketSource.indexOf("} catch", publishStart));
  const purchaseBlock = marketSource.slice(purchaseStart, marketSource.indexOf("} catch", purchaseStart));

  assert.ok(publishBlock.indexOf("void refreshUser().catch") < publishBlock.indexOf("NiceModal.show(GlobalInfoModal"));
  assert.ok(publishBlock.indexOf("void hideGlobalProcessModal().catch") < publishBlock.indexOf("NiceModal.show(GlobalInfoModal"));
  assert.doesNotMatch(purchaseBlock, /await NiceModal\.show\(GlobalInfoModal/);
  assert.ok(purchaseBlock.indexOf("setBusy(null)") < purchaseBlock.indexOf("NiceModal.show(GlobalInfoModal"));
  assert.ok(purchaseBlock.indexOf('phase: "complete"') < purchaseBlock.indexOf("NiceModal.show(GlobalInfoModal"));
  assert.ok(purchaseBlock.indexOf("void hideGlobalProcessModal().catch") < purchaseBlock.indexOf("NiceModal.show(GlobalInfoModal"));
});

test("NFT purchase errors appear in a dismissible tooltip", () => {
  const marketSource = readFileSync(new URL("../components/nft/FanNftMarket.tsx", import.meta.url), "utf8");
  const buyStart = marketSource.indexOf("const buy = async () =>");
  const buyEnd = marketSource.indexOf("const toggleEngagement", buyStart);
  const buyBlock = marketSource.slice(buyStart, buyEnd);

  assert.match(marketSource, /You already own the creator side of this NFT/);
  assert.match(marketSource, /已经拥有创作者侧资产，无需重复购买/);
  assert.match(buyBlock, /showPurchaseTooltip\(purchaseErrorText\(error\)\)/);
  assert.match(marketSource, /role="alert"/);
  assert.match(marketSource, /关闭购买错误提示/);
  assert.match(marketSource, /6_000/);
});

test("successful NFT publishing unlocks and closes the composer before showing the acquired modal", () => {
  const marketSource = readFileSync(new URL("../components/nft/FanNftMarket.tsx", import.meta.url), "utf8");
  const publishStart = marketSource.indexOf('api.post<FanNftCreateResponse>("/nft/creations"');
  const publishEnd = marketSource.indexOf("} catch", publishStart);
  const publishBlock = marketSource.slice(publishStart, publishEnd);
  const successModalIndex = publishBlock.indexOf("NiceModal.show(GlobalInfoModal");

  assert.ok(publishStart >= 0 && successModalIndex > 0);
  assert.doesNotMatch(publishBlock, /await NiceModal\.show\(GlobalInfoModal/);
  assert.doesNotMatch(publishBlock, /await hideGlobalProcessModal\(\)/);
  assert.ok(publishBlock.indexOf("setBusy(false)") < successModalIndex);
  assert.ok(publishBlock.indexOf("onPublished(response.data.listing)") < successModalIndex);
  assert.ok(publishBlock.indexOf('name: "", description: "", theme: "", image_data_url: ""') < successModalIndex);
});

test("acquired NFT and membership card images preserve source aspect ratio over blurred backdrops", () => {
  assert.match(globalInfoModalSource, /reward-modal-backdrop/);
  assert.match(globalInfoModalSource, /reward-modal-image object-contain/);
  assert.match(styleSource, /\.reward-modal-backdrop[\s\S]*filter: blur/);
  assert.match(styleSource, /\.membership-card-backdrop[\s\S]*filter: blur/);
  assert.match(source, /membership-card-backdrop object-cover/);
  assert.match(source, /membership-card-image \$\{identity\?\.is_member_card && identity\?\.image_url \? "object-contain" : "object-cover"\}/);
});
