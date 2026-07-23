export type FanTaskMode =
  | "daily_check_in"
  | "post_reply"
  | "content_publish"
  | "page_action"
  | "streak"
  | "event_check_in"
  | "future";

export type FanTaskCatalogItem = {
  key: string;
  order: number;
  imageSrc: string;
  title: string;
  summary: string;
  meta: string;
  category: "daily" | "discussion" | "music" | "creation" | "event" | "identity" | "special";
  mode: FanTaskMode;
  fanTokenReward: number;
  rewardLabel: string | null;
  interactionPrompt: string;
  actionHref: string;
  actionLabel: string;
  missionDetail: string;
  missionStatus: "进行中" | "即将开始";
  featuredActivity?: boolean;
  featuredMission?: boolean;
  special?: boolean;
};

export const fanTaskCatalog: FanTaskCatalogItem[] = [
  {
    key: "daily-check-in", order: 1, imageSrc: "/img/fanora/activity-checkin.jpg", title: "每日 Fans Club 签到",
    summary: "每天完成一次社区签到，连续活跃还能触发七日奖励。", meta: "每日互动 · 连续签到", category: "daily", mode: "daily_check_in",
    fanTokenReward: 20, rewardLabel: null, interactionPrompt: "每天回来签到，连续 7 天还有额外奖励", actionHref: "/community#check-in", actionLabel: "去签到",
    missionDetail: "每日互动", missionStatus: "进行中", featuredMission: true,
  },
  {
    key: "fear-and-dreams", order: 2, imageSrc: "/img/fanora/activity-concert.jpg", title: "FEAR and DREAMS 纪念票任务",
    summary: "进入专属纪念页完成演唱会打卡，为后续 NFT 纪念票领取积累资格。", meta: "近期活动 · 演唱会纪念", category: "event", mode: "page_action",
    fanTokenReward: 500, rewardLabel: null, interactionPrompt: "留下你的现场记忆，激活纪念票收藏资格", actionHref: "/community/tasks/fear-and-dreams", actionLabel: "进入纪念票页面",
    missionDetail: "特别任务", missionStatus: "进行中", featuredActivity: true, featuredMission: true, special: true,
  },
  {
    key: "new-song-listening", order: 3, imageSrc: "/img/fanora/activity-music.jpg", title: "新歌连续收听 7 天",
    summary: "连续参与共听并记录每日感受，让歌单讨论持续发生。", meta: "线上活动 · 七日共听", category: "music", mode: "streak",
    fanTokenReward: 120, rewardLabel: null, interactionPrompt: "连续记录收听感受，让歌单讨论持续发生", actionHref: "/community/creations?category=music", actionLabel: "查看共听计划",
    missionDetail: "连续任务", missionStatus: "即将开始", featuredActivity: true, featuredMission: true,
  },
  {
    key: "share-your-song", order: 4, imageSrc: "/img/fanora/activity-community.jpg", title: "分享你的入坑歌曲",
    summary: "回复最初打动你的歌曲和故事，用音乐认识拥有相似记忆的粉丝。", meta: "社区互动 · 故事回复", category: "discussion", mode: "post_reply",
    fanTokenReward: 80, rewardLabel: null, interactionPrompt: "用一首歌开启交流，认识拥有相似记忆的粉丝", actionHref: "/community/posts/00000000-0000-0000-0000-000000000003", actionLabel: "去分享歌曲",
    missionDetail: "社区互动", missionStatus: "进行中", featuredMission: true,
  },
  {
    key: "fan-story", order: 5, imageSrc: "/img/fanora/activity-community.jpg", title: "粉丝故事图文征集",
    summary: "发布故事或共创内容，把长期陪伴中的真实片段沉淀在社区。", meta: "社区共创 · 投稿进行中", category: "creation", mode: "content_publish",
    fanTokenReward: 180, rewardLabel: null, interactionPrompt: "用图文沉淀粉丝记忆，也为社区贡献优质内容", actionHref: "/community/creations?composer=1", actionLabel: "发布粉丝故事",
    missionDetail: "优质内容加成", missionStatus: "进行中", featuredActivity: true, featuredMission: true,
  },
  {
    key: "anniversary-wishes", order: 6, imageSrc: "/img/fanora/activity-badge.jpg", title: "周年祝福共创",
    summary: "发布周年祝福或视觉灵感，与社区共同完成一份纪念作品。", meta: "限时活动 · 周年共创", category: "creation", mode: "content_publish",
    fanTokenReward: 150, rewardLabel: null, interactionPrompt: "共同创作周年内容，让每一份祝福被看见", actionHref: "/community/creations?composer=1", actionLabel: "参与周年共创",
    missionDetail: "限时共创", missionStatus: "进行中", featuredMission: true,
  },
  {
    key: "classic-lyrics-chain", order: 7, imageSrc: "/img/fanora/activity-music.jpg", title: "经典歌词接龙",
    summary: "回复一句歌词或下一句联想，邀请更多粉丝接力完成讨论。", meta: "社区挑战 · 歌词互动", category: "music", mode: "post_reply",
    fanTokenReward: 60, rewardLabel: null, interactionPrompt: "回复歌词并邀请下一位粉丝接龙", actionHref: "/community/posts/00000000-0000-0000-0000-000000000004", actionLabel: "去歌词接龙",
    missionDetail: "社区挑战", missionStatus: "进行中", featuredMission: true,
  },
  {
    key: "core-fan-identity", order: 8, imageSrc: "/img/fanora/activity-badge.jpg", title: "核心粉丝身份画像",
    summary: "完善粉丝资料并连接互动记录，为后续自动身份验证做准备。", meta: "身份成长 · 即将开放", category: "identity", mode: "future",
    fanTokenReward: 300, rewardLabel: null, interactionPrompt: "完善真实粉丝画像，为身份成长积累可验证记录", actionHref: "/profile", actionLabel: "查看身份画像",
    missionDetail: "身份成长", missionStatus: "即将开始", featuredMission: true,
  },
  {
    key: "city-checkin", order: 9, imageSrc: "/img/fanora/activity-checkin.jpg", title: "城市粉丝见面打卡",
    summary: "为线下活动预留定位与现场凭证验证，开放后可领取活动积分。", meta: "线下活动 · 名额有限", category: "event", mode: "event_check_in",
    fanTokenReward: 300, rewardLabel: null, interactionPrompt: "在线下相遇并留下城市粉丝活动记录", actionHref: "/community/tasks", actionLabel: "等待活动开放",
    missionDetail: "线下活动", missionStatus: "即将开始", featuredActivity: true,
  },
  {
    key: "anniversary-badge", order: 10, imageSrc: "/img/fanora/activity-badge.jpg", title: "周年限定 Badge 解锁",
    summary: "为周年链上收藏预留资格任务，当前先展示未来领取入口。", meta: "链上纪念 · 即将开放", category: "special", mode: "future",
    fanTokenReward: 100, rewardLabel: "限量 10,000 枚", interactionPrompt: "持续参与社区，为未来周年纪念收藏积累资格", actionHref: "/community/tasks", actionLabel: "查看开放进度",
    missionDetail: "限量收藏", missionStatus: "即将开始", featuredActivity: true, special: true,
  },
];

