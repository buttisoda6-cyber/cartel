/**
 * Product API service
 */

import { apiClient } from "./client";

export interface Product {
  id: string;
  name: string;
  category: string;
  unit: string;
  mrp: number;
  stock: number;
  status: string;
  aiPick?: boolean;
  daysIdle?: number;
  img: string;
  expiryDays?: number;
  weightKg?: number;
}

export const productService = {
  /**
   * Get all products with optional filtering
   */
  async getAll(params?: {
    category?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<Product[]> {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.append("category", params.category);
    if (params?.status) searchParams.append("status", params.status);
    if (params?.skip) searchParams.append("skip", String(params.skip));
    if (params?.limit) searchParams.append("limit", String(params.limit));

    const query = searchParams.toString();
    const endpoint = query ? `/api/products?${query}` : "/api/products";
    return apiClient.get<Product[]>(endpoint);
  },

  /**
   * Get a single product by ID
   */
  async getById(id: string): Promise<Product> {
    return apiClient.get<Product>(`/api/products/${id}`);
  },

  /**
   * Get all categories
   */
  async getCategories(): Promise<string[]> {
    const response = await apiClient.get<{ categories: string[] }>(
      "/api/categories"
    );
    return response.categories;
  },
};
