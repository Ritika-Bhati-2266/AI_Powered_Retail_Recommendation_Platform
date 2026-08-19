export interface Customer {
  customer_id: string;
  name: string;
  email: string;
  consent_status: boolean;
  currency?: string;
  role?: string;
}

export interface Segment {
  segment: string;
  assigned_at: string;
}

export interface CustomerMetrics {
  total_views: number;
  total_purchases: number;
  total_cart_events: number;
  total_email_engagement: number;
  avg_session_duration_minutes: number;
  days_since_last_activity: number;
  lifetime_value: number;
  preferred_category: string;
  preferred_price_tier: string;
}

export interface CustomerFull extends Customer {
  segments: Segment[];
  metrics: CustomerMetrics;
  category_preferences?: string[];
}

export interface AuthResult {
  access_token: string;
  token_type: string;
  customer_id: string;
  name: string;
  email: string;
  role: string;
}

export interface Product {
  product_id: string;
  name: string;
  category: string;
  subcategory: string;
  brand: string;
  price: number;
  currency?: string;
  symbol?: string;
  image_url: string;
  rating?: number;
  original_price?: number;
  discount_percent?: number;
}

export interface Recommendation extends Product {
  score: number;
  reason_code: string;
  reason_text: string;
}

export interface Offer {
  offer_id: string;
  title: string;
  description: string;
  discount_type: string;
  discount_value: number;
  discount_percentage?: number;
  min_purchase?: number;
  reason?: string;
  valid_until: string;
  currency?: string;
  symbol?: string;
}

export interface SegmentCount {
  segment: string;
  count: number;
}

export interface SystemStats {
  total_customers: number;
  consent_rate: number;
  total_events: number;
  total_products: number;
  total_offers: number;
  active_offers: number;
  total_assignments: number;
  segment_distribution: SegmentCount[];
}

export interface OrderItem {
  order_item_id: string;
  product_id?: string;
  product_name_snapshot: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface Order {
  order_id: string;
  customer_id: string;
  total_amount: number;
  currency: string;
  applied_offer_id?: string;
  discount_amount?: number;
  status: string;
  shipping_name?: string;
  shipping_address?: string;
  created_at: string;
  items: OrderItem[];
}