export const fanTaskCatalogByKey = new Map(fanTaskCatalog.map((task) => [task.key, task]));

export const recentActivities = fanTaskCatalog.filter((task) => task.featuredActivity).map((task) => ({
  id: task.key,
  imageSrc: task.imageSrc,
  avatarSrc: task.imageSrc,
  title: task.title,
  meta: task.meta,
  fanTokenReward: task.rewardLabel ? null : task.fanTokenReward,
  rewardLabel: task.rewardLabel,
  actionHref: task.actionHref,
}));

export const fanMissions = fanTaskCatalog.filter((task) => task.featuredMission).map((task, index) => ({
  id: index + 1,
  avatar: task.imageSrc,
  name: task.title,
  fanTokenReward: task.fanTokenReward,
  detail: task.missionDetail,
  status: task.missionStatus,
  actionHref: task.actionHref,
}));

export const fanJourney = [
  {
    id: 1,
    iconSrc: "/img/process/process5.svg",
    title: "1. 连接自有钱包",
    bgClass: "bg-accent",
    ringColor: "#CDBCFF",
    description: "通过 RainbowKit 连接 MetaMask、WalletConnect 等自有钱包，完成一次无 Gas 的登录签名。",
  },
  {
    id: 2,
    iconSrc: "/img/process/process6.svg",
    title: "2. 参与粉丝活动",
    bgClass: "bg-green",
    ringColor: "#C4F2E3",
    description: "完成签到、内容互动、演唱会打卡与社区共创等真实粉丝任务。",
  },
  {
    id: 3,
    iconSrc: "/img/process/process7.svg",
    title: "3. 积累 Fan Token",
    bgClass: "bg-blue",
    ringColor: "#CDDFFB",
    description: "任务通过服务端规则验证后发放 FAN；Agent 只分析画像和解释结果，不直接修改余额。",
  },
  {
    id: 4,
    iconSrc: "/img/process/process8.svg",
    title: "4. 沉淀链上身份",
    bgClass: "bg-red",
    ringColor: "#FFD0D0",
    description: "终身 FAN 达到门槛后刷新唯一的 ERC-721 会员身份，任务纪念品则使用 ERC-1155 记录。",
  },
];

