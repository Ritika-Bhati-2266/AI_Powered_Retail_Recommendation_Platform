/**
 * Format a price with its currency symbol.
 * The backend already returns price and symbol, so we just combine them.
 */
export function formatPrice(price: number, symbol?: string): string {
  const sym = symbol || '$';
  if (sym === '₹') {
    // Indian format: ₹1,234 or ₹1,234.56
    if (Number.isInteger(price)) {
      return `${sym}${price.toLocaleString('en-IN')}`;
    }
    return `${sym}${price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  if (sym === '€') {
    // European format: €1.234,56 or space as thousand separator
    return `${sym}${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  // Default USD: $1,234.56
  if (price >= 1000) {
    return `${sym}${price.toLocaleString('en-US', { minimumFractionDigits: price % 1 === 0 ? 0 : 2, maximumFractionDigits: 2 })}`;
  }
  return `${sym}${Number(price).toFixed(price % 1 === 0 ? 0 : 2)}`;
}
