import { apiClient } from "./client";

export interface AIChatResponse {
  answer: string;
  context_snapshot: string;
  intent?: string;
  report_type?: string;
  generated_at?: string;
}

export interface AIBriefResponse {
  title: string;
  answer: string;
  context_snapshot: string;
  report_type?: string;
  generated_at?: string;
}

export interface SQLAgentResponse {
  source_db?: string;
  sql?: string;
  explanation?: string;
  limit_applied?: boolean;
  generated_at?: string;
  summary?: {
    row_count: number;
    columns: string[];
  };
  rows?: Record<string, unknown>[];
  error?: string;
}

export const aiService = {
  async chat(question: string): Promise<AIChatResponse> {
    return apiClient.post<AIChatResponse>("/api/ai/chat", { question });
  },

  async morningBrief(): Promise<AIBriefResponse> {
    return apiClient.get<AIBriefResponse>("/api/ai/morning-brief");
  },

  async endOfDayBrief(): Promise<AIBriefResponse> {
    return apiClient.get<AIBriefResponse>("/api/ai/end-of-day");
  },

  async sql(question: string): Promise<SQLAgentResponse> {
    return apiClient.post<SQLAgentResponse>("/api/ai/sql", { question });
  },

  async history(limit = 20): Promise<Array<{ id: number; user_query: string; ai_response: string; created_at: string }>> {
    return apiClient.get<Array<{ id: number; user_query: string; ai_response: string; created_at: string }>>(
      `/api/ai/history?limit=${limit}`
    );
  },
};