export const fandomProfiles = [
  {
    id: "loyal-fan",
    name: "长期陪伴者",
    images: [
      "/img/fanora/activity-concert.jpg",
      "/img/fanora/activity-music.jpg",
      "/img/fanora/activity-community.jpg",
      "/img/fanora/activity-badge.jpg",
    ],
    avatar: "/img/fanora/activity-concert.jpg",
    identity: "忠诚型粉丝",
    score: "92",
  },
  {
    id: "active-fan",
    name: "现场能量担当",
    images: [
      "/img/fanora/activity-checkin.jpg",
      "/img/fanora/activity-concert.jpg",
      "/img/fanora/activity-badge.jpg",
      "/img/fanora/activity-music.jpg",
    ],
    avatar: "/img/fanora/activity-checkin.jpg",
    identity: "活跃型粉丝",
    score: "88",
  },
  {
    id: "creator-fan",
    name: "社区共创者",
    images: [
      "/img/fanora/activity-music.jpg",
      "/img/fanora/activity-community.jpg",
      "/img/fanora/activity-checkin.jpg",
      "/img/fanora/activity-concert.jpg",
    ],
    avatar: "/img/fanora/activity-music.jpg",
    identity: "贡献型粉丝",
    score: "95",
  },
  {
    id: "early-fan",
    name: "早期同行者",
    images: [
      "/img/fanora/activity-community.jpg",
      "/img/fanora/activity-badge.jpg",
      "/img/fanora/activity-concert.jpg",
      "/img/fanora/activity-checkin.jpg",
    ],
    avatar: "/img/fanora/activity-community.jpg",
    identity: "早期支持者",
    score: "90",
  },
  {
    id: "influence-fan",
    name: "粉丝传播者",
    images: [
      "/img/fanora/activity-badge.jpg",
      "/img/fanora/activity-checkin.jpg",
      "/img/fanora/activity-music.jpg",
      "/img/fanora/activity-community.jpg",
    ],
    avatar: "/img/fanora/activity-badge.jpg",
    identity: "影响力粉丝",
    score: "86",
  },
];

export const technologyPartners = [
  { id: 1, name: "Monad", detail: "Identity Layer" },
  { id: 2, name: "LangGraph", detail: "Agent Workflow" },
  { id: 3, name: "FastAPI", detail: "Backend API" },
  { id: 4, name: "Solidity", detail: "Smart Contract" },
  { id: 5, name: "viem", detail: "Web3 Client" },
];
