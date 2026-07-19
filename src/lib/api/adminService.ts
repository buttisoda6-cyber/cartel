/**
 * Admin Panel API Service
 */

import { apiClient } from "./client";

export interface ScreenTimeResponse {
  username: string;
  screentime_minutes: number;
  screentime_hours: number;
}

export interface ScreenTimeData {
  week_label: string;
  start_date: string;
  end_date: string;
  users: ScreenTimeResponse[];
}

export interface BroadcastPerformanceResponse {
  product_id: number;
  product_name: string;
  category: string;
  this_week_qty: number;
  usual_weekly_qty: number;
  qty_growth: number;
  this_week_rev: number;
  usual_weekly_rev: number;
  rev_growth: number;
}

export interface DailySalesResponse {
  day: string;
  date: string;
  value: number;
}

export interface OverallSalesData {
  week_label: string;
  start_date: string;
  end_date: string;
  sales: DailySalesResponse[];
}

export interface TrafficPoint {
  hour: number;
  time_label: string;
  traffic: number;
}

export interface TrafficPeak {
  time_label: string;
  traffic: number;
  period: string;
}

export interface TrafficData {
  week_label: string;
  start_date: string;
  end_date: string;
  points: TrafficPoint[];
  peaks: TrafficPeak[];
}

export const adminService = {
  /**
   * Fetch screen times grouped by user for the specified week
   */
  async getScreenTime(weekOffset: number = 0): Promise<ScreenTimeData> {
    return apiClient.get<ScreenTimeData>(`/api/admin/screentime?week_offset=${weekOffset}`);
  },

  /**
   * Fetch broadcasted product sales performance
   */
  async getBroadcastPerformance(): Promise<BroadcastPerformanceResponse[]> {
    return apiClient.get<BroadcastPerformanceResponse[]>("/api/admin/broadcast-performance");
  },

  /**
   * Fetch daily overall sales for Sunday to Saturday for the specified week
   */
  async getOverallSales(weekOffset: number = 0): Promise<OverallSalesData> {
    return apiClient.get<OverallSalesData>(`/api/admin/overall-sales?week_offset=${weekOffset}`);
  },

  /**
   * Fetch hourly website traffic pattern for the specified week
   */
  async getTraffic(weekOffset: number = 0): Promise<TrafficData> {
    return apiClient.get<TrafficData>(`/api/admin/traffic?week_offset=${weekOffset}`);
  },
};
