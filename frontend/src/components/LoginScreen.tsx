import { useState, useCallback } from 'react';
import { Sparkles, Mail, ArrowRight, Loader2, AlertCircle, User, UserPlus, ArrowLeft, LogIn, ShoppingBag } from 'lucide-react';
import { apiClient } from '../api/client';
import type { CustomerFull } from '../types';

const CATEGORIES = [
  'Electronics', 'Clothing', 'Home & Kitchen', 'Books',
  'Sports', 'Beauty', 'Toys', 'Grocery',
];

interface LoginScreenProps {
  onLogin: (customer: CustomerFull) => void;
}

type Page = 'landing' | 'login' | 'signup';

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [page, setPage] = useState<Page>('landing');

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
      <div className="min-h-screen bg-surface flex items-center justify-center px-4">
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
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-6 backdrop-blur-sm">
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
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-6 backdrop-blur-sm">
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

          <div className="mt-6 bg-zinc-900/30 border border-zinc-800/30 rounded-xl p-4 text-center">
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
    <div className="min-h-screen bg-surface flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-purple-900/20 via-transparent to-transparent pointer-events-none" />

        <nav className="absolute top-0 left-0 right-0 flex items-center justify-between px-6 py-4 max-w-7xl mx-auto">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center">
              <ShoppingBag className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-purple-400">PersonalShop</span>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={goToLogin}
              className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Sign In
            </button>
            <button
              onClick={goToSignup}
              className="btn-primary text-sm px-5 py-2.5"
            >
              Get Started
            </button>
          </div>
        </nav>

        <div className="text-center max-w-3xl mx-auto px-4">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-medium mb-8">
            <Sparkles className="w-3.5 h-3.5" />
            AI-Powered Personalisation
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight leading-tight mb-6">
            The Store That{' '}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-pink-400 to-pink-300">
              Learns
            </span>{' '}
            You
          </h1>

          <p className="text-lg text-zinc-400 max-w-xl mx-auto mb-10 leading-relaxed">
            Every browse, every click — your store adapts in real time. 
            Discover products curated just for you by our AI engine.
          </p>

          <div className="flex items-center justify-center gap-4">
            <button
              onClick={goToSignup}
              className="btn-primary text-base px-8 py-4"
            >
              <UserPlus className="w-5 h-5" />
              Create Free Account
            </button>
            <button
              onClick={goToLogin}
              className="btn-outline text-base px-8 py-4"
            >
              <LogIn className="w-5 h-5" />
              Sign In
            </button>
          </div>

          <div className="mt-16 grid grid-cols-3 gap-8 max-w-lg mx-auto">
            {[
              { icon: Sparkles, label: 'Smart Picks', desc: 'AI that knows your taste' },
              { icon: ShoppingBag, label: 'Curated Shop', desc: 'Products handpicked for you' },
              { icon: ArrowRight, label: 'Real-Time', desc: 'Updates as you browse' },
            ].map((item) => (
              <div key={item.label} className="text-center">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center mx-auto mb-2">
                  <item.icon className="w-5 h-5 text-purple-400" />
                </div>
                <p className="text-sm font-semibold text-zinc-200">{item.label}</p>
                <p className="text-xs text-zinc-500 mt-0.5">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
