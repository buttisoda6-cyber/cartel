/**
 * Customer API service
 */

import { apiClient } from "./client";

export interface Customer {
  id: string;
  name: string;
  phone: string;
  type: string;
  outstanding: number;
  lastPurchase: string;
}

export const customerService = {
  /**
   * Get all customers with optional filtering
   */
  async getAll(params?: {
    customerType?: string;
    skip?: number;
    limit?: number;
  }): Promise<Customer[]> {
    const searchParams = new URLSearchParams();
    if (params?.customerType)
      searchParams.append("customer_type", params.customerType);
    if (params?.skip) searchParams.append("skip", String(params.skip));
    if (params?.limit) searchParams.append("limit", String(params.limit));

    const query = searchParams.toString();
    const endpoint = query ? `/api/customers?${query}` : "/api/customers";
    return apiClient.get<Customer[]>(endpoint);
  },

  /**
   * Get a single customer by ID
   */
  async getById(id: string): Promise<Customer> {
    return apiClient.get<Customer>(`/api/customers/${id}`);
  },
};
