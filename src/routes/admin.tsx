import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, CalendarDays, ChevronLeft, ChevronRight, Clock3, Users } from "lucide-react";
import { adminService, type ScreenTimeData, type TrafficData } from "@/lib/api";

export const Route = createFileRoute("/admin")({
  component: AdminDashboard,
});

type TrafficBand = {
  label: string;
  hours: number[];
  title: string;
};

// Rank-based shading for the screen time bars (darkest = highest usage)
const BAR_OPACITIES = [1, 0.75, 0.5, 0.3];
const BAR_COLOR = "#16a34a";

function AdminDashboard() {
  const [weekOffset, setWeekOffset] = useState(0);
  const [screenTime, setScreenTime] = useState<ScreenTimeData | null>(null);
  const [traffic, setTraffic] = useState<TrafficData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        setLoading(true);
        const [screenTimeData, trafficData] = await Promise.all([
          adminService.getScreenTime(weekOffset),
          adminService.getTraffic(weekOffset),
        ]);

        if (cancelled) return;

        setScreenTime(screenTimeData);
        setTraffic(trafficData);
        setError(null);
      } catch (loadError) {
        console.error("Failed to load admin dashboard:", loadError);
        if (!cancelled) {
          setError("Failed to load admin dashboard data.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [weekOffset]);

  const weekLabel = traffic?.week_label ?? screenTime?.week_label ?? "Loading week...";

  const screenTimeRows = useMemo(() => {
    return [...(screenTime?.users ?? [])].sort((left, right) => right.screentime_minutes - left.screentime_minutes);
  }, [screenTime]);

  const screenTimeMax = useMemo(() => {
    return Math.max(1, ...screenTimeRows.map((row) => row.screentime_minutes));
  }, [screenTimeRows]);

  const trafficChartData = useMemo(() => {
    return (traffic?.points ?? []).map((point) => ({
      hour: point.hour,
      label: point.time_label,
      traffic: point.traffic,
      period: getPeriodOfDay(point.hour),
    }));
  }, [traffic]);

  // Peaks are now placed directly on the chart (dot + label) instead of separate cards
  const trafficPeaks = useMemo(() => {
    const source = traffic?.peaks?.length
      ? traffic.peaks.map((peak) => {
          const matched = trafficChartData.find((point) => point.label === peak.time_label);
          return {
            hour: matched?.hour ?? 0,
            timeLabel: peak.time_label,
            traffic: peak.traffic,
            period: peak.period ?? (matched ? getPeriodOfDay(matched.hour) : ""),
          };
        })
      : [...trafficChartData]
          .sort((left, right) => right.traffic - left.traffic)
          .map((point) => ({
            hour: point.hour,
            timeLabel: point.label,
            traffic: point.traffic,
            period: point.period,
          }));

    return source.slice(0, 2).map((point, index) => ({
      title: `Peak ${index + 1}`,
      hour: point.hour,
      timeLabel: point.timeLabel,
      traffic: point.traffic,
      period: point.period,
    }));
  }, [traffic?.peaks, trafficChartData]);

  const trafficBands = useMemo<TrafficBand[]>(
    () => [
      { label: "Morning activity", hours: [5, 6, 7, 8, 9, 10, 11], title: "Morning activity" },
      { label: "Midday peak", hours: [12, 13, 14, 15, 16], title: "Midday peak" },
      { label: "Evening dip", hours: [17, 18, 19, 20], title: "Evening dip" },
      { label: "Night peak", hours: [21, 22, 23, 0, 1, 2, 3, 4], title: "Night peak" },
    ],
    []
  );

  const trafficBandTiles = useMemo(() => {
    return trafficBands.map((band) => {
      const relevant = trafficChartData.filter((point) => band.hours.includes(point.hour));
      const peak = relevant.reduce<{ label: string; traffic: number } | null>((best, current) => {
        if (!best || current.traffic > best.traffic) {
          return { label: current.label, traffic: current.traffic };
        }
        return best;
      }, null);

      return {
        title: band.title,
        value: peak ? `${peak.label} spike` : "No activity",
      };
    });
  }, [trafficBands, trafficChartData]);

  if (loading && !screenTime && !traffic) {
    return (
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-foreground">Admin Control Center</h1>
          <p className="mt-1 text-sm text-muted-foreground">Loading user activity and traffic analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="rounded-3xl border border-border bg-card p-6 shadow-card">
          <h1 className="text-2xl font-bold text-foreground">Admin Control Center</h1>
          <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-black tracking-tight text-foreground">Admin Control Center</h1>
        <p className="text-sm text-muted-foreground">Monitor user analytics and website traffic patterns.</p>
      </div>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.15fr]">
        <div className="rounded-[28px] border border-border bg-card p-5 shadow-card">
          <div className="mb-5 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-2xl bg-emerald-50 p-2 text-emerald-700">
                <Users className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-foreground">User Activity Screen Time</h2>
                <p className="text-xs text-muted-foreground">Ranked login activity across the selected week.</p>
              </div>
            </div>

            <div className="inline-flex items-center gap-2 rounded-2xl border border-border bg-background px-3 py-2 text-sm text-muted-foreground">
              <button
                type="button"
                onClick={() => setWeekOffset((current) => current + 1)}
                className="rounded-full p-1 transition-colors hover:bg-muted"
                aria-label="Previous week"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <CalendarDays className="h-4 w-4" />
              <span className="max-w-[9rem] text-center text-xs font-semibold text-foreground md:max-w-none">
                {weekLabel}
              </span>
              <button
                type="button"
                onClick={() => setWeekOffset((current) => Math.max(0, current - 1))}
                disabled={weekOffset === 0}
                className="rounded-full p-1 transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Next week"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={screenTimeRows} layout="vertical" margin={{ top: 6, right: 16, left: 12, bottom: 0 }} barCategoryGap="32%">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(148,163,184,0.18)" />
                <XAxis type="number" hide domain={[0, screenTimeMax]} />
                <YAxis
                  type="category"
                  dataKey="username"
                  width={95}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#475569", fontSize: 12, fontWeight: 500 }}
                />
                <Tooltip
                  cursor={{ fill: "rgba(16,185,129,0.06)" }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const row = payload[0].payload as ScreenTimeData["users"][number];
                    return (
                      <div className="rounded-2xl border border-border bg-card px-3 py-2 text-sm shadow-card">
                        <div className="font-semibold text-foreground">{row.username}</div>
                        <div className="text-muted-foreground">
                          {row.screentime_hours.toFixed(2)} hrs ({row.screentime_minutes.toFixed(1)}m)
                        </div>
                      </div>
                    );
                  }}
                />
                <Bar dataKey="screentime_minutes" radius={[0, 0, 0, 0]}>
                  {screenTimeRows.map((row, index) => (
                    <Cell
                      key={row.username}
                      fill={BAR_COLOR}
                      fillOpacity={BAR_OPACITIES[index] ?? BAR_OPACITIES[BAR_OPACITIES.length - 1]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-5">
            <div className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Screentime Details</div>
            <div className="divide-y divide-border">
              {screenTimeRows.map((item) => (
                <div key={item.username} className="flex items-center justify-between gap-3 py-2.5">
                  <div className="flex min-w-0 items-center gap-2">
                    <Clock3 className="h-4 w-4 shrink-0 text-emerald-700" />
                    <span className="truncate text-sm font-semibold text-foreground">{item.username}</span>
                  </div>
                  <div className="shrink-0 text-sm text-muted-foreground">
                    {item.screentime_hours.toFixed(2)} hrs ({item.screentime_minutes.toFixed(1)}m)
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-[28px] border border-border bg-card p-5 shadow-card">
          <div className="mb-4 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-2xl bg-emerald-50 p-2 text-emerald-700">
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-foreground">General Website Traffic Pattern</h2>
                <p className="text-xs text-muted-foreground">Hourly activity derived from login sessions for the selected week.</p>
              </div>
            </div>

            <div className="inline-flex items-center gap-2 rounded-2xl border border-border bg-background px-3 py-2 text-xs text-muted-foreground">
              <CalendarDays className="h-4 w-4" />
              <span>{weekLabel}</span>
            </div>
          </div>

          <div className="h-[380px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trafficChartData} margin={{ top: 36, right: 18, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="trafficFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#16a34a" stopOpacity={0.32} />
                    <stop offset="95%" stopColor="#16a34a" stopOpacity={0.03} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(148,163,184,0.14)" />
                <XAxis
                  dataKey="hour"
                  type="number"
                  domain={[0, 23]}
                  ticks={[0, 3, 6, 9, 12, 15, 18, 21]}
                  tickFormatter={(hour) => formatHourLabel(hour)}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#64748b", fontSize: 12 }}
                />
                <YAxis hide />
                <Tooltip
                  cursor={{ stroke: "rgba(22,163,74,0.16)", strokeWidth: 1 }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const point = payload[0].payload as TrafficData["points"][number];
                    return (
                      <div className="rounded-2xl border border-border bg-card px-3 py-2 text-sm shadow-card">
                        <div className="font-semibold text-foreground">{point.time_label}</div>
                        <div className="text-muted-foreground">{point.traffic} active visits</div>
                      </div>
                    );
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="traffic"
                  stroke="#15803d"
                  strokeWidth={2.5}
                  fill="url(#trafficFill)"
                  dot={{ r: 3, strokeWidth: 2, fill: "#fff", stroke: "#15803d" }}
                  activeDot={{ r: 6, strokeWidth: 0, fill: "#15803d" }}
                />
                {trafficPeaks.map((peak) => (
                  <ReferenceDot
                    key={peak.title}
                    x={peak.hour}
                    y={peak.traffic}
                    r={5}
                    fill="#15803d"
                    stroke="#fff"
                    strokeWidth={2}
                    label={{
                      value: `${peak.title}: ${peak.timeLabel} (${peak.period})`,
                      position: "top",
                      fill: "#0f172a",
                      fontSize: 12,
                      fontWeight: 700,
                    }}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {trafficBandTiles.map((tile) => (
              <div key={tile.title} className="rounded-2xl border border-border bg-background/70 p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{tile.title}</div>
                <div className="mt-2 text-sm font-bold text-foreground">{tile.value}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function formatHourLabel(hour: number) {
  const period = hour < 12 ? "AM" : "PM";
  const displayHour = hour % 12 || 12;
  return `${displayHour} ${period}`;
}

function getPeriodOfDay(hour: number) {
  if (hour >= 5 && hour < 12) return "Morning";
  if (hour >= 12 && hour < 17) return "Afternoon";
  if (hour >= 17 && hour < 21) return "Evening";
  return "Night";
}
