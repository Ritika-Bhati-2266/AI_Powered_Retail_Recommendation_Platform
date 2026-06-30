import type { Customer, CustomerFull, Recommendation, Offer, Product } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => 'Unknown error');
    throw new ApiError(`API error ${response.status}: ${text}`, response.status);
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  healthCheck(): Promise<{ status: string }> {
    return request<{ status: string }>('/health');
  },

  searchCustomers(query: string): Promise<Customer[]> {
    return request<Customer[]>(`/customers/search?q=${encodeURIComponent(query)}`);
  },

  getCustomer(customerId: string): Promise<CustomerFull> {
    return request<CustomerFull>(`/customers/${encodeURIComponent(customerId)}`);
  },

  getRecommendations(customerId: string): Promise<Recommendation[]> {
    return request<Recommendation[]>(
      `/customers/${encodeURIComponent(customerId)}/recommendations`
    );
  },

  getOffers(customerId: string): Promise<Offer[]> {
    return request<Offer[]>(
      `/customers/${encodeURIComponent(customerId)}/offers`
    );
  },

  trainModel(): Promise<{ status: string; message: string }> {
    return request<{ status: string; message: string }>('/admin/train', {
      method: 'POST',
    });
  },

  assignOffers(): Promise<{ status: string; assignments_count: number; message: string }> {
    return request<{ status: string; assignments_count: number; message: string }>('/admin/assign-offers', {
      method: 'POST',
    });
  },

  getStats(): Promise<import('../types').SystemStats> {
    return request<import('../types').SystemStats>('/admin/stats');
  },

  searchProducts(query: string, category?: string, customerId?: string): Promise<Product[]> {
    let path = `/products/search?q=${encodeURIComponent(query)}&limit=50`;
    if (category) {
      path += `&category=${encodeURIComponent(category)}`;
    }
    if (customerId) {
      path += `&customer_id=${encodeURIComponent(customerId)}`;
    }
    return request<Product[]>(path);
  },

  getProduct(productId: string): Promise<Product> {
    return request<Product>(`/products/${encodeURIComponent(productId)}`);
  },

  getProductCategories(): Promise<string[]> {
    return request<string[]>('/products/categories');
  },

  loginByEmail(email: string): Promise<CustomerFull> {
    return request<CustomerFull>(`/customers/by-email?email=${encodeURIComponent(email)}`);
  },

  createCustomer(name: string, email: string, categoryPreferences?: string[]): Promise<CustomerFull> {
    return request<CustomerFull>('/customers', {
      method: 'POST',
      body: JSON.stringify({
        name,
        email,
        consent_given: true,
        category_preferences: categoryPreferences || [],
      }),
    });
  },

  updateCustomerCurrency(customerId: string, currency: string): Promise<CustomerFull> {
    return request<CustomerFull>(`/customers/${encodeURIComponent(customerId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ currency }),
    });
  },

  getCurrencies(): Promise<Record<string, string>> {
    return request<Record<string, string>>('/customers/currencies');
  },
};
