export interface Article {
  id?: number;
  title: string;
  source: string;
  publishedAt: string;
  url: string;
  sentiment: string;
  ticker: string;
  summary: string;
  whyMatters?: string;
  topics: string[];
  rank?: number;
}

export interface MetricItem {
  label: string;
  value: string | number;
}

export interface TopicItem {
  topic: string;
  count: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ComponentArgs {
  view: string;
  bedrock?: boolean;
  bedrockLabel?: string;
  bedrockKind?: string;
  pending?: number;
  vectorCount?: number;
  articleCount?: number;
  metrics?: MetricItem[];
  metricItems?: MetricItem[];
  embedded?: boolean;
  sentiment?: Record<string, number>;
  topics?: TopicItem[];
  articles?: Article[];
  messages?: ChatMessage[];
  answer?: string;
  sources?: string[];
  evidence?: Article[];
  placeholder?: string;
  examples?: string[];
  height?: number;
  bedrockConfigured?: boolean;
  summarizeFailed?: boolean;
}
