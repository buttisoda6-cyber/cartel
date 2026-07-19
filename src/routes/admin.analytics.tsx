import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  BarChart,
  Bar,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Download, Shield, Users, Clock3, MessageSquareMore, Activity } from "lucide-react";
import { adminAnalyticsService, type AdminAnalyticsReport } from "@/lib/api/adminAnalyticsService";

export const Route = createFileRoute("/admin/analytics")({
  component: AdminAnalyticsPage,
});

function AdminAnalyticsPage() {
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [data, setData] = useState<AdminAnalyticsReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setIsAdmin(sessionStorage.getItem("merchant_role") === "admin");
  }, []);

  useEffect(() => {
    if (isAdmin === false) {
      setLoading(false);
      return;
    }
    if (!isAdmin) return;

    (async () => {
      try {
        setLoading(true);
        setData(await adminAnalyticsService.getAnalytics());
      } catch (error) {
        console.error("Failed to load admin analytics:", error);
      } finally {
        setLoading(false);
      }
    })();
  }, [isAdmin]);

  const exportCsv = async () => {
    const result = await adminAnalyticsService.exportCsv();
    const blob = new Blob([result.csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "admin-analytics.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.weekly_snapshots.map((item) => ({
      label: `${item.window_days}d`,
      dau: item.daily_active_users,
      wau: item.weekly_active_users,
      mau: item.monthly_active_users,
      chats: item.ai_chat_usage,
    }));
  }, [data]);

  if (isAdmin === false) {
    return (
      <div className="mx-auto max-w-3xl rounded-3xl border border-border bg-card p-8 shadow-card">
        <div className="flex items-center gap-3">
          <Shield className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold text-foreground">Admin only</h1>
            <p className="text-sm text-muted-foreground">This dashboard is hidden from merchant accounts.</p>
          </div>
        </div>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="mx-auto max-w-7xl space-y-6">
        <h1 className="text-3xl font-bold text-foreground">Admin Analytics</h1>
        <p className="text-sm text-muted-foreground">Loading platform analytics...</p>
      </div>
    );
  }

  const { summary } = data;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            <Shield className="h-3.5 w-3.5" />
            Administrator Analytics
          </div>
          <h1 className="mt-3 text-3xl font-black tracking-tight text-foreground">Platform Adoption Dashboard</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            Track adoption, engagement, recommendation conversion, and AI usage across the store experience.
          </p>
        </div>
        <button
          onClick={exportCsv}
          className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-card"
        >
          <Download className="h-4 w-4" />
          Export CSV
        </button>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={<Users className="h-5 w-5 text-primary" />} label="Registered Merchants" value={summary.registered_merchants} />
        <StatCard icon={<Activity className="h-5 w-5 text-success" />} label="Daily / Weekly / Monthly Active" value={`${summary.daily_active_users} / ${summary.weekly_active_users} / ${summary.monthly_active_users}`} />
        <StatCard icon={<Clock3 className="h-5 w-5 text-warning" />} label="Avg Session Duration" value={`${summary.average_session_duration_minutes} mins`} />
        <StatCard icon={<MessageSquareMore className="h-5 w-5 text-primary" />} label="AI Chat Usage" value={summary.ai_chat_usage} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-3xl border border-border bg-card p-5 shadow-card">
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-foreground">Engagement Trends</h2>
            <p className="text-xs text-muted-foreground">Active users, AI chats, approval, and conversion snapshots.</p>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="dau" fill="#1A7A45" radius={[8, 8, 0, 0]} />
                <Bar dataKey="wau" fill="#E6B800" radius={[8, 8, 0, 0]} />
                <Bar dataKey="chats" fill="#2563EB" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-3xl border border-border bg-card p-5 shadow-card">
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-foreground">Recommendation Funnel</h2>
            <p className="text-xs text-muted-foreground">Approval and conversion rates from intervention tracking.</p>
          </div>
          <div className="space-y-4">
            <MetricRow label="Approval Rate" value={`${summary.recommendation_approval_rate}%`} />
            <MetricRow label="Conversion Rate" value={`${summary.recommendation_conversion_rate}%`} />
            <MetricRow label="Reports Generated" value={summary.reports_generated} />
            <MetricRow label="Returning Users" value={summary.returning_users} />
            <MetricRow label="Last Active" value={summary.last_active_timestamp ? new Date(summary.last_active_timestamp).toLocaleString() : "N/A"} />
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-3xl border border-border bg-card p-5 shadow-card">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Most Visited Pages</h2>
          <div className="space-y-3">
            {summary.most_visited_pages.map((item) => (
              <BarRow key={item.page} label={item.page} value={item.count} />
            ))}
          </div>
        </div>
        <div className="rounded-3xl border border-border bg-card p-5 shadow-card">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Most Clicked Features</h2>
          <div className="space-y-3">
            {summary.most_clicked_features.map((item) => (
              <BarRow key={item.action_type} label={item.action_type} value={item.count} />
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-3xl border border-border bg-card p-5 shadow-card">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Time Spent Per Page</h2>
          <div className="space-y-3">
            {summary.page_time_spent.map((item) => (
              <BarRow key={item.page} label={item.page} value={`${item.minutes} min`} />
            ))}
          </div>
        </div>
        <div className="rounded-3xl border border-border bg-card p-5 shadow-card">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Recent Activity</h2>
          <div className="space-y-3">
            {data.recent_activity.slice(0, 8).map((item, index) => (
              <div key={`${item.action_type}-${index}`} className="rounded-2xl bg-background/70 p-3 text-sm">
                <div className="font-medium text-foreground">{item.action_type}</div>
                <div className="text-xs text-muted-foreground">{item.action_description}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-border bg-card p-5 shadow-card">
        <h2 className="mb-4 text-lg font-semibold text-foreground">Recent Logins</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
              <tr>
                <th className="pb-3 pr-4">Username</th>
                <th className="pb-3 pr-4">Login</th>
                <th className="pb-3 pr-4">Logout</th>
                <th className="pb-3 pr-4">Device</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_logins.map((item, index) => (
                <tr key={`${item.username}-${index}`} className="border-t border-border">
                  <td className="py-3 pr-4 font-medium text-foreground">{item.username}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{new Date(item.login_time).toLocaleString()}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{item.logout_time ? new Date(item.logout_time).toLocaleString() : "Active"}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{item.device_info || "Unknown"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: ReactNode; label: string; value: string | number }) {
  return (
    <div className="rounded-3xl border border-border bg-card p-5 shadow-card">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
          <div className="mt-2 text-2xl font-black text-foreground">{value}</div>
        </div>
        <div className="rounded-2xl bg-background p-3">{icon}</div>
      </div>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between rounded-2xl bg-background/70 px-4 py-3">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold text-foreground">{value}</span>
    </div>
  );
}

function BarRow({ label, value }: { label: string; value: string | number }) {
  const numeric = typeof value === "number" ? value : Number.parseFloat(String(value)) || 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium text-foreground">{label}</span>
        <span className="text-muted-foreground">{value}</span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div className="h-2 rounded-full bg-primary" style={{ width: `${Math.min(100, numeric * 5 || 8)}%` }} />
      </div>
    </div>
  );
}