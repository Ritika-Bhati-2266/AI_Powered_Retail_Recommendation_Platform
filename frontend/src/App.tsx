import { useState, useCallback, useEffect } from 'react';
import {
  Sparkles,
  BrainCircuit,
  Loader2,
  ChevronLeft,
  BarChart3,
  Search,
  Package,
  LogOut,
  User,
  ShoppingCart,
} from 'lucide-react';
import { apiClient } from './api/client';
import CustomerSearch from './components/CustomerSearch';
import CustomerProfile from './components/CustomerProfile';
import RecommendationsPanel from './components/RecommendationsPanel';
import OffersPanel from './components/OffersPanel';
import AnalyticsPage from './components/AnalyticsPage';
import ProductSearch from './components/ProductSearch';
import LoginScreen from './components/LoginScreen';
import CustomerView from './components/CustomerView';
import DemoView from './components/DemoView';
import type { CustomerFull } from './types';

type AppMode = 'login' | 'admin' | 'customer' | 'demo';
type AdminTab = 'dashboard' | 'analytics' | 'products';

export default function App() {
  const [mode, setMode] = useState<AppMode>('login');
  const [loggedInCustomer, setLoggedInCustomer] = useState<CustomerFull | null>(null);
  const [activeTab, setActiveTab] = useState<AdminTab>('dashboard');
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const [customer, setCustomer] = useState<CustomerFull | null>(null);
  const [loadingCustomer, setLoadingCustomer] = useState(false);
  const [training, setTraining] = useState(false);
  const [trainMessage, setTrainMessage] = useState<string | null>(null);

  const handleLogin = useCallback((c: CustomerFull) => {
    setLoggedInCustomer(c);
    localStorage.setItem('user_email', c.email);
    if (c.role === 'admin') {
      setMode('admin');
    } else {
      setMode('customer');
    }
  }, []);

  const handleLogout = useCallback(() => {
    setLoggedInCustomer(null);
    localStorage.removeItem('user_email');
    setMode('login');
  }, []);

  const handleEnterAdmin = useCallback(() => {
    if (loggedInCustomer?.role === 'admin') {
      setMode('admin');
    } else {
      setMode('login');
    }
  }, [loggedInCustomer]);

  const handleEnterDemo = useCallback(() => {
    setMode('demo');
  }, []);

  const handleCustomerSelect = useCallback(async (customerId: string) => {
    setSelectedCustomerId(customerId);
    setLoadingCustomer(true);
    setCustomer(null);
    try {
      const data = await apiClient.getCustomer(customerId);
      setCustomer(data);
    } catch {
      setCustomer(null);
    } finally {
      setLoadingCustomer(false);
    }
  }, []);

  const handleTrainModel = useCallback(async () => {
    setTraining(true);
    setTrainMessage(null);
    try {
      const result = await apiClient.trainModel();
      setTrainMessage(result.message);
    } catch {
      setTrainMessage('Failed to start training');
    } finally {
      setTraining(false);
    }
  }, []);

  const handleBack = useCallback(() => {
    setSelectedCustomerId(null);
    setCustomer(null);
  }, []);

  // Direct URL access check: redirect to login if not admin
  useEffect(() => {
    const checkAuth = () => {
      const isHashAdmin = window.location.hash === '#admin' || window.location.search.includes('mode=admin');
      if (isHashAdmin) {
        if (loggedInCustomer?.role !== 'admin') {
          setMode('login');
          window.location.hash = '';
        } else {
          setMode('admin');
        }
      }
    };
    checkAuth();
    window.addEventListener('hashchange', checkAuth);
    return () => window.removeEventListener('hashchange', checkAuth);
  }, [loggedInCustomer]);

  if (mode === 'login') {
    return (
      <div className="min-h-screen bg-black flex flex-col">
        <LoginScreen onLogin={handleLogin} onEnterDemo={handleEnterDemo} />
        {loggedInCustomer?.role === 'admin' && (
          <div className="text-center pb-8">
            <button
              onClick={handleEnterAdmin}
              className="inline-flex items-center gap-1.5 text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
            >
              <User className="w-3 h-3" />
              Admin Dashboard
            </button>
          </div>
        )}
      </div>
    );
  }

  if (mode === 'customer' && loggedInCustomer) {
    return <CustomerView customer={loggedInCustomer} onLogout={handleLogout} />;
  }

  if (mode === 'demo') {
    return <DemoView onBack={() => setMode('login')} />;
  }

  return (
    <div className="min-h-screen bg-black">
      <header className="bg-zinc-900/80 border-b border-zinc-800 sticky top-0 z-50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-zinc-100">
                PersonalShop
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 bg-zinc-800/50 rounded-lg p-0.5 mr-2">
              <button
                onClick={() => { setActiveTab('dashboard'); setSelectedCustomerId(null); setCustomer(null); }}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  activeTab === 'dashboard'
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Search className="w-3.5 h-3.5" />
                Dashboard
              </button>
              <button
                onClick={() => setActiveTab('analytics')}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  activeTab === 'analytics'
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                Analytics
              </button>
              <button
                onClick={() => setActiveTab('products')}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  activeTab === 'products'
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Package className="w-3.5 h-3.5" />
                Products
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleTrainModel}
                disabled={training}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-purple-600/20"
              >
                {training ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <BrainCircuit className="w-4 h-4" />
                )}
                {training ? 'Training...' : 'Train Model'}
              </button>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-200 bg-zinc-800/30 hover:bg-zinc-700/30 rounded-lg transition-all"
                title="Log out and switch to customer portal"
              >
                <LogOut className="w-3 h-3" />
                Exit
              </button>
            </div>
          </div>
        </div>
        {trainMessage && (
          <div className="max-w-7xl mx-auto px-6 pb-3">
            <div className="bg-emerald-900/30 border border-emerald-700/30 rounded-lg px-4 py-2">
              <p className="text-xs text-emerald-300">{trainMessage}</p>
            </div>
          </div>
        )}
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {activeTab === 'analytics' ? (
          <AnalyticsPage />
        ) : activeTab === 'products' ? (
          <ProductSearch />
        ) : !selectedCustomerId ? (
          <div className="max-w-lg mx-auto mt-12">
            <div className="text-center mb-6">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-purple-600/20">
                <BrainCircuit className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-semibold text-zinc-200">Welcome to the Dashboard</h2>
              <p className="text-sm text-zinc-500 mt-2">
                Search for a customer to view their personalised insights, recommendations, and offers.
              </p>
            </div>
            <CustomerSearch
              onCustomerSelect={handleCustomerSelect}
              selectedCustomerId={selectedCustomerId}
            />
          </div>
        ) : (
          <div className="flex gap-6">
            <div className="w-72 shrink-0">
              <button
                onClick={handleBack}
                className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200 mb-3 transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                Back to search
              </button>
              <CustomerSearch
                onCustomerSelect={handleCustomerSelect}
                selectedCustomerId={selectedCustomerId}
              />
            </div>
            <div className="flex-1 min-w-0 space-y-5">
              {loadingCustomer && (
                <div className="card p-5 space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="skeleton w-12 h-12 rounded-full" />
                    <div className="space-y-2">
                      <div className="skeleton h-5 w-48" />
                      <div className="skeleton h-3 w-32" />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                      <div key={i} className="skeleton h-16" />
                    ))}
                  </div>
                </div>
              )}
              {!loadingCustomer && customer && (
                <>
                  <CustomerProfile customer={customer} />
                  <div className="grid grid-cols-5 gap-5">
                    <div className="col-span-3">
                      <RecommendationsPanel
                        customerId={customer.customer_id}
                        consentStatus={customer.consent_status}
                      />
                    </div>
                    <div className="col-span-2">
                      <OffersPanel customerId={customer.customer_id} />
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
