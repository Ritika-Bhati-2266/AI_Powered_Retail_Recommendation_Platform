import { useState, useEffect } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  Users,
  Activity,
  Package,
  Gift,
  BrainCircuit,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { formatSegmentLabel } from '../utils/formatSegmentLabel';
import type { SystemStats } from '../types';

const SEGMENT_COLORS: Record<string, string> = {
  cart_abandoner: '#f59e0b',
  high_value: '#10b981',
  brand_loyalist: '#8b5cf6',
  bargain_hunter: '#ec4899',
  new_user: '#3b82f6',
  lapsed: '#6b7280',
  window_shopper: '#06b6d4',
  power_user: '#f97316',
};

function getSegmentColor(segment: string): string {
  return SEGMENT_COLORS[segment] || '#a855f7';
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-2 shadow-xl">
        <p className="text-sm font-medium text-zinc-200">{formatSegmentLabel(data.segment)}</p>
        <p className="text-lg font-bold text-white">{data.count} customers</p>
        <p className="text-xs text-zinc-400">
          {data.percentage}% of total
        </p>
      </div>
    );
  }
  return null;
};

export default function AnalyticsPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<'pie' | 'bar'>('pie');
  const [assigning, setAssigning] = useState(false);
  const [assignMessage, setAssignMessage] = useState<string | null>(null);

  const fetchStats = () => {
    setLoading(true);
    setError(null);
    apiClient
      .getStats()
      .then(setStats)
      .catch((err) => setError(err.message || 'Failed to load stats'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleAssignOffers = async () => {
    setAssigning(true);
    setAssignMessage(null);
    try {
      const result = await apiClient.assignOffers();
      setAssignMessage(`Assigned ${result.assignments_count} offers`);
      fetchStats();
    } catch {
      setAssignMessage('Failed to assign offers');
    } finally {
      setAssigning(false);
    }
  };

  const chartData = stats
    ? stats.segment_distribution.map((s) => ({
        ...s,
        percentage: stats.total_customers > 0
          ? ((s.count / stats.total_customers) * 100).toFixed(1)
          : '0.0',
      }))
    : [];

  const totalSegmented = chartData.reduce((sum, s) => sum + s.count, 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">System Analytics</h2>
          <p className="text-sm text-zinc-500 mt-1">
            Overview of customer segments, consent rates, and system health
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleAssignOffers}
            disabled={assigning}
            className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition-all shadow-lg shadow-amber-600/20"
          >
            {assigning ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Gift className="w-4 h-4" />
            )}
            {assigning ? 'Assigning...' : 'Assign Offers'}
          </button>
          <button
            onClick={fetchStats}
            disabled={loading}
            className="btn-outline"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {assignMessage && (
        <div className="bg-amber-900/30 border border-amber-700/30 rounded-xl px-4 py-2">
          <p className="text-xs text-amber-300">{assignMessage}</p>
        </div>
      )}

      {error && (
        <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-8 text-center">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {loading && !stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-4 space-y-2">
              <div className="skeleton h-4 w-20" />
              <div className="skeleton h-8 w-16" />
            </div>
          ))}
        </div>
      )}

      {stats && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-4 h-4 text-blue-400" />
                <span className="metric-label">Total Customers</span>
              </div>
              <p className="metric-value text-lg">
                {stats.total_customers.toLocaleString()}
              </p>
            </div>
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-4 h-4 text-emerald-400" />
                <span className="metric-label">Consent Rate</span>
              </div>
              <p className="metric-value text-lg">{stats.consent_rate}%</p>
              <div className="mt-2 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full transition-all"
                  style={{ width: `${stats.consent_rate}%` }}
                />
              </div>
            </div>
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <BrainCircuit className="w-4 h-4 text-purple-400" />
                <span className="metric-label">Total Events</span>
              </div>
              <p className="metric-value text-lg">
                {stats.total_events.toLocaleString()}
              </p>
            </div>
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Package className="w-4 h-4 text-amber-400" />
                <span className="metric-label">Products</span>
              </div>
              <p className="metric-value text-lg">
                {stats.total_products.toLocaleString()}
              </p>
            </div>
          </div>

          <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider">
                  Segment Distribution
                </h3>
                <p className="text-xs text-zinc-500 mt-1">
                  {totalSegmented} of {stats.total_customers} customers have at least one segment
                </p>
              </div>
              <div className="flex items-center gap-1 bg-zinc-800 rounded-xl p-0.5">
                <button
                  onClick={() => setChartType('pie')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                    chartType === 'pie'
                      ? 'bg-purple-600 text-white shadow-sm'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  Pie
                </button>
                <button
                  onClick={() => setChartType('bar')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                    chartType === 'bar'
                      ? 'bg-purple-600 text-white shadow-sm'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  Bar
                </button>
              </div>
            </div>

            {chartData.length === 0 ? (
              <div className="text-center py-12">
                <Users className="w-8 h-8 text-zinc-700 mx-auto mb-2" />
                <p className="text-sm text-zinc-500">No segments assigned yet</p>
                <p className="text-xs text-zinc-600 mt-1">
                  Run "Assign Offers" to compute segments for all customers
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-4 lg:flex-row lg:gap-6">
                <div className="flex-1" style={{ height: 320 }}>
                  {chartType === 'pie' ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={chartData}
                          dataKey="count"
                          nameKey="segment"
                          cx="50%"
                          cy="50%"
                          outerRadius={120}
                          innerRadius={60}
                          paddingAngle={2}
                        >
                          {chartData.map((entry) => (
                            <Cell
                              key={entry.segment}
                              fill={getSegmentColor(entry.segment)}
                              stroke="rgba(0,0,0,0.2)"
                              strokeWidth={1}
                            />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                        <Legend
                          formatter={(value: string) => (
                            <span className="text-xs text-zinc-400">
                              {formatSegmentLabel(value)}
                            </span>
                          )}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData} layout="vertical" margin={{ left: 100 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                        <XAxis
                          type="number"
                          tick={{ fill: '#a1a1aa', fontSize: 12 }}
                          axisLine={{ stroke: '#27272a' }}
                        />
                        <YAxis
                          type="category"
                          dataKey="segment"
                          tick={{ fill: '#a1a1aa', fontSize: 12 }}
                          axisLine={{ stroke: '#27272a' }}
                          tickFormatter={(value: string) =>
                            value
                              .replace(/_/g, ' ')
                              .replace(/\b\w/g, (c) => c.toUpperCase())
                          }
                          width={120}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                          {chartData.map((entry) => (
                            <Cell
                              key={entry.segment}
                              fill={getSegmentColor(entry.segment)}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>

                {chartType === 'pie' && (
                  <div className="w-full lg:w-56 shrink-0 space-y-2">
                    {chartData.map((entry) => (
                      <div
                        key={entry.segment}
                        className="flex items-center justify-between p-2 rounded-xl bg-zinc-800/50"
                      >
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: getSegmentColor(entry.segment) }}
                          />
                          <span className="text-xs text-zinc-300">
                            {formatSegmentLabel(entry.segment)}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-xs font-medium text-zinc-200">
                            {entry.count}
                          </span>
                          <span className="text-xs text-zinc-500 ml-1">
                            ({entry.percentage}%)
                          </span>
                        </div>
                      </div>
                    ))}
                    <div className="flex items-center justify-between p-2 rounded-xl bg-zinc-800/50 border border-zinc-700/50">
                      <span className="text-xs font-medium text-zinc-400">Total</span>
                      <span className="text-xs font-semibold text-zinc-200">
                        {totalSegmented}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Gift className="w-4 h-4 text-amber-400" />
                <span className="metric-label">Total Offers</span>
              </div>
              <p className="metric-value text-lg">{stats.total_offers}</p>
            </div>
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Gift className="w-4 h-4 text-green-400" />
                <span className="metric-label">Active Offers</span>
              </div>
              <p className="metric-value text-lg">{stats.active_offers}</p>
            </div>
            <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-4 h-4 text-indigo-400" />
                <span className="metric-label">Offer Assignments</span>
              </div>
              <p className="metric-value text-lg">
                {stats.total_assignments.toLocaleString()}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
