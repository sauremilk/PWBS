// Types shared across the PWBS mobile app (TASK-152)

export interface Briefing {
  id: string;
  briefing_type: "morning" | "meeting" | "project" | "weekly";
  title: string;
  content: string;
  sources: SourceRef[];
  created_at: string;
  word_count: number;
}

export interface SourceRef {
  title: string;
  source_type: string;
  url: string | null;
  snippet: string;
}

export interface SearchResult {
  id: string;
  title: string;
  content_preview: string;
  source_type: string;
  relevance_score: number;
  created_at: string;
}

export interface Entity {
  id: string;
  name: string;
  entity_type: "person" | "project" | "decision" | "topic";
  mention_count: number;
}

export interface QuickNote {
  id: string;
  content: string;
  source: "text" | "voice";
  created_at: string;
  synced: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_at: number;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
}

export type RootStackParamList = {
  Login: undefined;
  Main: undefined;
  BriefingDetail: { id: string };
};

export type MainTabParamList = {
  Briefings: undefined;
  Search: undefined;
  QuickNote: undefined;
  Settings: undefined;
};
