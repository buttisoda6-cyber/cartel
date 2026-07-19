/**
 * Broadcast API service
 */

import { apiClient } from "./client";

export interface BroadcastRecipient {
  customerId: number;
  customerName: string;
  phoneNumber: string;
}

export interface BroadcastLog {
  id: number;
  offerId: number;
  customerCount: number;
  status: string;
  sentAt: string;
  scheduledAt?: string;
}

export interface BroadcastCreate {
  offerId: number;
  customerCount: number;
  recipients: BroadcastRecipient[];
  scheduledAt?: string;
}

export const broadcastService = {
  /**
   * Create a new broadcast for an offer
   */
  async create(broadcast: BroadcastCreate): Promise<BroadcastLog> {
    return apiClient.post<BroadcastLog>("/api/broadcasts", broadcast);
  },

  /**
   * Get all broadcasts
   */
  async getAll(limit: number = 50, offset: number = 0): Promise<BroadcastLog[]> {
    return apiClient.get<BroadcastLog[]>(`/api/broadcasts?limit=${limit}&offset=${offset}`);
  },

  /**
   * Get broadcasts for a specific offer
   */
  async getForOffer(offerId: number): Promise<BroadcastLog[]> {
    return apiClient.get<BroadcastLog[]>(`/api/broadcasts/offer/${offerId}/broadcasts`);
  },

  /**
   * Get a specific broadcast by ID
   */
  async getById(broadcastId: number): Promise<BroadcastLog> {
    return apiClient.get<BroadcastLog>(`/api/broadcasts/${broadcastId}`);
  },

  /**
   * Get broadcast summary statistics
   */
  async getSummary(broadcastId: number): Promise<any> {
    return apiClient.get<any>(`/api/broadcasts/${broadcastId}/summary`);
  },

  /**
   * Get recipients for a broadcast
   */
  async getRecipients(broadcastId: number, limit: number = 100, offset: number = 0): Promise<BroadcastRecipient[]> {
    return apiClient.get<BroadcastRecipient[]>(
      `/api/broadcasts/${broadcastId}/recipients?limit=${limit}&offset=${offset}`
    );
  },

  /**
   * Update recipient delivery status
   */
  async updateRecipientStatus(
    broadcastId: number,
    recipientId: number,
    status: string
  ): Promise<BroadcastRecipient> {
    return apiClient.patch<BroadcastRecipient>(
      `/api/broadcasts/${broadcastId}/recipients/${recipientId}/status?status=${status}`,
      {}
    );
  },
};
