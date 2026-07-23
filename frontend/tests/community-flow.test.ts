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
const creationWallSource = readFileSync(new URL("../components/community/CreationWall.tsx", import.meta.url), "utf8");
const taskCatalogSource = readFileSync(new URL("../data/fanora.ts", import.meta.url), "utf8");
const fearTicketSource = readFileSync(new URL("../components/community/FearAndDreamsTicket.tsx", import.meta.url), "utf8");
const markdownEditorSource = readFileSync(new URL("../components/community/MarkdownEditor.tsx", import.meta.url), "utf8");
const markdownContentSource = readFileSync(new URL("../components/community/MarkdownContent.tsx", import.meta.url), "utf8");
const coverFlowSource = readFileSync(new URL("../components/homes/home/CoverFlowSlider.tsx", import.meta.url), "utf8");
const collectionsSource = readFileSync(new URL("../components/homes/common/Collections.tsx", import.meta.url), "utf8");

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
  assert.match(hubSource, /<CheckInCalendar checkIn=\{checkIn\}/);
  assert.match(checkInCalendarSource, /monthly_reward_fan_tokens/);
  assert.match(checkInCalendarSource, /monthly_records/);
  assert.match(checkInCalendarSource, /grid-cols-7/);
  assert.match(hubSource, /community-section-enter/);
  assert.match(hubSource, /community-list-item/);
  assert.doesNotMatch(hubSource, /showComposer/);
});

test("replying to a post refreshes automatic task completion and Fan Token state", () => {
  assert.match(postSource, /`\/community\/posts\/\$\{postId\}\/replies`/);
  assert.match(postSource, /participation_status === "claimed"/);
  assert.match(postSource, /refreshUser\(\)/);
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
