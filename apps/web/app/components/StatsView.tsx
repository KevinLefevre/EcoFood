'use client';

import { useEffect, useState, useMemo } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer
} from 'recharts';

type StatPoint = {
    label: string;
    mean_calories: number;
    mean_co2_per_meal: number;
    total_co2: number;
};

type StatsResponse = {
    weekly: StatPoint[];
    monthly: StatPoint[];
    yearly: StatPoint[];
};

type Household = {
    id: number;
    name: string;
};

type ViewMode = 'weekly' | 'monthly' | 'yearly';

export default function StatsView({ apiBaseUrl }: { apiBaseUrl: string }) {
    const [households, setHouseholds] = useState<Household[]>([]);
    const [selectedHouseholdId, setSelectedHouseholdId] = useState<number | null>(null);
    const [stats, setStats] = useState<StatsResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [insight, setInsight] = useState<string | null>(null);
    const [insightLoading, setInsightLoading] = useState(false);
    const [viewMode, setViewMode] = useState<ViewMode>('weekly');
    const [selectedYear, setSelectedYear] = useState<string>('');

    useEffect(() => {
        async function fetchHouseholds() {
            try {
                const res = await fetch(`${apiBaseUrl}/households`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.length > 0) {
                        setHouseholds(data);
                        setSelectedHouseholdId(data[0].id);
                    }
                }
            } catch (err) {
                console.error('Failed to fetch households', err);
            }
        }
        fetchHouseholds();
    }, [apiBaseUrl]);

    useEffect(() => {
        if (!selectedHouseholdId) return;

        async function fetchStats() {
            setLoading(true);
            setError(null);
            setInsight(null); // Reset insight on household change
            try {
                const res = await fetch(`${apiBaseUrl}/households/${selectedHouseholdId}/stats`);
                if (!res.ok) {
                    throw new Error(`Failed to load stats (${res.status})`);
                }
                const data: StatsResponse = await res.json();
                setStats(data);

                // Default to the latest year if available
                if (data.yearly.length > 0) {
                    setSelectedYear(data.yearly[data.yearly.length - 1].label);
                } else {
                    setSelectedYear(new Date().getFullYear().toString());
                }
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load stats');
            } finally {
                setLoading(false);
            }
        }
        fetchStats();
    }, [apiBaseUrl, selectedHouseholdId]);

    const generateInsight = async () => {
        if (!selectedHouseholdId) return;
        setInsightLoading(true);
        try {
            const res = await fetch(`${apiBaseUrl}/households/${selectedHouseholdId}/stats/insights`, {
                method: 'POST'
            });
            if (res.ok) {
                const data = await res.json();
                setInsight(data.insight);
            }
        } catch (err) {
            console.error('Failed to generate insight', err);
        } finally {
            setInsightLoading(false);
        }
    };

    const availableYears = useMemo(() => {
        if (!stats) return [];
        return stats.yearly.map(p => p.label);
    }, [stats]);

    const filteredStats = useMemo(() => {
        if (!stats || !selectedYear) return { weekly: [], monthly: [], yearly: [] };

        return {
            weekly: stats.weekly.filter(p => p.label.startsWith(selectedYear)),
            monthly: stats.monthly.filter(p => p.label.startsWith(selectedYear)),
            yearly: stats.yearly // Always show full history for yearly view
        };
    }, [stats, selectedYear]);

    const summary = useMemo(() => {
        if (!stats) return null;

        // Total CO2 (All Time) - Sum of all yearly totals
        const totalCo2AllTime = stats.yearly.reduce((acc, curr) => acc + curr.total_co2, 0);

        // Total CO2 (Year) - For the selected year
        const selectedYearStats = stats.yearly.find(p => p.label === selectedYear);
        const totalCo2Year = selectedYearStats ? selectedYearStats.total_co2 : 0;

        // Avg CO2/Week (Selected Year)
        // Calculate average of all weeks in the selected year
        const weeksInYear = stats.weekly.filter(p => p.label.startsWith(selectedYear));
        const avgCo2Week = weeksInYear.length
            ? Math.round(weeksInYear.reduce((acc, curr) => acc + curr.total_co2, 0) / weeksInYear.length)
            : 0;

        return { totalCo2AllTime, totalCo2Year, avgCo2Week };
    }, [stats, selectedYear]);

    if (!selectedHouseholdId) {
        return <div className="p-8 text-center text-slate-400">Loading household...</div>;
    }

    if (loading) {
        return <div className="p-8 text-center text-slate-400">Loading stats...</div>;
    }

    if (error) {
        return <div className="p-8 text-center text-rose-400">Error: {error}</div>;
    }

    if (!stats) {
        return <div className="p-8 text-center text-slate-400">No stats available</div>;
    }

    return (
        <div className="space-y-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <h2 className="text-2xl font-semibold text-slate-200">Household Statistics</h2>
                <div className="flex flex-wrap gap-4">
                    <button
                        onClick={generateInsight}
                        disabled={insightLoading}
                        className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
                    >
                        {insightLoading ? 'Analyzing...' : 'Generate Insight'}
                    </button>

                    {/* Year Selector */}
                    {availableYears.length > 0 && (
                        <select
                            value={selectedYear}
                            onChange={(e) => setSelectedYear(e.target.value)}
                            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-300"
                        >
                            {availableYears.map(year => (
                                <option key={year} value={year}>{year}</option>
                            ))}
                        </select>
                    )}

                    <select
                        value={selectedHouseholdId}
                        onChange={(e) => setSelectedHouseholdId(Number(e.target.value))}
                        className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-300"
                    >
                        {households.map((h) => (
                            <option key={h.id} value={h.id}>
                                {h.name}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {insight && (
                <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4 text-indigo-200">
                    <div className="flex items-start gap-3">
                        <span className="text-xl">✨</span>
                        <p>{insight}</p>
                    </div>
                </div>
            )}

            {summary && (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <SummaryCard label="Total CO2 (All Time)" value={summary.totalCo2AllTime} unit="kg" color="text-emerald-400" />
                    <SummaryCard label={`Total CO2 (${selectedYear})`} value={summary.totalCo2Year} unit="kg" color="text-emerald-400" />
                    <SummaryCard label={`Avg CO2 / Week (${selectedYear})`} value={summary.avgCo2Week} unit="kg" color="text-cyan-400" />
                </div>
            )}

            <div className="space-y-4">
                <div className="flex justify-center">
                    <div className="inline-flex rounded-lg border border-slate-700 bg-slate-900/50 p-1">
                        {(['weekly', 'monthly', 'yearly'] as const).map((mode) => (
                            <button
                                key={mode}
                                onClick={() => setViewMode(mode)}
                                className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${viewMode === mode
                                        ? 'bg-slate-700 text-white'
                                        : 'text-slate-400 hover:text-slate-200'
                                    }`}
                            >
                                {mode.charAt(0).toUpperCase() + mode.slice(1)}
                            </button>
                        ))}
                    </div>
                </div>

                {viewMode === 'weekly' && <StatsSection title={`Weekly Trends (${selectedYear})`} data={filteredStats.weekly} />}
                {viewMode === 'monthly' && <StatsSection title={`Monthly Trends (${selectedYear})`} data={filteredStats.monthly} />}
                {viewMode === 'yearly' && <StatsSection title="Yearly Trends (All Time)" data={filteredStats.yearly} />}
            </div>
        </div>
    );
}

function SummaryCard({ label, value, unit, color }: { label: string; value: number; unit: string; color: string }) {
    return (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
            <div className="text-sm font-medium text-slate-400">{label}</div>
            <div className={`mt-2 text-3xl font-bold ${color}`}>
                {value} <span className="text-lg font-normal text-slate-500">{unit}</span>
            </div>
        </div>
    );
}

function StatsSection({ title, data }: { title: string; data: StatPoint[] }) {
    if (!data.length) return (
        <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 p-12 text-center text-slate-500">
            No data available for {title.toLowerCase()}.
        </div>
    );

    return (
        <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 p-6">
            <h3 className="mb-6 text-lg font-medium text-cyan-100">{title}</h3>
            <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                        <XAxis
                            dataKey="label"
                            stroke="#94a3b8"
                            tick={{ fill: '#94a3b8' }}
                            tickLine={{ stroke: '#94a3b8' }}
                        />
                        <YAxis
                            yAxisId="left"
                            orientation="left"
                            stroke="#10b981"
                            tick={{ fill: '#10b981' }}
                            tickLine={{ stroke: '#10b981' }}
                            label={{ value: 'CO2 (kg)', angle: -90, position: 'insideLeft', fill: '#10b981' }}
                        />
                        <YAxis
                            yAxisId="right"
                            orientation="right"
                            stroke="#f59e0b"
                            tick={{ fill: '#f59e0b' }}
                            tickLine={{ stroke: '#f59e0b' }}
                            label={{ value: 'Calories', angle: 90, position: 'insideRight', fill: '#f59e0b' }}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9' }}
                            itemStyle={{ color: '#f1f5f9' }}
                        />
                        <Legend />
                        <Line yAxisId="left" type="monotone" dataKey="total_co2" name="Total CO2 (kg)" stroke="#10b981" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                        <Line yAxisId="right" type="monotone" dataKey="mean_calories" name="Avg Calories" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
