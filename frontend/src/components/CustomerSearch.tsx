import { useState, useEffect, useRef } from 'react';
import { Search, User } from 'lucide-react';
import { apiClient } from '../api/client';
import type { Customer } from '../types';

interface CustomerSearchProps {
  onCustomerSelect: (customerId: string) => void;
  selectedCustomerId: string | null;
}

export default function CustomerSearch({ onCustomerSelect, selectedCustomerId }: CustomerSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setSearched(false);
      return;
    }

    setLoading(true);
    clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      try {
        const data = await apiClient.searchCustomers(query.trim());
        setResults(data);
        setSearched(true);
      } catch {
        setResults([]);
        setSearched(true);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(debounceRef.current);
  }, [query]);

  return (
    <div className="card p-4">
      <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
        Customer Search
      </h2>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name or email..."
          className="w-full bg-slate-800 text-slate-100 placeholder-slate-500 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
        />
      </div>

      {loading && (
        <div className="mt-3 space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-14 w-full" />
          ))}
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="mt-4 text-center py-6">
          <User className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-sm text-slate-500">No customers found</p>
          <p className="text-xs text-slate-600 mt-1">Try a different search term</p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <>
          <p className="text-xs text-slate-500 mt-3 mb-2">
            {results.length} customer{results.length !== 1 ? 's' : ''} found
          </p>
          <div className="space-y-1 max-h-[calc(100vh-320px)] overflow-y-auto">
            {results.map((customer) => (
              <button
                key={customer.customer_id}
                onClick={() => onCustomerSelect(customer.customer_id)}
                className={`w-full text-left p-3 rounded-lg transition-all ${
                  selectedCustomerId === customer.customer_id
                    ? 'bg-primary-500/10 border border-primary-500/30'
                    : 'hover:bg-slate-700/50 border border-transparent'
                }`}
              >
                <p className="text-sm font-medium text-slate-200">{customer.name}</p>
                <p className="text-xs text-slate-400 mt-0.5">{customer.email}</p>
              </button>
            ))}
          </div>
        </>
      )}

      {!loading && !query.trim() && (
        <div className="mt-4 text-center py-6">
          <Search className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-sm text-slate-500">Type to search customers</p>
        </div>
      )}
    </div>
  );
}
