import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const navSource = readFileSync(new URL("../components/headers/component/Nav.tsx", import.meta.url), "utf8");
const hubSource = readFileSync(new URL("../components/community/CommunityHub.tsx", import.meta.url), "utf8");
const checkInCalendarSource = readFileSync(new URL("../components/community/CheckInCalendar.tsx", import.meta.url), "utf8");
const postSource = readFileSync(new URL("../components/community/PostDetail.tsx", import.meta.url), "utf8");
const imageGallerySource = readFileSync(new URL("../components/community/ImageGallery.tsx", import.meta.url), "utf8");
const commentPhotoGallerySource = readFileSync(new URL("../components/community/CommentPhotoGallery.tsx", import.meta.url), "utf8");
const taskGallerySource = readFileSync(new URL("../components/community/TaskGallery.tsx", import.meta.url), "utf8");
const leaderboardSource = readFileSync(new URL("../components/community/FanTokenLeaderboard.tsx", import.meta.url), "utf8");
const creationWallSource = readFileSync(new URL("../components/community/CreationWall.tsx", import.meta.url), "utf8");
const taskCatalogSource = readFileSync(new URL("../data/fanora.ts", import.meta.url), "utf8");
const fearTicketSource = readFileSync(new URL("../components/community/FearAndDreamsTicket.tsx", import.meta.url), "utf8");
const globalInfoModalSource = readFileSync(new URL("../components/modals/GlobalInfoModal.tsx", import.meta.url), "utf8");
const globalProcessModalSource = readFileSync(new URL("../components/modals/GlobalProcessModal.tsx", import.meta.url), "utf8");
const providerSource = readFileSync(new URL("../components/providers/Web3Provider.tsx", import.meta.url), "utf8");
const transactionProgressSource = readFileSync(new URL("../components/nft/ChainTransactionProgress.tsx", import.meta.url), "utf8");
const markdownEditorSource = readFileSync(new URL("../components/community/MarkdownEditor.tsx", import.meta.url), "utf8");
const markdownContentSource = readFileSync(new URL("../components/community/MarkdownContent.tsx", import.meta.url), "utf8");
const coverFlowSource = readFileSync(new URL("../components/homes/home/CoverFlowSlider.tsx", import.meta.url), "utf8");
const collectionsSource = readFileSync(new URL("../components/homes/common/Collections.tsx", import.meta.url), "utf8");
const homeSource = readFileSync(new URL("../app/(homes)/home/page.tsx", import.meta.url), "utf8");
const footerSource = readFileSync(new URL("../components/footer/Footer1.tsx", import.meta.url), "utf8");
const identityLinkSource = readFileSync(new URL("../components/profile/UserIdentityLink.tsx", import.meta.url), "utf8");
const publicProfileSource = readFileSync(new URL("../components/profile/PublicCollectionDashboard.tsx", import.meta.url), "utf8");
const nftMarketSource = readFileSync(new URL("../components/nft/FanNftMarket.tsx", import.meta.url), "utf8");
const fanProfileSummarySource = readFileSync(new URL("../components/profile/FanProfileSummary.tsx", import.meta.url), "utf8");
const confettiSource = readFileSync(new URL("../lib/ui/confetti.ts", import.meta.url), "utf8");
const stylesSource = readFileSync(new URL("../public/styles/style.css", import.meta.url), "utf8");

