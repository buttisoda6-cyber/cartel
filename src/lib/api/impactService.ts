import { apiClient } from "./client";

export interface InterventionRecord {
  id: number;
  recommendation_key: string;
  product_id?: number | null;
  product_name: string;
  category_name?: string | null;
  intervention_type: string;
  recommendation_reason: string;
  recommended_discount_type?: string | null;
  recommended_discount_value?: number | null;
  recommended_action?: string | null;
  merchant?: string | null;
  status: string;
  generated_at: string;
  viewed_at?: string | null;
  approved_at?: string | null;
  executed_at?: string | null;
  action_performed?: string | null;
  notes?: string | null;
  stock_before?: number | null;
  stock_after?: number | null;
  units_sold_before?: number | null;
  units_sold_after?: number | null;
  revenue_before?: number | null;
  revenue_after?: number | null;
  estimated_revenue_recovered?: number | null;
  estimated_loss_avoided?: number | null;
  sales_velocity_before?: number | null;
  sales_velocity_after?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ImpactMetrics {
  generatedRecommendations: number;
  viewedRecommendations: number;
  approvedRecommendations: number;
  executedRecommendations: number;
  estimatedRevenueRecovered: number;
  estimatedLossAvoided: number;
  deadStockReduced: number;
  inventoryCleared: number;
  avgSalesVelocityImprovement: number;
}

export interface ImpactReportItem {
  label: string;
  generatedRecommendations: number;
  approvedRecommendations: number;
  executedRecommendations: number;
  estimatedRevenueRecovered: number;
  estimatedLossAvoided: number;
  deadStockReduced: number;
  inventoryCleared: number;
  avgSalesVelocityImprovement: number;
}

export interface ApproveRequest {
  recommendationKey: string;
  merchant?: string;
  actionPerformed?: string;
  notes?: string;
}

export interface ExecuteRequest {
  recommendationKey: string;
  merchant?: string;
  actionPerformed?: string;
  notes?: string;
}

export interface RefreshStatus {
  status: "idle" | "running" | "refresh_started" | "already_running" | "completed" | "failed";
  error?: string | null;
  startedAt?: string | null;
  completedAt?: string | null;
}

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 120;

export const impactService = {
  /** Read cached recommendations from SQLite only. */
  async getRecommendations(): Promise<InterventionRecord[]> {
    return apiClient.get<InterventionRecord[]>("/api/impact/recommendations");
  },

  /** Start background regeneration; returns immediately. */
  async startRefresh(): Promise<RefreshStatus> {
    return apiClient.post<RefreshStatus>("/api/impact/recommendations/refresh", {});
  },

  async getRefreshStatus(): Promise<RefreshStatus> {
    return apiClient.get<RefreshStatus>("/api/impact/recommendations/refresh/status");
  },

  async waitForRefreshComplete(): Promise<RefreshStatus> {
    for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt += 1) {
      const status = await this.getRefreshStatus();
      if (status.status === "completed" || status.status === "idle") {
        return status;
      }
      if (status.status === "failed") {
        throw new Error(status.error || "Recommendation refresh failed");
      }
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    }
    throw new Error("Recommendation refresh timed out");
  },

  async approve(payload: ApproveRequest): Promise<InterventionRecord> {
    return apiClient.post<InterventionRecord>("/api/impact/approve", payload);
  },

  async execute(payload: ExecuteRequest): Promise<InterventionRecord> {
    return apiClient.post<InterventionRecord>("/api/impact/execute", payload);
  },

  async overview(): Promise<ImpactMetrics> {
    return apiClient.get<ImpactMetrics>("/api/impact/overview");
  },

  async weeklyReport(): Promise<ImpactReportItem[]> {
    return apiClient.get<ImpactReportItem[]>("/api/impact/reports/weekly");
  },

  async monthlyReport(): Promise<ImpactReportItem[]> {
    return apiClient.get<ImpactReportItem[]>("/api/impact/reports/monthly");
  },
};
