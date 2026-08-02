import type { Customer, CustomerFull, Recommendation, Offer, Product, Order, AuthResult } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export const tokenStore = {
  get(): string | null {
    return sessionStorage.getItem('access_token');
  },
  set(token: string): void {
    sessionStorage.setItem('access_token', token);
  },
  clear(): void {
    sessionStorage.removeItem('access_token');
  },
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers = new Headers(options?.headers);
  headers.set('Content-Type', 'application/json');

  // The bearer token is the source of truth for who the user is.
  const token = tokenStore.get();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
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
    let path = `/products/search?q=${encodeURIComponent(query)}&limit=100`;
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

  async login(email: string, password: string): Promise<AuthResult> {
    const res = await request<AuthResult>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    tokenStore.set(res.access_token);
    return res;
  },

  async createCustomer(name: string, email: string, password: string, categoryPreferences?: string[]): Promise<CustomerFull> {
    return request<CustomerFull>('/customers', {
      method: 'POST',
      body: JSON.stringify({
        name,
        email,
        password,
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

  trackEvent(customerId: string, eventType: string, productId?: string, sessionId?: string): Promise<{ status: string; event_id: string }> {
    return request<{ status: string; event_id: string }>('/events', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: customerId,
        event_type: eventType,
        product_id: productId,
        session_id: sessionId,
      }),
    });
  },

  getRecentlyViewed(customerId: string, limit: number = 10): Promise<Product[]> {
    return request<Product[]>(
      `/customers/${encodeURIComponent(customerId)}/recently-viewed?limit=${limit}`
    );
  },

  getContinueShopping(customerId: string, limit: number = 10): Promise<Product[]> {
    return request<Product[]>(
      `/customers/${encodeURIComponent(customerId)}/continue-shopping?limit=${limit}`
    );
  },

  placeOrder(customerId: string, items: { product_id: string; quantity: number }[], shipping?: { name?: string; address?: string }): Promise<Order> {
    return request<Order>(`/customers/${encodeURIComponent(customerId)}/orders`, {
      method: 'POST',
      body: JSON.stringify({
        items,
        shipping_name: shipping?.name,
        shipping_address: shipping?.address,
      }),
    });
  },

  getOrders(customerId: string): Promise<Order[]> {
    return request<Order[]>(`/customers/${encodeURIComponent(customerId)}/orders`);
  },

  getOrder(customerId: string, orderId: string): Promise<Order> {
    return request<Order>(`/customers/${encodeURIComponent(customerId)}/orders/${encodeURIComponent(orderId)}`);
  },
};
