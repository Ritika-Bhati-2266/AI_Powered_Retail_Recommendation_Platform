import { useState, useCallback } from 'react';
import { Sparkles, Mail, ArrowRight, Loader2, AlertCircle, User, UserPlus, ArrowLeft, LogIn, ShoppingBag, Search, ShoppingCart, Sun, BrainCircuit, Star, Smartphone, Shirt, BookOpen, Gamepad2, X } from 'lucide-react';
import { apiClient } from '../api/client';
import type { CustomerFull } from '../types';

const CATEGORIES = [
  'Electronics', 'Clothing', 'Home & Kitchen', 'Books',
  'Sports', 'Beauty', 'Toys', 'Grocery',
];

interface LoginScreenProps {
  onLogin: (customer: CustomerFull) => void;
  onEnterDemo?: () => void;
}

type Page = 'landing' | 'login' | 'signup';

export default function LoginScreen({ onLogin, onEnterDemo }: LoginScreenProps) {
  const [page, setPage] = useState<Page>('landing');
  const [selectedPreviewProduct, setSelectedPreviewProduct] = useState<any | null>(null);

  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupLoading, setSignupLoading] = useState(false);
  const [signupError, setSignupError] = useState<string | null>(null);
  const [categoryPreferences, setCategoryPreferences] = useState<string[]>([]);

  const handleLoginSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    try {
      const customer = await apiClient.loginByEmail(trimmed);
      onLogin(customer);
    } catch (err: unknown) {
      if (err instanceof Error && err.message.includes('404')) {
        setError('No account found with that email.');
      } else {
        setError('Something went wrong. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }, [email, onLogin]);

  const handleSignupSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const name = signupName.trim();
    const email = signupEmail.trim();
    if (!name || !email) return;
    setSignupLoading(true);
    setSignupError(null);
    try {
      const customer = await apiClient.createCustomer(name, email, categoryPreferences);
      onLogin(customer);
    } catch {
      setSignupError('Failed to create account. Please try again.');
    } finally {
      setSignupLoading(false);
    }
  }, [signupName, signupEmail, categoryPreferences, onLogin]);

  const goToLogin = useCallback(() => {
    setPage('login');
    setError(null);
  }, []);

  const goToSignup = useCallback(() => {
    setPage('signup');
    setSignupName('');
    setSignupEmail('');
    setSignupError(null);
    setCategoryPreferences([]);
  }, []);

  const switchToSignup = useCallback(() => {
    setSignupEmail(email);
    setPage('signup');
    setError(null);
    setCategoryPreferences([]);
  }, [email]);

  const goToLanding = useCallback(() => {
    setPage('landing');
    setError(null);
    setSignupError(null);
  }, []);

  if (page !== 'landing') {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-purple-600/25">
              <ShoppingBag className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-zinc-100">
              PersonalShop
            </h1>
            <p className="text-sm text-zinc-500 mt-2">
              {page === 'login'
                ? 'Sign in to see your personalised recommendations and offers'
                : 'Create an account to get started'}
            </p>
          </div>

          {page === 'login' ? (
            <div className="bg-black/60 border border-zinc-800/50 rounded-2xl p-6 backdrop-blur-sm">
              <button
                onClick={goToLanding}
                className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200 mb-4 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back
              </button>
              <form onSubmit={handleLoginSubmit} className="space-y-4">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-zinc-300 mb-1.5">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      required
                      autoFocus
                      className="input-dark"
                    />
                  </div>
                </div>
                {error && (
                  <div className="flex flex-col gap-3 bg-red-900/20 border border-red-800/30 rounded-xl px-4 py-3">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                      <p className="text-sm text-red-300">{error}</p>
                    </div>
                    <button
                      type="button"
                      onClick={switchToSignup}
                      className="flex items-center justify-center gap-2 px-3 py-2 bg-purple-700/40 hover:bg-purple-700/60 text-purple-300 text-sm font-medium rounded-lg transition-all border border-purple-700/30"
                    >
                      <UserPlus className="w-4 h-4" />
                      Create Account with This Email
                    </button>
                  </div>
                )}
                <button
                  type="submit"
                  disabled={loading || !email.trim()}
                  className="btn-primary w-full"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <ArrowRight className="w-4 h-4" />
                  )}
                  {loading ? 'Signing in...' : 'Sign In'}
                </button>
              </form>
              <p className="text-xs text-zinc-600 mt-4 text-center">
                No password required. Enter your email to view your personalised experience.
              </p>
            </div>
          ) : (
            <div className="bg-black/60 border border-zinc-800/50 rounded-2xl p-6 backdrop-blur-sm">
              <button
                onClick={goToLanding}
                className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200 mb-4 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back
              </button>
              <form onSubmit={handleSignupSubmit} className="space-y-4">
                <div>
                  <label htmlFor="signup-name" className="block text-sm font-medium text-zinc-300 mb-1.5">
                    Your Name
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <input
                      id="signup-name"
                      type="text"
                      value={signupName}
                      onChange={(e) => setSignupName(e.target.value)}
                      placeholder="Jane Smith"
                      required
                      autoFocus
                      className="input-dark"
                    />
                  </div>
                </div>
                <div>
                  <label htmlFor="signup-email" className="block text-sm font-medium text-zinc-300 mb-1.5">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <input
                      id="signup-email"
                      type="email"
                      value={signupEmail}
                      onChange={(e) => setSignupEmail(e.target.value)}
                      placeholder="jane@example.com"
                      required
                      className="input-dark"
                    />
                  </div>
                </div>
                {signupError && (
                  <div className="flex items-start gap-2 bg-red-900/20 border border-red-800/30 rounded-xl px-4 py-3">
                    <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                    <p className="text-sm text-red-300">{signupError}</p>
                  </div>
                )}
                <div>
                  <p className="text-xs font-medium text-zinc-500 mb-2">
                    Choose categories you're interested in (optional)
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {CATEGORIES.map((cat) => {
                      const selected = categoryPreferences.includes(cat);
                      return (
                        <button
                          key={cat}
                          type="button"
                          onClick={() => {
                            setCategoryPreferences((prev) =>
                              prev.includes(cat)
                                ? prev.filter((c) => c !== cat)
                                : [...prev, cat]
                            );
                          }}
                          className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-all ${
                            selected
                              ? 'bg-purple-500/20 border-purple-500/50 text-purple-300'
                              : 'bg-zinc-800/50 border-zinc-700/50 text-zinc-400 hover:border-zinc-600 hover:text-zinc-300'
                          }`}
                        >
                          {cat}
                        </button>
                      );
                    })}
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={signupLoading || !signupName.trim() || !signupEmail.trim()}
                  className="btn-primary w-full"
                >
                  {signupLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <UserPlus className="w-4 h-4" />
                  )}
                  {signupLoading ? 'Creating Account...' : 'Create Account'}
                </button>
              </form>
              <p className="text-xs text-zinc-600 mt-4 text-center">
                Your account will be created with consent enabled. You'll get personalised recommendations.
              </p>
            </div>
          )}

          <div className="mt-6 bg-black/40 border border-zinc-800/30 rounded-xl p-4 text-center">
            <p className="text-xs text-zinc-500">
              {page === 'login'
                ? 'Enter your email to sign in. New users can create an account from the main screen.'
                : 'Fill in your name and email to create a new account instantly.'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black flex flex-col">
      <header className="bg-zinc-900/80 border-b border-zinc-800 sticky top-0 z-50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center">
              <ShoppingBag className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-purple-400">PersonalShop</span>
          </div>

          <div className="hidden md:flex flex-1 max-w-md mx-6 relative">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="text"
                placeholder="Search products, categories..."
                onFocus={goToSignup}
                className="w-full bg-zinc-800/50 text-zinc-100 placeholder-zinc-500 border border-zinc-700/50 rounded-xl pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all cursor-pointer"
                readOnly
              />
            </div>
            <div className="absolute top-full left-0 right-0 mt-2 bg-zinc-900/95 border border-zinc-800/50 rounded-xl p-3 backdrop-blur-sm">
              <p className="text-[10px] font-medium text-zinc-600 uppercase tracking-wider mb-2">Trending Searches</p>
              <div className="flex flex-wrap gap-1.5">
                {['Wireless Headphones', 'Sports Shoes', 'Smart Home', 'Skincare', 'Gaming'].map((term) => (
                  <button
                    key={term}
                    onClick={goToSignup}
                    className="text-xs text-zinc-400 hover:text-purple-300 bg-zinc-800/30 hover:bg-purple-500/10 px-2.5 py-1 rounded-full border border-zinc-700/50 hover:border-purple-500/30 transition-all"
                  >
                    {term}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button className="w-10 h-10 rounded-xl bg-zinc-800/50 border border-zinc-700/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all">
              <Sun className="w-4 h-4 text-zinc-300" />
            </button>

            <button className="relative w-10 h-10 rounded-xl bg-zinc-800/50 border border-zinc-700/50 flex items-center justify-center hover:bg-zinc-700/50 transition-all">
              <ShoppingCart className="w-4 h-4 text-zinc-300" />
            </button>

            <div className="flex items-center gap-1.5 bg-zinc-800/50 border border-zinc-700/50 rounded-xl px-2.5 py-1.5">
              <User className="w-3.5 h-3.5 text-zinc-400" />
              <span className="text-xs font-medium text-zinc-200">Hi, Guest</span>
            </div>

            <div className="flex items-center gap-2 pl-2 border-l border-zinc-800">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center">
                <User className="w-4 h-4 text-white" />
              </div>
              <span className="text-xs font-medium text-zinc-200">Guest</span>
            </div>
          </div>
        </div>
      </header>

      <div className="bg-black">
        <div className="max-w-7xl mx-auto px-6 pt-16 pb-20 md:pb-28 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-medium mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            REAL-TIME BEHAVIOR ENGINE
          </div>

          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight leading-tight mb-4">
            The Store That{' '}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500">
              Learns You
            </span>
          </h1>

          <p className="text-base text-zinc-400 max-w-xl mx-auto mb-10">
            Watch recommendations and discount packages adapt instantly as you search, click, and browse the catalog.
          </p>

          <div className="flex items-center justify-center gap-3 mb-16 flex-wrap">
            <button
              onClick={goToSignup}
              className="btn-primary text-base px-8 py-4"
            >
              <UserPlus className="w-5 h-5" />
              Create Free Account
            </button>
            <button
              onClick={onEnterDemo}
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-zinc-800 hover:bg-zinc-700 text-zinc-100 text-base font-semibold rounded-xl transition-all border border-zinc-700 hover:border-purple-500/50 shadow-lg shadow-zinc-900/20"
            >
              <ShoppingBag className="w-5 h-5" />
              Try Demo
            </button>
            <button
              onClick={goToLogin}
              className="btn-outline text-base px-8 py-4"
            >
              <ArrowRight className="w-5 h-5" />
              Sign In
            </button>
          </div>

          <div className="grid grid-cols-3 gap-8 md:gap-12 max-w-3xl mx-auto">
            {[
              { icon: Sparkles, label: 'Smart Picks', desc: 'Personalized picks refresh every time you browse', accent: 'text-amber-400', bg: 'bg-zinc-800/30' },
              { icon: ShoppingBag, label: 'Curated Shop', desc: 'Handpicked from 20K+ products across 8 categories', accent: 'text-emerald-400', bg: 'bg-zinc-800/30' },
              { icon: ArrowRight, label: 'Real-Time', desc: 'Recommendations update as you click and search', accent: 'text-cyan-400', bg: 'bg-zinc-800/30' },
            ].map((item) => (
              <div key={item.label} className="text-center group">
                <div className={`w-16 h-16 rounded-2xl ${item.bg} flex items-center justify-center mx-auto mb-4 transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg group-hover:shadow-zinc-900/30`}>
                  <item.icon className={`w-7 h-7 ${item.accent} transition-transform duration-300 group-hover:scale-110`} />
                </div>
                <p className="text-base font-semibold text-zinc-200 group-hover:text-zinc-100 transition-colors">{item.label}</p>
                <p className="text-xs text-zinc-500 mt-1.5 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Live Demo Preview */}
      <div className="border-t border-zinc-800/50 bg-zinc-900/20">
        <div className="max-w-7xl mx-auto px-6 py-20 md:py-24">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs font-medium mb-4">
              <Sparkles className="w-3.5 h-3.5" />
              LIVE DEMO PREVIEW
            </div>
            <h2 className="text-3xl md:text-4xl font-bold text-zinc-100 mb-3">
              See Recommendations{' '}
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500">
                Adapt Instantly
              </span>
            </h2>
            <p className="text-sm text-zinc-400 max-w-lg mx-auto">
              Hover over any product to see personalization in action — rankings shift based on your interactions.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
            {[
              { name: 'SonicWire Pro', cat: 'Electronics', price: 79.99, icon: Smartphone, col: 'from-cyan-500/20 to-cyan-600/10 border-cyan-700/30', iconCol: 'text-cyan-400' },
              { name: 'Urban Flex Jacket', cat: 'Clothing', price: 129.99, icon: Shirt, col: 'from-pink-500/20 to-pink-600/10 border-pink-700/30', iconCol: 'text-pink-400' },
              { name: 'Quantum Reader', cat: 'Books', price: 14.99, icon: BookOpen, col: 'from-emerald-500/20 to-emerald-600/10 border-emerald-700/30', iconCol: 'text-emerald-400' },
              { name: 'BuildMaster 500pc', cat: 'Toys', price: 39.99, icon: Gamepad2, col: 'from-orange-500/20 to-orange-600/10 border-orange-700/30', iconCol: 'text-orange-400' },
            ].map((item, i) => (
              <div
                key={item.name}
                onClick={() => setSelectedPreviewProduct(item)}
                className="group relative bg-zinc-900/50 border border-zinc-800/50 rounded-2xl overflow-hidden hover:border-zinc-700/50 transition-all duration-500 hover:shadow-xl hover:shadow-purple-600/10 hover:-translate-y-1 cursor-pointer"
                style={{ animationDelay: `${i * 100}ms` }}
              >
                <div className={`relative aspect-[4/3] bg-gradient-to-br ${item.col} overflow-hidden`}>
                  <div className="flex absolute inset-0 items-center justify-center">
                    <item.icon className={`w-14 h-14 ${item.iconCol} opacity-40 group-hover:opacity-60 transition-opacity duration-500`} />
                  </div>
                  <div className="absolute inset-0 bg-gradient-to-t from-zinc-900/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <div className="absolute bottom-0 left-0 right-0 p-3 translate-y-2 group-hover:translate-y-0 opacity-0 group-hover:opacity-100 transition-all duration-400">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-medium text-zinc-300 bg-zinc-900/80 px-2 py-0.5 rounded-full border border-zinc-700/50">
                        #{i + 1} Pick
                      </span>
                      <span
                        title="Based on your browsing and search behavior"
                        className="text-[10px] font-bold text-emerald-400 bg-emerald-900/40 px-2 py-0.5 rounded-full cursor-help"
                      >
                        +{85 - i * 12}% match
                      </span>
                    </div>
                  </div>
                </div>
                <div className="p-3.5">
                  <h3 className="text-sm font-semibold text-zinc-100 truncate group-hover:text-purple-300 transition-colors">{item.name}</h3>
                  <p className="text-xs text-zinc-500 mt-1">{item.cat}</p>
                  <div className="flex items-center justify-between mt-2.5">
                    <span className="text-base font-bold text-purple-400">${item.price}</span>
                    <div className="flex items-center gap-1 text-[10px] text-zinc-600">
                      <ArrowRight className="w-3 h-3 text-purple-500/50 group-hover:text-purple-400 transition-colors" />
                      <span className="group-hover:text-zinc-400 transition-colors">View</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <p className="text-[11px] text-zinc-500 mt-6 italic">
            * Match % is based on your browsing and search behavior.
          </p>

          <div className="text-center mt-8">
            <button
              onClick={onEnterDemo}
              className="inline-flex items-center gap-2 text-xs text-zinc-500 hover:text-purple-400 transition-colors"
            >
              <ShoppingBag className="w-3.5 h-3.5" />
              Browse full demo catalog with 10+ products
            </button>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="border-t border-zinc-800/50 bg-black">
        <div className="max-w-7xl mx-auto px-6 py-20 md:py-24">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold text-zinc-100 mb-3">
              How It{' '}
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500">
                Works
              </span>
            </h2>
            <p className="text-sm text-zinc-400 max-w-lg mx-auto">
              Three simple steps to a completely personalized shopping experience.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {[
              {
                step: '01',
                icon: Search,
                title: 'Browse',
                desc: 'Search for products, click categories, and view items you love. Every interaction teaches the engine your preferences.',
                color: 'from-blue-500/20 to-blue-600/10 border-blue-700/30',
                iconCol: 'text-blue-400',
              },
              {
                step: '02',
                icon: BrainCircuit,
                title: 'AI Learns',
                desc: 'Our hybrid engine analyzes your behavior — weighted by purchase intent — to build a unique taste profile in real time.',
                color: 'from-violet-500/20 to-violet-600/10 border-violet-700/30',
                iconCol: 'text-violet-400',
              },
              {
                step: '03',
                icon: Sparkles,
                title: 'Personalized Results',
                desc: 'Your recommendations, offers, and catalog sort order adapt instantly. Every refresh brings something more relevant.',
                color: 'from-emerald-500/20 to-emerald-600/10 border-emerald-700/30',
                iconCol: 'text-emerald-400',
              },
            ].map((item) => (
              <div key={item.step} className="relative text-center group">
                <div className={`w-20 h-20 rounded-2xl bg-gradient-to-br ${item.color} flex items-center justify-center mx-auto mb-5 transition-all duration-300 group-hover:scale-110 group-hover:shadow-xl`}>
                  <item.icon className={`w-9 h-9 ${item.iconCol}`} />
                </div>
                <span className="text-[10px] font-bold text-zinc-600 tracking-widest">{item.step}</span>
                <h3 className="text-lg font-bold text-zinc-100 mt-1.5 mb-2">{item.title}</h3>
                <p className="text-sm text-zinc-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Social Proof */}
      <div className="border-t border-zinc-800/50 bg-zinc-900/20">
        <div className="max-w-7xl mx-auto px-6 py-20 md:py-24 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-medium mb-6">
            <Star className="w-3.5 h-3.5" />
            TRUSTED BY THOUSANDS
          </div>
          <span className="block text-[10px] text-zinc-600 italic -mt-4 mb-8">Illustrative sample data</span>

          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto mb-14">
            {[
              { value: '500K+', label: 'Active Users', desc: 'Shoppers rely on PersonalShop daily for tailored recommendations.' },
              { value: '98.7%', label: 'Satisfaction Rate', desc: 'Users report noticeably better discoverability versus generic stores.' },
              { value: '2.3x', label: 'Avg. Engagement', desc: 'Personalized recommendations drive over double the interaction rate.' },
            ].map((stat) => (
              <div key={stat.label} className="bg-zinc-900/40 border border-zinc-800/40 rounded-2xl p-6 hover:border-zinc-700/50 transition-all hover:-translate-y-0.5">
                <p className="text-3xl md:text-4xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-pink-400">
                  {stat.value}
                </p>
                <p className="text-sm font-semibold text-zinc-200 mt-1.5">{stat.label}</p>
                <p className="text-xs text-zinc-500 mt-1.5 leading-relaxed">{stat.desc}</p>
              </div>
            ))}
          </div>

          <div className="max-w-2xl mx-auto space-y-6">
            {[
              { name: 'Sarah Chen', role: 'Verified Buyer', text: '"I\'ve never had a store understand my taste this well. The recommendations are scarily accurate — it\'s like having a personal stylist."' },
              { name: 'Marcus Rivera', role: 'Premium Member', text: '"The offers I get are actually things I want to buy. No spam, no irrelevant discounts. This is how personalization should work."' },
            ].map((t) => (
              <div key={t.name} className="bg-zinc-900/40 border border-zinc-800/40 rounded-2xl p-5 text-left hover:border-zinc-700/50 transition-all">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center text-white text-sm font-bold">
                    {t.name.charAt(0)}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-zinc-200">{t.name}</p>
                    <p className="text-xs text-zinc-500">{t.role}</p>
                  </div>
                </div>
                <p className="text-sm text-zinc-400 leading-relaxed">{t.text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {selectedPreviewProduct && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl p-6 space-y-5" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setSelectedPreviewProduct(null);
              }}
              className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-200 p-1 bg-zinc-800/50 hover:bg-zinc-800 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
            <div className={`aspect-[4/3] w-full bg-gradient-to-br ${selectedPreviewProduct.col} rounded-xl flex items-center justify-center relative overflow-hidden border border-zinc-800`}>
              <selectedPreviewProduct.icon className={`w-20 h-20 ${selectedPreviewProduct.iconCol} opacity-40`} />
            </div>
            <div>
              <span className="text-[10px] font-semibold text-purple-400 bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-full">
                {selectedPreviewProduct.cat}
              </span>
              <h3 className="text-xl font-bold text-zinc-100 mt-2">{selectedPreviewProduct.name}</h3>
              <p className="text-2xl font-extrabold text-purple-400 mt-2">${selectedPreviewProduct.price}</p>
              <p className="text-xs text-zinc-400 mt-3 leading-relaxed">
                This is a live preview item. In our full interactive sandbox, you can search the catalog, view detail pages, add products to your cart, and watch recommendations automatically adapt based on your behavior.
              </p>
            </div>
            <div className="pt-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedPreviewProduct(null);
                  onEnterDemo?.();
                }}
                className="w-full btn-primary py-3 text-sm font-semibold rounded-xl"
              >
                Try Full Interactive Demo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
