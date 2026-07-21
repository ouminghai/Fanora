export type WalletInfo = {
  address: string;
  wallet_type: "embedded" | "external";
  provider: string | null;
  is_primary: boolean;
};

export type Community = {
  id: string;
  slug: string;
  name: string;
  description: string;
  logo_url: string;
  owner_user_id: string;
  is_public: boolean;
  joined: boolean;
};

export type FanoraUser = {
  id: string;
  display_name: string | null;
  username: string | null;
  email: string | null;
  avatar_url: string | null;
  bio: string | null;
  locale: string;
  level: string;
  is_official_member: boolean;
  official_member_since: string | null;
  fan_token_balance: number;
  fan_type: string;
  profile_visibility: "public" | "private";
  onboarding_completed: boolean;
  roles: string[];
  primary_wallet: WalletInfo;
  communities: Community[];
  created_at: string;
  updated_at: string;
};

export type AuthSession = {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  is_new_user: boolean;
  user: FanoraUser;
};

export type MembershipLevel = {
  code: string;
  name: string;
  description: string;
  rank: number;
  min_token_balance: number | null;
  max_token_balance: number | null;
  badge_image_url: string;
  is_management: boolean;
};

export type OfficialMembershipStatus = {
  status: "pending_payment" | "active";
  is_official_member: boolean;
  fee_mon: string;
  fee_wei: string;
  treasury_address: string | null;
  payment_contract_address: string | null;
  payment_id: string | null;
  chain_id: number;
  transaction_hash: string | null;
  joined_at: string | null;
  identity_nft_status: string;
};

export type OfficialCommunity = {
  id: string;
  slug: string;
  name: string;
  description: string;
  logo_url: string;
  joined: boolean;
  member_count: number;
  post_count: number;
};

export type CommunityAuthor = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  level: string;
};

export type CommunityPostSummary = {
  id: string;
  title: string;
  body_preview: string;
  cover_url: string | null;
  image_urls: string[];
  category: string;
  reply_count: number;
  like_count: number;
  bookmark_count: number;
  liked: boolean;
  bookmarked: boolean;
  author: CommunityAuthor;
  created_at: string;
  updated_at: string;
};

export type CommunityReply = {
  id: string;
  post_id: string;
  author: CommunityAuthor;
  body: string;
  image_urls: string[];
  parent_reply_id: string | null;
  like_count: number;
  liked: boolean;
  children: CommunityReply[];
  created_at: string;
};

export type CommunityPostDetail = {
  id: string;
  title: string;
  body: string;
  cover_url: string | null;
  image_urls: string[];
  category: string;
  reply_count: number;
  like_count: number;
  bookmark_count: number;
  liked: boolean;
  bookmarked: boolean;
  author: CommunityAuthor;
  replies: CommunityReply[];
  has_more_replies: boolean;
  next_replies_offset: number | null;
  created_at: string;
  updated_at: string;
};

export type PostEngagement = {
  post_id: string;
  liked: boolean;
  bookmarked: boolean;
  like_count: number;
  bookmark_count: number;
};

export type ReplyEngagement = {
  reply_id: string;
  liked: boolean;
  like_count: number;
};

export type FanTask = {
  id: string;
  title: string;
  description: string;
  task_type: string;
  status: string;
  start_at: string | null;
  end_at: string | null;
  reward_fan_tokens: number;
  target_post_id: string | null;
  target_post_title: string | null;
  required_tag: string | null;
  presentation: {
    catalog_key: string | null;
    image_url: string | null;
    category: string;
    interaction_prompt: string;
    action_url: string;
    action_label: string;
    badge_label: string | null;
    special: boolean;
  };
  participation_limit: number | null;
  participant_count: number;
  participation_status: "claimed" | "rewarded" | null;
  eligible: boolean;
  unavailable_reason: string | null;
  created_at: string;
  updated_at: string;
};

export type DailyCheckInStatus = {
  check_in_date: string;
  checked_in: boolean;
  already_checked_in: boolean;
  streak_days: number;
  reward_fan_tokens: number;
  fan_token_balance: number;
  month: string;
  monthly_records: Array<{
    check_in_date: string;
    reward_fan_tokens: number;
  }>;
  monthly_reward_fan_tokens: number;
};

export type FanTokenLedgerEntry = {
  id: string;
  delta: number;
  balance_after: number;
  source_type: string;
  source_id: string | null;
  task_id: string | null;
  description: string;
  created_at: string;
};

export type ChainOperation = {
  id: string;
  operation_type: string;
  status: string;
  transaction_hash: string | null;
  block_number: number | null;
  confirmations: number;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
};

export type MembershipIdentityNft = {
  token_id: number | null;
  level_id: number;
  level_code: string;
  metadata_version: number;
  metadata_uri: string;
  image_url: string | null;
  status: string;
  contract_address: string;
  chain_id: number;
  explorer_url: string | null;
  operation: ChainOperation | null;
};

export type CollectibleNft = {
  token_type_id: string;
  token_id: number;
  category: string;
  name: string;
  description: string;
  metadata_uri: string;
  image_url: string | null;
  amount: number;
  max_supply: number;
  minted_supply: number;
  transferable: boolean;
  status: string;
  contract_address: string;
  chain_id: number;
  explorer_url: string | null;
  operation: ChainOperation | null;
};

export type NftApplication = {
  id: string;
  name: string;
  description: string;
  theme: string;
  public_attributes: Array<{ trait_type: string; value: string }>;
  copyright_declaration: string;
  image_data_url: string | null;
  status: string;
  rejection_reason: string | null;
  metadata_version_id: string | null;
  collectible_token_type_id: string | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MyCollection = {
  chain_id: number;
  network_name: string;
  identity_sync_status: string;
  identity: MembershipIdentityNft | null;
  collectibles: CollectibleNft[];
  applications: NftApplication[];
};
