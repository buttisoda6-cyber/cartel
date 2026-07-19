/**
 * Analytics API service
 */

import { apiClient } from "./client";

export interface DailySales {
  day: string;
  value: number;
}

export interface PaymentMix {
  name: string;
  value: number;
  color: string;
}

export interface Mover {
  name: string;
  qty: number;
}

export interface Analytics {
  dailySales: DailySales[];
  paymentMix: PaymentMix[];
  fastMovers: Mover[];
  slowMovers: Mover[];
}

export const analyticsService = {
  /**
   * Get analytics data
   */
  async get(): Promise<Analytics> {
    return apiClient.get<Analytics>("/api/analytics");
  },
};
