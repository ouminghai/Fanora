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
