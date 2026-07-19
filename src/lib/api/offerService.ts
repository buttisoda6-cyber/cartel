/**
 * Offer API service
 */

import { apiClient } from "./client";

export interface Offer {
  id: number;
  productIds: number[];
  productNames: string[];
  discountType: string;
  discountValue: number;
  validFrom: string;
  validTo: string;
  status: string;
  broadcasted: boolean;
  createdAt: string;
}

export interface OfferCreate {
  productIds: number[];
  productNames: string[];
  discountType: string;
  discountValue: number;
  validFrom: string;
  validTo: string;
}

export const offerService = {
  /**
   * Approve and create a new offer
   */
  async approve(offer: OfferCreate): Promise<Offer> {
    return apiClient.post<Offer>("/api/offers/approve", offer);
  },

  /**
   * Get the current unbroadcasted offer
   */
  async getCurrent(): Promise<Offer | null> {
    return apiClient.get<Offer | null>("/api/offers/current");
  },

  /**
   * Get all offers with optional filtering
   */
  async getAll(
    status?: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<Offer[]> {
    let url = `/api/offers?limit=${limit}&offset=${offset}`;
    if (status) {
      url += `&status=${status}`;
    }
    return apiClient.get<Offer[]>(url);
  },

  /**
   * Get a specific offer by ID
   */
  async getById(offerId: number): Promise<Offer> {
    return apiClient.get<Offer>(`/api/offers/${offerId}`);
  },

  /**
   * Get offer approval history
   */
  async getHistory(days?: number, limit: number = 100): Promise<Offer[]> {
    let url = `/api/offers/history/approval?limit=${limit}`;
    if (days) {
      url += `&days=${days}`;
    }
    return apiClient.get<Offer[]>(url);
  },

  /**
   * Get detailed information about an offer
   */
  async getDetails(offerId: number): Promise<any> {
    return apiClient.get<any>(`/api/offers/${offerId}/details`);
  },

  /**
   * Archive an offer
   */
  async archive(offerId: number): Promise<Offer> {
    return apiClient.patch<Offer>(`/api/offers/${offerId}/archive`, {});
  },
};

