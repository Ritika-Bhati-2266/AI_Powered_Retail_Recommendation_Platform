import { useState, useCallback } from 'react';
import { Sparkles, Mail, ArrowRight, Loader2, AlertCircle, User, UserPlus, ArrowLeft, LogIn } from 'lucide-react';
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

  // Login state
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Signup state
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

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Branding */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-primary-500/25">
            <Sparkles className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100">
            Hyper-Personalisation Engine
          </h1>
          <p className="text-sm text-slate-400 mt-2">
            {page === 'landing'
              ? 'Sign in or create an account to get started'
              : page === 'login'
                ? 'Sign in to see your personalised recommendations and offers'
                : 'Create an account to get started'}
          </p>
        </div>

        {page === 'landing' ? (
          /* ── Landing Choice ──────────────────────────────────────── */
          <div className="space-y-4">
            <button
              onClick={goToLogin}
              className="w-full card p-6 flex items-center gap-4 hover:border-primary-500/50 transition-all group text-left"
            >
              <div className="w-12 h-12 rounded-xl bg-primary-500/10 flex items-center justify-center shrink-0 group-hover:bg-primary-500/20 transition-colors">
                <LogIn className="w-6 h-6 text-primary-400" />
              </div>
              <div>
                <p className="text-base font-semibold text-slate-100">Sign In</p>
                <p className="text-sm text-slate-400">Existing user — enter your email to view your personalised experience</p>
              </div>
              <ArrowRight className="w-5 h-5 text-slate-500 group-hover:text-primary-400 ml-auto shrink-0 transition-colors" />
            </button>

            <button
              onClick={goToSignup}
              className="w-full card p-6 flex items-center gap-4 hover:border-emerald-500/50 transition-all group text-left"
            >
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center shrink-0 group-hover:bg-emerald-500/20 transition-colors">
                <UserPlus className="w-6 h-6 text-emerald-400" />
              </div>
              <div>
                <p className="text-base font-semibold text-slate-100">Create Account</p>
                <p className="text-sm text-slate-400">New here? Set up your profile and preferences</p>
              </div>
              <ArrowRight className="w-5 h-5 text-slate-500 group-hover:text-emerald-400 ml-auto shrink-0 transition-colors" />
            </button>
          </div>
        ) : page === 'login' ? (
          /* ── Login Card ──────────────────────────────────────────── */
          <div className="card p-6">
            <button
              onClick={goToLanding}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 mb-4 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back
            </button>

            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    autoFocus
                    className="w-full bg-slate-800 text-slate-100 placeholder-slate-500 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              {error && (
                <div className="flex flex-col gap-3 bg-red-900/20 border border-red-800/30 rounded-lg px-4 py-3">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                    <p className="text-sm text-red-300">{error}</p>
                  </div>
                  <button
                    type="button"
                    onClick={switchToSignup}
                    className="flex items-center justify-center gap-2 px-3 py-2 bg-emerald-700/40 hover:bg-emerald-700/60 text-emerald-300 text-sm font-medium rounded-lg transition-all border border-emerald-700/30"
                  >
                    <UserPlus className="w-4 h-4" />
                    Create Account with This Email
                  </button>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || !email.trim()}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-primary-600/20"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ArrowRight className="w-4 h-4" />
                )}
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            <p className="text-xs text-slate-500 mt-4 text-center">
              No password required. Enter your email to view your personalised experience.
            </p>
          </div>
        ) : (
          /* ── Signup Card ─────────────────────────────────────────── */
          <div className="card p-6">
            <button
              onClick={goToLanding}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 mb-4 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back
            </button>

            <form onSubmit={handleSignupSubmit} className="space-y-4">
              <div>
                <label htmlFor="signup-name" className="block text-sm font-medium text-slate-300 mb-1.5">
                  Your Name
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    id="signup-name"
                    type="text"
                    value={signupName}
                    onChange={(e) => setSignupName(e.target.value)}
                    placeholder="Jane Smith"
                    required
                    autoFocus
                    className="w-full bg-slate-800 text-slate-100 placeholder-slate-500 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="signup-email" className="block text-sm font-medium text-slate-300 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    id="signup-email"
                    type="email"
                    value={signupEmail}
                    onChange={(e) => setSignupEmail(e.target.value)}
                    placeholder="jane@example.com"
                    required
                    className="w-full bg-slate-800 text-slate-100 placeholder-slate-500 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              {signupError && (
                <div className="flex items-start gap-2 bg-red-900/20 border border-red-800/30 rounded-lg px-4 py-3">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <p className="text-sm text-red-300">{signupError}</p>
                </div>
              )}

              {/* Category Preferences */}
              <div>
                <p className="text-xs font-medium text-slate-400 mb-2">
                  Choose categories you're interested in (optional — helps us personalise)
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
                            ? 'bg-primary-500/20 border-primary-500/50 text-primary-300'
                            : 'bg-slate-800/50 border-slate-700/50 text-slate-400 hover:border-slate-600 hover:text-slate-300'
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
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-emerald-600/20"
              >
                {signupLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <UserPlus className="w-4 h-4" />
                )}
                {signupLoading ? 'Creating Account...' : 'Create Account'}
              </button>
            </form>

            <p className="text-xs text-slate-500 mt-4 text-center">
              Your account will be created with consent enabled. You'll get a Welcome offer and personalised recommendations.
            </p>
          </div>
        )}

        {/* Hint */}
        <div className="mt-6 card p-4 text-center">
          <p className="text-xs text-slate-400">
            {page === 'landing'
              ? 'Choose an option above to sign in or create a new account.'
              : page === 'login'
                ? 'Enter your email to sign in. New users can create an account from the main screen.'
                : 'Fill in your name and email to create a new account instantly.'}
          </p>
        </div>
      </div>
    </div>
  );
}
