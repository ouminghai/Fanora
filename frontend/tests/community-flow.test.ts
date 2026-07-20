import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const navSource = readFileSync(new URL("../components/headers/component/Nav.tsx", import.meta.url), "utf8");
const hubSource = readFileSync(new URL("../components/community/CommunityHub.tsx", import.meta.url), "utf8");
const postSource = readFileSync(new URL("../components/community/PostDetail.tsx", import.meta.url), "utf8");
const taskGallerySource = readFileSync(new URL("../components/community/TaskGallery.tsx", import.meta.url), "utf8");
const creationWallSource = readFileSync(new URL("../components/community/CreationWall.tsx", import.meta.url), "utf8");
const taskCatalogSource = readFileSync(new URL("../data/fanora.ts", import.meta.url), "utf8");
const fearTicketSource = readFileSync(new URL("../components/community/FearAndDreamsTicket.tsx", import.meta.url), "utf8");
const markdownEditorSource = readFileSync(new URL("../components/community/MarkdownEditor.tsx", import.meta.url), "utf8");
const markdownContentSource = readFileSync(new URL("../components/community/MarkdownContent.tsx", import.meta.url), "utf8");

test("header exposes the official community and its three requested modules", () => {
  assert.match(navSource, /href: "\/community"/);
  assert.match(navSource, /\/community#check-in/);
  assert.match(navSource, /\/community#tasks/);
  assert.match(navSource, /\/community#creation/);
});

test("community hub connects check-in, task claim and content creation to backend APIs", () => {
  assert.match(hubSource, /api\.post<DailyCheckInStatus>\("\/check-ins"\)/);
  assert.match(hubSource, /`\/tasks\/\$\{task\.id\}\/claim`/);
  assert.match(hubSource, /api\.post<CommunityPostDetail>\("\/community\/posts", draft\)/);
});

test("replying to a post refreshes automatic task completion and Fan Token state", () => {
  assert.match(postSource, /`\/community\/posts\/\$\{postId\}\/replies`/);
  assert.match(postSource, /participation_status === "claimed"/);
  assert.match(postSource, /refreshUser\(\)/);
});

test("separate task and creation pages expose card and masonry layouts", () => {
  assert.match(taskGallerySource, /md:grid-cols-2 xl:grid-cols-3/);
  assert.match(creationWallSource, /sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4/);
  assert.match(creationWallSource, /masonryColumns/);
});

test("creation interactions include likes, bookmarks and two-level comments", () => {
  assert.match(creationWallSource, /action: "like" \| "bookmark"/);
  assert.match(postSource, /parent_reply_id/);
  assert.match(postSource, /reply\.children/);
  assert.match(postSource, /\/community\/replies\/\$\{replyId\}\/like/);
});

test("home activities and community tasks share one extensible task catalog", () => {
  assert.match(taskCatalogSource, /export const fanTaskCatalog/);
  assert.match(taskCatalogSource, /daily_check_in/);
  assert.match(taskCatalogSource, /content_publish/);
  assert.match(taskCatalogSource, /page_action/);
  assert.match(taskCatalogSource, /recentActivities = fanTaskCatalog\.filter/);
  assert.match(taskCatalogSource, /fanMissions = fanTaskCatalog\.filter/);
  assert.match(taskGallerySource, /fanTaskCatalogByKey/);
  assert.match(taskGallerySource, /全部模式/);
});

test("FEAR and DREAMS has a dedicated future-NFT task page", () => {
  assert.match(fearTicketSource, /MEMORIAL PASS/);
  assert.match(fearTicketSource, /interaction_note/);
  assert.match(fearTicketSource, /`\/tasks\/\$\{task\.id\}\/complete`/);
  assert.match(fearTicketSource, /后续可在同一页面接入 NFT 合约/);
});

test("creation publishing supports Markdown and a Base64 cover image", () => {
  assert.match(creationWallSource, /<MarkdownEditor/);
  assert.match(creationWallSource, /reader\.readAsDataURL\(file\)/);
  assert.match(creationWallSource, /首图/);
  assert.match(markdownEditorSource, /编辑/);
  assert.match(markdownEditorSource, /预览/);
  assert.match(markdownContentSource, /ReactMarkdown/);
  assert.match(markdownContentSource, /remarkGfm/);
  assert.match(postSource, /<MarkdownContent content=\{post\.body\}/);
  assert.match(postSource, /alt=\{`\$\{post\.title\}首图`\}/);
});
