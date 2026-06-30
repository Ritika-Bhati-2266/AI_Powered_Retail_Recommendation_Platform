import { useState, useCallback } from 'react';
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
import type { CustomerFull } from './types';

type AppMode = 'login' | 'admin' | 'customer';
type AdminTab = 'dashboard' | 'analytics' | 'products';

export default function App() {
  const [mode, setMode] = useState<AppMode>('login');
  const [loggedInCustomer, setLoggedInCustomer] = useState<CustomerFull | null>(null);

  // Admin mode state
  const [activeTab, setActiveTab] = useState<AdminTab>('dashboard');
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const [customer, setCustomer] = useState<CustomerFull | null>(null);
  const [loadingCustomer, setLoadingCustomer] = useState(false);
  const [training, setTraining] = useState(false);
  const [trainMessage, setTrainMessage] = useState<string | null>(null);

  const handleLogin = useCallback((c: CustomerFull) => {
    setLoggedInCustomer(c);
    setMode('customer');
  }, []);

  const handleLogout = useCallback(() => {
    setLoggedInCustomer(null);
    setMode('login');
  }, []);

  // Admin: switch to admin mode from login or customer view
  const handleEnterAdmin = useCallback(() => {
    setMode('admin');
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

  // ── Login Screen ──────────────────────────────────────────────────
  if (mode === 'login') {
    return (
      <div className="min-h-screen bg-surface flex flex-col">
        <LoginScreen onLogin={handleLogin} />
        <div className="text-center pb-8">
          <button
            onClick={handleEnterAdmin}
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            <User className="w-3 h-3" />
            Admin Dashboard
          </button>
        </div>
      </div>
    );
  }

  // ── Customer View ─────────────────────────────────────────────────
  if (mode === 'customer' && loggedInCustomer) {
    return <CustomerView customer={loggedInCustomer} onLogout={handleLogout} />;
  }

  // ── Admin Dashboard ────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-surface">
      {/* Header */}
      <header className="bg-slate-900/80 border-b border-slate-800 sticky top-0 z-50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-slate-100">
                Hyper-Personalisation Engine
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Tab Navigation */}
            <div className="flex items-center gap-1 bg-slate-800/50 rounded-lg p-0.5 mr-2">
              <button
                onClick={() => { setActiveTab('dashboard'); setSelectedCustomerId(null); setCustomer(null); }}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  activeTab === 'dashboard'
                    ? 'bg-slate-700 text-slate-100 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Search className="w-3.5 h-3.5" />
                Dashboard
              </button>
              <button
                onClick={() => setActiveTab('analytics')}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  activeTab === 'analytics'
                    ? 'bg-slate-700 text-slate-100 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                Analytics
              </button>
              <button
                onClick={() => setActiveTab('products')}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  activeTab === 'products'
                    ? 'bg-slate-700 text-slate-100 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Package className="w-3.5 h-3.5" />
                Products
              </button>
            </div>
            <button
            onClick={handleTrainModel}
            disabled={training}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-primary-600/20"
          >
            {training ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <BrainCircuit className="w-4 h-4" />
            )}
            {training ? 'Training...' : 'Train Model'}
          </button>
            {/* Logout / Switch to Customer Portal */}
            <button
              onClick={() => setMode('login')}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 bg-slate-800/30 hover:bg-slate-700/30 rounded-lg transition-all"
              title="Switch to customer portal"
            >
              <LogOut className="w-3 h-3" />
              Exit
            </button>
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

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        {activeTab === 'analytics' ? (
          <AnalyticsPage />
        ) : activeTab === 'products' ? (
          <ProductSearch />
        ) : !selectedCustomerId ? (
          /* Initial State - Customer Search Centered */
          <div className="max-w-lg mx-auto mt-12">
            <div className="text-center mb-6">
              <BrainCircuit className="w-12 h-12 text-primary-400/60 mx-auto mb-3" />
              <h2 className="text-xl font-semibold text-slate-200">Welcome to the Dashboard</h2>
              <p className="text-sm text-slate-400 mt-2">
                Search for a customer to view their personalised insights, recommendations, and
                offers.
              </p>
            </div>
            <CustomerSearch
              onCustomerSelect={handleCustomerSelect}
              selectedCustomerId={selectedCustomerId}
            />
          </div>
        ) : (
          /* Customer Detail View */
          <div className="flex gap-6">
            {/* Left Sidebar */}
            <div className="w-72 shrink-0">
              <button
                onClick={handleBack}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 mb-3 transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                Back to search
              </button>
              <CustomerSearch
                onCustomerSelect={handleCustomerSelect}
                selectedCustomerId={selectedCustomerId}
              />
            </div>

            {/* Main Content Area */}
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
