/**
 * Activity Logging and Analytics API service
 */

import { apiClient } from "./client";

export interface AppUsageLog {
  id: number;
  actionType: string;
  actionDescription: string;
  offerId?: number;
  broadcastLogId?: number;
  extraData?: any;
  createdAt: string;
}

export interface OfferAnalytics {
  totalOffersApproved: number;
  totalBroadcastsSent: number;
  totalCustomersReached: number;
  averageRecipientsPerBroadcast: number;
}

export interface ActivityStats {
  actionType: string;
  count: number;
  lastAction: string;
}

export interface Last7DaysActivity {
  date: string;
  offersApproved: number;
  broadcastsSent: number;
}

export const analyticsService = {
  /**
   * Get offer analytics summary
   */
  async getOfferSummary(): Promise<OfferAnalytics> {
    return apiClient.get<OfferAnalytics>("/api/analytics/offers/summary");
  },

  /**
   * Get feature usage statistics
   */
  async getFeatureUsage(): Promise<ActivityStats[]> {
    return apiClient.get<ActivityStats[]>("/api/analytics/offers/feature-usage");
  },

  /**
   * Get activity for last 7 days
   */
  async getLast7DaysActivity(): Promise<Last7DaysActivity[]> {
    return apiClient.get<Last7DaysActivity[]>("/api/analytics/offers/activity/last-7-days");
  },

  /**
   * Get offer approval history
   */
  async getOfferHistory(limit: number = 50): Promise<any[]> {
    return apiClient.get<any[]>(`/api/analytics/offers/history?limit=${limit}`);
  },

  /**
   * Get broadcast history
   */
  async getBroadcastHistory(limit: number = 50): Promise<any[]> {
    return apiClient.get<any[]>(`/api/analytics/broadcasts/history?limit=${limit}`);
  },

  /**
   * Get recent activity logs
   */
  async getRecentActivity(
    actionType?: string,
    limit: number = 50
  ): Promise<AppUsageLog[]> {
    const url = actionType
      ? `/api/analytics/activity/recent?action_type=${actionType}&limit=${limit}`
      : `/api/analytics/activity/recent?limit=${limit}`;
    return apiClient.get<AppUsageLog[]>(url);
  },
};
