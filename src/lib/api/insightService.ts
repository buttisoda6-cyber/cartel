import { apiClient } from "./client";

export interface InsightSummary {
  moneyAtRisk: number;
  moneyRecoverable: number;
  recommendedAction: string;
  expectedOutcome: string;
  activeCustomers: number;
  offersRun: number;
  broadcastsSent: number;
}

export interface HeuristicRule {
  name: string;
  formula: string;
  inputs: string[];
}

export interface ExpiryAlert {
  title: string;
  severity: string;
  inventory_at_risk: number;
  recommendation: string;
  predicted_revenue_recovery: number;
  predicted_waste_reduction: number;
  confidence: number;
  days_to_expiry: number;
}

export interface BroadcastPrediction {
  title: string;
  target_customers: number;
  expected_conversion_rate: number;
  expected_sales: number;
  expected_inventory_reduction: number;
  confidence: number;
}

export interface FinancialRiskItem {
  priority: string;
  product: string;
  potential_loss: number;
  potential_recovery: number;
  urgency: string;
}

export interface SlowMoverPrediction {
  title: string;
  inventory_value: number;
  recommendation: string;
  predicted_sales_lift: number;
  predicted_revenue_recovery: number;
  confidence: number;
  days_idle: number;
}

export interface OverstockPrediction {
  title: string;
  excess_units: number;
  carrying_cost_risk: number;
  recommendation: string;
  predicted_inventory_reduction: number;
  confidence: number;
}

export interface RevenueOpportunityAlert {
  title: string;
  products: string[];
  bundle_recommendation: string;
  predicted_additional_revenue: number;
  confidence: number;
}

export interface InterventionInsights {
  summary: InsightSummary;
  heuristics: HeuristicRule[];
  expiryAlerts: ExpiryAlert[];
  broadcastPrediction: BroadcastPrediction;
  financialRiskRanking: FinancialRiskItem[];
  slowMoverPredictions: SlowMoverPrediction[];
  overstockPredictions: OverstockPrediction[];
  revenueOpportunityAlerts: RevenueOpportunityAlert[];
}

export const insightService = {
  async getInterventions(): Promise<InterventionInsights> {
    return apiClient.get<InterventionInsights>("/api/insights/interventions");
  },
};
