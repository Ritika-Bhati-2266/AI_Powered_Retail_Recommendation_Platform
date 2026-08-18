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

// Thrown whenever the backend itself is unreachable (crashed, still starting
// up, busy, or running on the wrong port) — NOT a credentials/data problem.
export class BackendUnreachableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'BackendUnreachableError';
  }
}

const REQUEST_TIMEOUT_MS = 30_000;

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
  getCustomer(): CustomerFull | null {
    try {
      const raw = sessionStorage.getItem('customer_profile');
      return raw ? (JSON.parse(raw) as CustomerFull) : null;
    } catch {
      return null;
    }
  },
  setCustomer(c: CustomerFull): void {
    sessionStorage.setItem('customer_profile', JSON.stringify(c));
  },
  clearAll(): void {
    this.clear();
    sessionStorage.removeItem('customer_profile');
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

  // Abort after REQUEST_TIMEOUT_MS so a busy/stuck backend can't hang the UI
  // forever — the user gets a clear "server busy" message instead.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (err) {
    // Fetch only throws on transport-level failures: DNS, connection refused,
    // socket reset — i.e. the backend is unreachable.
    const timedOut = err instanceof DOMException && err.name === 'AbortError';
    throw new BackendUnreachableError(
      timedOut
        ? 'The server is taking too long to respond — it may be busy or still starting up. Please wait a moment and try again.'
        : 'Connection error — the backend appears to be unavailable or starting up. Please wait a moment and try again.'
    );
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    const text = await response.text().catch(() => 'Unknown error');

    // The Vite proxy/dev proxy returns 503 with a `backend_unreachable` flag
    // when it cannot reach the backend — surface that as a connection problem,
    // not a data/credentials problem.
    if (response.status === 503) {
      try {
        const body = JSON.parse(text);
        if (body?.error === 'backend_unreachable') {
          throw new BackendUnreachableError(
            'Server is starting up or temporarily unavailable. Please wait a moment and try again.'
          );
        }
      } catch {
        /* not a proxy error body — fall through to the normal ApiError */
      }
    }

    // A 401 on an authenticated call means the stored token is invalid/expired.
    // Only treat /auth/login 401s as normal "wrong credentials" (shown inline by
    // the login form) — never clear an otherwise-active session for those.
    if (response.status === 401 && path !== '/auth/login') {
      const hadToken = !!tokenStore.get();
      tokenStore.clearAll();
      if (hadToken) {
        window.dispatchEvent(new Event('auth:unauthorized'));
      }
    }
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

  async createCustomer(name: string, email: string, password: string, categoryPreferences?: string[], consentGiven?: boolean): Promise<CustomerFull> {
    return request<CustomerFull>('/customers', {
      method: 'POST',
      body: JSON.stringify({
        name,
        email,
        password,
        consent_given: consentGiven === true,
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

  updateConsent(customerId: string, consentGiven: boolean): Promise<CustomerFull> {
    return request<CustomerFull>(`/customers/${encodeURIComponent(customerId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ consent_given: consentGiven }),
    });
  },

  exportCustomerData(customerId: string): Promise<Record<string, unknown>> {
    return request<Record<string, unknown>>(
      `/customers/${encodeURIComponent(customerId)}/data-export`
    );
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

  getWishlist(customerId: string, limit: number = 50): Promise<Product[]> {
    return request<Product[]>(
      `/customers/${encodeURIComponent(customerId)}/wishlist?limit=${limit}`
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