test("header exposes the on-chain community and its requested modules", () => {
  assert.match(navSource, /href: "\/community\/creations"/);
  assert.match(navSource, /\/community#check-in/);
  assert.match(navSource, /\/community\/tasks/);
  assert.match(navSource, /\/community\/creations/);
});

test("community hub connects check-in and tasks, then routes creation to the full editor", () => {
  assert.match(hubSource, /api\.post<DailyCheckInStatus>\("\/check-ins"\)/);
  assert.match(hubSource, /`\/tasks\/\$\{task\.id\}\/claim`/);
  assert.match(hubSource, /task\.presentation\.action_url/);
  assert.match(hubSource, /catalog\?\.actionHref/);
  assert.match(hubSource, /router\.push\(taskPreview\(response\.data\)\.actionUrl\)/);
  assert.doesNotMatch(
    hubSource,
    /const taskAction = claimed \|\| rewarded\s*\? `\/community\/posts\/\$\{task\.target_post_id\}`/,
  );
  assert.match(hubSource, /href="\/community\/creations\?composer=1"/);
  assert.match(hubSource, /href="\/community\/leaderboard"/);
  assert.match(hubSource, /<CheckInCalendar checkIn=\{checkIn\}/);
  assert.match(checkInCalendarSource, /monthly_reward_fan_tokens/);
  assert.match(checkInCalendarSource, /monthly_records/);
  assert.match(checkInCalendarSource, /grid-cols-7/);
  assert.match(hubSource, /community-section-enter/);
  assert.match(hubSource, /community-list-item/);
  assert.doesNotMatch(hubSource, /showComposer/);
});

test("community exposes a Fan Token leaderboard powered by the public API", () => {
  assert.match(leaderboardSource, /\/fan-tokens\/leaderboard\?limit=10/);
  assert.match(leaderboardSource, /leaders\.slice\(0, 3\)/);
  assert.match(leaderboardSource, /leaders\.slice\(3\)/);
  assert.match(leaderboardSource, /\/users\/\$\{leader\.user_id\}/);
  assert.match(leaderboardSource, /FanTokenAmount amount=\{leader\.fan_token_balance\}/);
});

test("replying to a post refreshes automatic task completion and Fan Token state", () => {
  assert.match(postSource, /`\/community\/posts\/\$\{postId\}\/replies`/);
  assert.match(postSource, /participation_status === "claimed"/);
  assert.match(postSource, /refreshUser\(\)/);
  assert.match(postSource, /\[load, user\?\.id\]/);
});

test("separate task and creation pages expose gallery and masonry layouts", () => {
  assert.match(taskGallerySource, /lg:grid-cols-3/);
  assert.match(taskGallerySource, /community-task-card/);
  assert.match(taskGallerySource, /--community-item-delay/);
  assert.match(creationWallSource, /sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4/);
  assert.match(creationWallSource, /masonryColumns/);
  assert.match(creationWallSource, /POST_PAGE_SIZE = 25/);
  assert.match(creationWallSource, /offset=\$\{offset\}/);
  assert.match(creationWallSource, /IntersectionObserver/);
  assert.match(creationWallSource, /rootMargin: "600px 0px"/);
});

test("creation details open as a dismissible 3D letter drawer over the wall", () => {
  assert.match(creationWallSource, /import PostDetail from/);
  assert.match(creationWallSource, /window\.history\.pushState/);
  assert.match(creationWallSource, /\/community\/posts\/\$\{postId\}/);
  assert.match(creationWallSource, /backdrop-blur-md/);
  assert.match(creationWallSource, /items-end justify-center/);
  assert.doesNotMatch(creationWallSource, /border border-white\/20 bg-\[#111538\]/);
  assert.match(creationWallSource, /event\.target === event\.currentTarget/);
  assert.match(creationWallSource, /<PostDetail postId=\{selectedPostId\} variant="drawer"/);
  assert.match(postSource, /variant\?: "page" \| "drawer"/);
  assert.match(postSource, /community-letter-scroll/);
  assert.doesNotMatch(postSource, /← 返回创作墙/);
});

test("portrait creation images remain fully visible on the wall and in post details", () => {
  assert.match(creationWallSource, /className="block h-auto w-full/);
  assert.doesNotMatch(creationWallSource, /post\.cover_url \? <div className=\{`relative overflow-hidden \$\{index % 3/);
  assert.match(postSource, /mode="natural"/);
  assert.doesNotMatch(postSource, /aspect-\[16\/9\]/);
  assert.match(imageGallerySource, /mode\?: "cover" \| "natural"/);
  assert.match(imageGallerySource, /autoHeight/);
  assert.match(imageGallerySource, /max-h-\[80vh\].*object-contain/);
});

test("creation interactions include likes, bookmarks and two-level comments", () => {
  assert.match(creationWallSource, /action: "like" \| "bookmark"/);
  assert.match(postSource, /parent_reply_id/);
  assert.match(postSource, /reply\.children/);
  assert.match(postSource, /\/community\/replies\/\$\{replyId\}\/like/);
  assert.match(postSource, /<CommentPhotoGallery images=\{images\}/);
  assert.match(commentPhotoGallerySource, /react-photoswipe-gallery/);
  assert.match(commentPhotoGallerySource, /h-\[150px\] w-\[150px\]/);
  assert.match(commentPhotoGallerySource, /wheelToZoom: true/);
});

test("home activities and community tasks share one extensible task catalog", () => {
  assert.match(taskCatalogSource, /export const fanTaskCatalog/);
  assert.match(taskCatalogSource, /daily_check_in/);
  assert.match(taskCatalogSource, /content_publish/);
  assert.match(taskCatalogSource, /page_action/);
  assert.match(taskCatalogSource, /recentActivities = fanTaskCatalog\.filter/);
  assert.match(taskCatalogSource, /fanMissions = fanTaskCatalog\.filter/);
  assert.match(taskGallerySource, /fanTaskCatalogByKey/);
  assert.match(taskGallerySource, /taskGalleryGroups/);
});

test("home hot content and popular missions use live community APIs", () => {
  assert.match(coverFlowSource, /\/community\/posts\?sort=hot&limit=10/);
  assert.match(coverFlowSource, /\/community\/posts\/\$\{post\.id\}/);
  assert.match(coverFlowSource, /Math\.ceil\(12 \/ posts\.length\)/);
  assert.match(coverFlowSource, /loopAdditionalSlides=\{5\}/);
  assert.match(collectionsSource, /api\.get<FanTask\[]>\("\/tasks"\)/);
  assert.match(collectionsSource, /task\.presentation\.action_url/);
  assert.match(collectionsSource, /participant_count/);
  assert.match(collectionsSource, /FANORA NFT CREATION AGENT/);
  assert.match(collectionsSource, /CYBER IDENTITY/);
  assert.match(collectionsSource, /ON-CHAIN PASSPORT/);
  assert.match(collectionsSource, /href="\/collections\/create"/);
  assert.match(collectionsSource, /walletAddress/);
  assert.match(collectionsSource, /progressRing/);
  assert.doesNotMatch(homeSource, /<Featured/);
});

test("footer exposes the current community, NFT Agent, membership, and identity routes", () => {
  assert.match(footerSource, /"\/community"/);
  assert.match(footerSource, /"\/collections\/create"/);
  assert.match(footerSource, /"\/collection"/);
  assert.match(footerSource, /"\/membership\/join"/);
  assert.match(footerSource, /"\/profile"/);
  assert.match(footerSource, /LANGGRAPH AGENT/);
  assert.doesNotMatch(footerSource, /href="#"/);
});

test("FEAR and DREAMS uses AI review and an ERC-1155 memorial ticket reward", () => {
  assert.match(fearTicketSource, /MEMORIAL PASS/);
  assert.match(fearTicketSource, /interaction_note/);
  assert.match(fearTicketSource, /`\/tasks\/\$\{task\.id\}\/complete`/);
  assert.match(fearTicketSource, /\/img\/fanora\/eason-concert\.webp/);
  assert.match(fearTicketSource, /AI 内容审核/);
  assert.match(fearTicketSource, /ERC-1155 纪念票/);
  assert.match(fearTicketSource, /nft_reward_status === "CONFIRMED"/);
  assert.match(fearTicketSource, /nft_explorer_url/);
  assert.match(fearTicketSource, /不伪造交易/);
  assert.match(providerSource, /NiceModal\.Provider/);
  assert.match(fearTicketSource, /NiceModal\.show\(GlobalInfoModal/);
  assert.match(globalInfoModalSource, /@ebay\/nice-modal-react/);
  assert.match(fearTicketSource, /NiceModal\.show\(GlobalProcessModal/);
  assert.match(fearTicketSource, /progressKind: "quest-reward"/);
  assert.match(globalProcessModalSource, /<ChainTransactionProgress/);
  assert.match(globalProcessModalSource, /fixed inset-0 z-\[1450\]/);
  assert.match(globalProcessModalSource, /NiceModal\.remove\(GlobalProcessModal\)/);
  assert.match(transactionProgressSource, /"quest-reward": \["AI 审核", "写入 IPFS", "提交铸造", "获得 NFT"]/);
  assert.match(fearTicketSource, /reward-ticket-stage/);
  assert.match(fearTicketSource, /Sealed until mint confirmed/);
  assert.match(fearTicketSource, /获得 FEAR and DREAMS 纪念票/);
  assert.match(fearTicketSource, /celebrate: true/);
  assert.match(globalInfoModalSource, /nft-tilt-surface nft-flow-border/);
  assert.match(globalInfoModalSource, /startRealisticConfetti\(celebrationDurationMs\)/);
  assert.match(globalInfoModalSource, /celebrationDurationMs = 3000/);
  assert.match(confettiSource, /const count = 1000/);
  assert.match(confettiSource, /angle: 30[\s\S]*origin: \{ x: 0\.04, y: 0\.72 \}/);
  assert.match(confettiSource, /angle: 150[\s\S]*origin: \{ x: 0\.96, y: 0\.72 \}/);
  assert.match(confettiSource, /Math\.floor\(\(count \* particleRatio\) \/ 2\)/);
  assert.match(confettiSource, /fire\(0\.25, \{ spread: 26, startVelocity: 75 \}\)/);
  assert.match(confettiSource, /fire\(0\.35, \{ spread: 100, startVelocity: 60, decay: 0\.91, scalar: 0\.8 \}\)/);
  assert.match(confettiSource, /fire\(0\.1, \{ spread: 120, startVelocity: 50, decay: 0\.92, scalar: 1\.2 \}\)/);
});

test("post publishing and replies use a blocking AI review modal and shared errors", () => {
  assert.match(creationWallSource, /NiceModal\.show\(GlobalProcessModal/);
  assert.match(creationWallSource, /\/img\/process\/cyancat\.gif/);
  assert.match(creationWallSource, /NiceModal\.show\(GlobalInfoModal/);
  assert.match(postSource, /NiceModal\.show\(GlobalProcessModal/);
  assert.match(postSource, /\/img\/process\/cyancat\.gif/);
  assert.match(postSource, /NiceModal\.show\(GlobalInfoModal/);
  assert.match(globalInfoModalSource, /tone\?: "success" \| "warning" \| "error" \| "info"/);
  assert.doesNotMatch(globalInfoModalSource, /backdrop-blur/);
  assert.match(globalProcessModalSource, /useBodyScrollLock\(modal\.visible\)/);
  assert.match(globalProcessModalSource, /pointer-events-none cursor-default/);
  assert.match(globalProcessModalSource, /border-cyan-300\/35/);
  assert.match(globalProcessModalSource, /imageUrl=\{imageUrl\} embedded/);
  assert.match(globalInfoModalSource, /border-cyan-300\/35/);
  assert.match(globalInfoModalSource, /flex w-full flex-col items-center text-center/);
  assert.match(stylesSource, /\.chain-transaction-progress\.is-embedded \{/);
  assert.match(stylesSource, /\.chain-transaction-progress\.is-embedded \{[\s\S]*?border: 0;[\s\S]*?background: transparent;/);
  assert.match(creationWallSource, /apiErrorMessage\(error/);
  assert.match(postSource, /apiErrorMessage\(error/);
});

test("fan NFT AI generation accepts a reference image and requires clicking the result to select it", () => {
  assert.match(nftMarketSource, /reference_image_data_url: referenceImageDataUrl \|\| null/);
  assert.match(nftMarketSource, /上传 AI 参考图/);
  assert.match(nftMarketSource, /点击选择作为 NFT 图片/);
  assert.match(nftMarketSource, /image_data_url: aiGeneratedImage/);
  assert.match(nftMarketSource, /showFormError\("请选择 NFT 图片"/);
  const aiButtonIndex = nftMarketSource.indexOf('{aiBusy ? "AI 生成中…" : "AI 生成草稿与图片"}');
  const aiNoticeIndex = nftMarketSource.indexOf("{aiNotice ?", aiButtonIndex);
  const generatedImageIndex = nftMarketSource.indexOf("{aiGeneratedImage ?", aiButtonIndex);
  assert.ok(aiButtonIndex >= 0 && aiNoticeIndex > aiButtonIndex && aiNoticeIndex < generatedImageIndex);
});

test("creation publishing supports Markdown, task tags and multiple images", () => {
  assert.match(creationWallSource, /<MarkdownEditor/);
  assert.match(creationWallSource, /requiredTags/);
  assert.match(creationWallSource, /tagInjectedForOpenComposer/);
  assert.match(creationWallSource, /body: draft\.body\.trim\(\)/);
  assert.match(creationWallSource, /image_urls/);
  assert.match(markdownEditorSource, /编辑/);
  assert.match(markdownEditorSource, /预览/);
  assert.match(markdownContentSource, /ReactMarkdown/);
  assert.match(markdownContentSource, /remarkGfm/);
  assert.match(postSource, /<MarkdownContent content=\{post\.body\}/);
  assert.match(postSource, /<ImageGallery images=\{postImages\}/);
  assert.match(postSource, /<CommentComposer/);
});

test("Echo, Gallery, posts, and comments expose member-card hover profiles", () => {
  assert.match(identityLinkSource, /`\/users\/\$\{author\.id\}`/);
  assert.match(identityLinkSource, /\/nft\/users\/\$\{userId\}/);
  assert.match(identityLinkSource, /createPortal/);
  assert.match(identityLinkSource, /style=\{\{ left: cardPosition\.left/);
  assert.match(identityLinkSource, /fixed z-\[1600\]/);
  assert.match(identityLinkSource, /Fanora 会员证/);
  assert.match(hubSource, /<UserIdentityLink author=\{post\.author\}/);
  assert.match(creationWallSource, /<UserIdentityLink author=\{post\.author\}/);
  assert.match(postSource, /<UserIdentityLink author=\{reply\.author\}/);
  assert.match(nftMarketSource, /<UserIdentityLink[\s\S]*author=\{item\.creator\}/);
  assert.match(publicProfileSource, /TA 发布的 NFT/);
  assert.match(publicProfileSource, /TA 的链上收藏/);
  assert.match(publicProfileSource, /\/profile\/users\/\$\{userId\}/);
  assert.match(publicProfileSource, /<FanProfileSummary/);
  assert.match(fanProfileSummarySource, /Proof of Fandom/);
});

test("community cards do not nest user profile anchors inside post anchors", () => {
  const nestedProfileLink = /<Link(?=[^>]*href=\{`\/community\/posts\/\$\{post\.id\}`\})[^>]*[^/]>(?:(?!<\/Link>)[\s\S])*<UserIdentityLink/;

  assert.doesNotMatch(hubSource, nestedProfileLink);
  assert.doesNotMatch(creationWallSource, nestedProfileLink);
});

test("community posts can link an owned NFT and open its purchase drawer", () => {
  assert.match(creationWallSource, /\/nft\/me\/creations/);
  assert.match(creationWallSource, /linked_nft_creation_id/);
  assert.match(postSource, /post\.linked_nft/);
  assert.match(postSource, /购买并铸造/);
  assert.match(postSource, /<FanNftMarket mode="item" itemId=\{itemId\} variant="drawer"/);
});
