import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(
  new URL("../components/collection/CollectionDashboard.tsx", import.meta.url),
  "utf8",
);
const transactionProgressSource = readFileSync(
  new URL("../components/nft/ChainTransactionProgress.tsx", import.meta.url),
  "utf8",
);

test("collection uses a profile banner, overlapping avatar, and asset tabs", () => {
  assert.match(source, /eason-concert\.webp/);
  assert.match(source, /-translate-y-1\/2/);
  assert.match(source, /community-reveal relative h-\[220px\]/);
  assert.match(source, /key=\{activeTab\}/);
  assert.match(source, /<CollectibleCard/);
  assert.match(source, /key=\{item\.token_type_id\}/);
  assert.match(source, /item=\{item\}/);
  assert.match(source, /index=\{index\}/);
  assert.match(source, /animationDelay: `\$\{Math\.min\(index, 12\) \* 55\}ms`/);
  assert.match(source, /链上身份/);
  assert.match(source, /我的收藏/);
  assert.doesNotMatch(source, /徽章申请/);
  assert.doesNotMatch(source, /\/nft\/applications/);
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

test("collection automatically creates, refreshes, reveals, and downloads a free membership card", () => {
  assert.match(source, /\/nft\/identity\/card\/refresh/);
  assert.match(source, /\/nft\/identity\/card/);
  assert.match(source, /制作会员证/);
  assert.match(source, /无需消耗 FAN/);
  assert.match(source, /autoCardSyncKeyRef/);
  assert.match(source, /identity\?\.is_member_card && !identity\.card_needs_refresh/);
  assert.match(source, /\/img\/membercard\/membercard\.jpg/);
  assert.match(source, /membership-card-stage/);
  assert.match(source, /kind="member-card"/);
  assert.match(transactionProgressSource, /"member-card": \["验证会员身份"/);
  assert.doesNotMatch(transactionProgressSource, /"member-card": \["扣除 FAN"/);
  assert.match(source, /downloadMembershipCard/);
  assert.match(source, /等级或资料已更新，点击卡面刷新会员证/);
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

test("fan NFT publishing is guarded by spendable FAN balance", () => {
  const marketSource = readFileSync(
    new URL("../components/nft/FanNftMarket.tsx", import.meta.url),
    "utf8",
  );
  const markdownEditorSource = readFileSync(
    new URL("../components/community/MarkdownEditor.tsx", import.meta.url),
    "utf8",
  );

  assert.match(marketSource, /user\.fan_token_balance < publishFeeFanTokens/);
  assert.match(marketSource, /可用 FAN 不足/);
  assert.match(marketSource, /发布费/);
  assert.match(marketSource, /function PublishModal/);
  assert.match(marketSource, /\/img\/process\/cyancat\.gif/);
  assert.match(marketSource, /正在上传图片与 metadata 到 IPFS/);
  assert.match(marketSource, /transition-opacity duration-200/);
  assert.match(marketSource, /translate-y-3 scale-95 opacity-0/);
  assert.match(marketSource, /NFT 名称/);
  assert.match(marketSource, /主题 \/ 分类/);
  assert.match(marketSource, /NFT 故事描述/);
  assert.match(marketSource, /<MarkdownEditor/);
  assert.match(markdownEditorSource, /title: "图片"/);
  assert.match(markdownEditorSource, /!\[/);
  assert.match(marketSource, /imageUrls=\{storyImageUrls\}/);
  assert.match(marketSource, /onImageUrlsChange=\{setStoryImageUrls\}/);
  assert.match(marketSource, /story_image_urls: storyImageUrls/);
  assert.match(marketSource, /版权声明/);
  assert.match(marketSource, /h-11 w-11/);
  assert.match(marketSource, /hover:bg-accent/);
  assert.match(marketSource, /place-items-center/);
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
  assert.match(progressSource, /chain-transaction-link/);
  assert.match(progressSource, /chain-transaction-artifact/);
  assert.match(marketSource, /kind="publish"/);
  assert.match(marketSource, /kind="mint"/);
  assert.match(marketSource, /setPublishPhase\("complete"\)/);
  assert.match(marketSource, /setBuyPhase\("complete"\)/);
  assert.match(collectionSource, /kind="identity"/);
  assert.match(collectionSource, /setIdentityPhase\(confirmed \? "complete"/);
});
