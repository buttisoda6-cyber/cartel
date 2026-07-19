import { apiClient } from "./client";

export interface AdminAnalyticsSummary {
  window_days: number;
  registered_merchants: number;
  daily_active_users: number;
  weekly_active_users: number;
  monthly_active_users: number;
  login_frequency: number;
  average_session_duration_minutes: number;
  average_engagement_time_minutes: number;
  session_duration_by_user: number;
  most_visited_pages: Array<{ page: string; count: number }>;
  most_clicked_features: Array<{ action_type: string; count: number }>;
  page_time_spent: Array<{ page: string; minutes: number }>;
  ai_chat_usage: number;
  reports_generated: number;
  recommendation_approval_rate: number;
  recommendation_conversion_rate: number;
  returning_users: number;
  last_active_timestamp?: string | null;
}

export interface AdminAnalyticsReport {
  generated_at: string;
  summary: AdminAnalyticsSummary;
  weekly_snapshots: AdminAnalyticsSummary[];
  recent_logins: Array<{
    username: string;
    login_time: string;
    logout_time?: string | null;
    device_info?: string | null;
    ip_address?: string | null;
  }>;
  recent_activity: Array<{
    action_type: string;
    action_description: string;
    created_at: string;
    extra_data?: any;
  }>;
}

export const adminAnalyticsService = {
  async getAnalytics(): Promise<AdminAnalyticsReport> {
    return apiClient.get<AdminAnalyticsReport>("/api/admin/analytics");
  },

  async exportCsv(): Promise<{ csv: string; generated_at: string }> {
    return apiClient.get<{ csv: string; generated_at: string }>("/api/admin/analytics/export");
  },
};
