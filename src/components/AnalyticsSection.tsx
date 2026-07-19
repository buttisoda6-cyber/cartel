import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Area,
  AreaChart,
  Legend,
} from "recharts";
import { analyticsService, type Analytics } from "@/lib/api/analyticsService";
import {
  analyticsService as offerAnalyticsService,
  type Last7DaysActivity,
  type OfferAnalytics,
  type AppUsageLog,
} from "@/lib/api/activityService";
import { adminService, type BroadcastPerformanceResponse } from "@/lib/api";
import {
  BarChart3,
  CreditCard,
  History,
  Megaphone,
  PackageSearch,
  Sparkles,
  TrendingUp,
  Wallet,
  Trophy,
  Zap,
  Target,
  Star,
  Flame,
  Crown,
  Award,
  ArrowUpRight,
  ArrowDownRight,
  Radio,
  DollarSign,
} from "lucide-react";

export function AnalyticsSection({ embedded = false }: { embedded?: boolean }) {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [offerSummary, setOfferSummary] = useState<OfferAnalytics | null>(null);
  const [activityTrend, setActivityTrend] = useState<Last7DaysActivity[]>([]);
  const [recentActivity, setRecentActivity] = useState<AppUsageLog[]>([]);
  const [broadcastPerformance, setBroadcastPerformance] = useState<BroadcastPerformanceResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingBroadcast, setLoadingBroadcast] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setLoadingBroadcast(true);
        const [analyticsData, offerSummaryData, activityTrendData, recentActivityData, broadcastData] = await Promise.all([
          analyticsService.get(),
          offerAnalyticsService.getOfferSummary(),
          offerAnalyticsService.getLast7DaysActivity(),
          offerAnalyticsService.getRecentActivity(undefined, 6),
          adminService.getBroadcastPerformance(),
        ]);
        setAnalytics(analyticsData);
        setOfferSummary(offerSummaryData);
        setActivityTrend(activityTrendData);
        setRecentActivity(recentActivityData);
        setBroadcastPerformance(broadcastData);
        setError(null);
      } catch (err) {
        console.error("Failed to load analytics:", err);
        setError("Failed to load analytics data");
      } finally {
        setLoading(false);
        setLoadingBroadcast(false);
      }
    };

    fetchData();
  }, []);

  const broadcastStats = useMemo(() => {
    if (!broadcastPerformance.length) return { totalGrowth: 0, totalRevGrowth: 0, positiveCount: 0 };
    const totalGrowth = broadcastPerformance.reduce((sum, item) => sum + item.qty_growth, 0);
    const totalRevGrowth = broadcastPerformance.reduce((sum, item) => sum + item.rev_growth, 0);
    const positiveCount = broadcastPerformance.filter((item) => item.qty_growth > 0).length;
    return { totalGrowth, totalRevGrowth, positiveCount };
  }, [broadcastPerformance]);

  const enhancedDailySales = useMemo(() => {
    if (!analytics) return [];
    return analytics.dailySales.map((day, index, list) => {
      const previous = index === 0 ? day.value : list[index - 1].value;
      return {
        ...day,
        delta: day.value - previous,
      };
    });
  }, [analytics]);

  const kpi = useMemo(() => {
    if (!analytics) return null;
    const totalSales = analytics.dailySales.reduce((sum, item) => sum + item.value, 0);
    const avgDailySales = totalSales / Math.max(analytics.dailySales.length, 1);
    const bestDay = analytics.dailySales.reduce(
      (best, current) => (current.value > best.value ? current : best),
      analytics.dailySales[0]
    );
    const lowestSlowMover = analytics.slowMovers[0];

    return {
      totalSales,
      avgDailySales,
      bestDay,
      lowestSlowMover,
    };
  }, [analytics]);

  const campaignCards = useMemo(() => {
    if (!offerSummary) return [];
    return [
      {
        label: "Offers Approved",
        value: String(offerSummary.totalOffersApproved),
        helper: "Promotions created so far",
        icon: <Sparkles className="w-5 h-5 text-primary" />,
      },
      {
        label: "Broadcasts Sent",
        value: String(offerSummary.totalBroadcastsSent),
        helper: "WhatsApp campaigns executed",
        icon: <Megaphone className="w-5 h-5 text-success" />,
      },
      {
        label: "Customers Reached",
        value: offerSummary.totalCustomersReached.toLocaleString("en-IN"),
        helper: "Total campaign reach",
        icon: <Wallet className="w-5 h-5 text-warning" />,
      },
      {
        label: "Avg Reach / Broadcast",
        value: `${offerSummary.averageRecipientsPerBroadcast.toFixed(1)}`,
        helper: "Audience size per send",
        icon: <CreditCard className="w-5 h-5 text-primary" />,
      },
    ];
  }, [offerSummary]);

  // Gamification: Calculate achievements and streaks
  const gamification = useMemo(() => {
    if (!analytics || !offerSummary) return null;
    
    const totalSales = analytics.dailySales.reduce((sum, item) => sum + item.value, 0);
    const avgDailySales = totalSales / Math.max(analytics.dailySales.length, 1);
    
    // Calculate level based on total sales (every 500k = 1 level)
    const level = Math.floor(totalSales / 500000) + 1;
    
    // Calculate XP (experience points) for progress bar
    const xpInLevel = (totalSales % 500000) / 500000;
    
    // Calculate streaks
    let offerStreak = 0;
    let broadcastStreak = 0;
    
    // Achievements unlocked
    const achievements = [];
    if (offerSummary.totalOffersApproved >= 5) achievements.push({ name: "Offer Master", icon: "🎯" });
    if (offerSummary.totalBroadcastsSent >= 10) achievements.push({ name: "Broadcast King", icon: "📢" });
    if (offerSummary.totalCustomersReached >= 1000) achievements.push({ name: "People's Choice", icon: "👑" });
    if (totalSales >= 1000000) achievements.push({ name: "Million Maker", icon: "💰" });
    if (analytics.fastMovers.length >= 3) achievements.push({ name: "Product Wizard", icon: "✨" });
    
    // Calculate goal progress (example: 2M sales target)
    const salesTarget = 2000000;
    const salesProgress = (totalSales / salesTarget) * 100;
    
    return {
      level,
      xpInLevel: Math.round(xpInLevel * 100),
      offerStreak,
      broadcastStreak,
      achievements: achievements.slice(0, 3),
      salesProgress: Math.min(salesProgress, 100),
      nextLevelSales: 500000 * level,
      currentLevelSales: 500000 * (level - 1),
    };
  }, [analytics, offerSummary]);

  if (loading) {
    return (
      <div className="space-y-6">
        {!embedded && (
          <div>
            <h1 className="text-3xl font-bold text-foreground">Analytics</h1>
            <p className="text-sm text-muted-foreground mt-1">Loading store performance...</p>
          </div>
        )}
      </div>
    );
  }

  if (error || !analytics || !kpi) {
    return (
      <div className="space-y-6">
        {!embedded && (
          <div>
            <h1 className="text-3xl font-bold text-foreground">Analytics</h1>
          </div>
        )}
        <div className="bg-alert/10 border border-alert rounded-xl p-6 text-alert">
          <p className="font-semibold">{error || "Failed to load analytics"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {!embedded && (
        <section
          className="rounded-[28px] shadow-card overflow-hidden text-white relative"
          style={{ background: "linear-gradient(135deg, #1A3A2A 0%, #1A7A45 52%, #D9A617 135%)" }}
        >
          <div className="absolute -right-10 -top-10 w-56 h-56 rounded-full bg-white/10" />
          <div className="relative p-6 md:p-8">
            <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full bg-white/12 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]">
                  <BarChart3 className="w-3.5 h-3.5" />
                  Store Performance
                </div>
                <h1 className="mt-3 text-3xl md:text-4xl font-black tracking-tight flex items-center gap-2">
                  Analytics Dashboard
                  {gamification && (
                    <span className="inline-flex items-center gap-1 bg-white/20 px-3 py-1 rounded-full text-lg font-bold">
                      <Crown className="w-5 h-5" />
                      Lvl {gamification.level}
                    </span>
                  )}
                </h1>
                <p className="mt-2 text-sm md:text-base text-white/80 max-w-2xl">
                  Daily sales, payment behavior, product movement, and campaign performance in one place.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 md:min-w-[360px]">
                <HeroMetric label="7-Day Sales" value={formatLakh(kpi.totalSales)} />
                <HeroMetric label="Avg Daily Sales" value={formatCurrency(kpi.avgDailySales)} />
                <HeroMetric label="Best Day" value={`${kpi.bestDay.day} • ${formatCurrency(kpi.bestDay.value)}`} />
                <HeroMetric label="Slowest Mover" value={kpi.lowestSlowMover ? `${kpi.lowestSlowMover.name} • ${kpi.lowestSlowMover.qty} qty` : "—"} />
              </div>
            </div>
          </div>
        </section>
      )}

      {embedded && (
        <div>
          <h2 className="text-2xl font-bold text-foreground">Business Analytics</h2>
          <p className="text-sm text-muted-foreground mt-1">Sales, payments, movers, and campaign performance inside your main dashboard.</p>
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {campaignCards.map((card) => (
          <div key={card.label} className="rounded-2xl bg-card shadow-card p-5 border border-border">
            <div className="flex items-center justify-between">
              <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{card.label}</div>
              {card.icon}
            </div>
            <div className="mt-3 text-3xl font-bold text-foreground">{card.value}</div>
            <div className="mt-1 text-sm text-muted-foreground">{card.helper}</div>
          </div>
        ))}
      </section>

      {/* Gamification Section */}
      {gamification && (
        <section className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
          {/* Level & XP Card */}
          <div className="rounded-2xl bg-card shadow-card border border-border p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-2xl font-bold text-foreground flex items-center gap-2">
                  <Crown className="w-6 h-6 text-warning" />
                  Level {gamification.level}
                </h3>
                <p className="text-xs text-muted-foreground mt-1">Merchant Experience</p>
              </div>
              <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center">
                <span className="text-3xl font-bold text-primary">{gamification.level}</span>
              </div>
            </div>

            {/* XP Progress Bar */}
            <div className="space-y-2 mb-6">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-muted-foreground">Level Progress</span>
                <span className="text-primary">{gamification.xpInLevel}%</span>
              </div>
              <div className="h-3 bg-muted rounded-full overflow-hidden">
                <div 
                  className="h-full bg-primary rounded-full transition-all duration-500"
                  style={{ width: `${gamification.xpInLevel}%` }}
                />
              </div>
              <div className="text-[10px] text-muted-foreground pt-1">
                {formatCurrency(gamification.currentLevelSales)} → {formatCurrency(gamification.nextLevelSales)}
              </div>
            </div>

            {/* Sales Goal Progress */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-muted-foreground">Sales Target Progress</span>
                <span className="text-success">{Math.round(gamification.salesProgress)}%</span>
              </div>
              <div className="h-3 bg-muted rounded-full overflow-hidden">
                <div 
                  className="h-full bg-success rounded-full transition-all duration-500"
                  style={{ width: `${gamification.salesProgress}%` }}
                />
              </div>
              <div className="text-[10px] text-muted-foreground pt-1">Target: Rs. 20L | Keep growing!</div>
            </div>
          </div>

          {/* Achievements Card */}
          <div className="rounded-2xl bg-card shadow-card border border-border p-6">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2 mb-4">
              <Trophy className="w-5 h-5 text-warning" />
              Achievements
            </h3>
            <div className="space-y-3">
              {gamification.achievements.length > 0 ? (
                gamification.achievements.map((achievement, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-background/70 border border-border/50">
                    <div className="text-3xl">{achievement.icon}</div>
                    <div>
                      <div className="text-sm font-semibold text-foreground">{achievement.name}</div>
                      <div className="text-xs text-muted-foreground">Unlocked ✓</div>
                    </div>
                    <Star className="w-4 h-4 text-warning ml-auto" />
                  </div>
                ))
              ) : (
                <div className="text-center py-4 text-muted-foreground text-sm">
                  Keep growing to unlock achievements!
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      <section className="grid gap-6 xl:grid-cols-[1.25fr_0.95fr]">
        <CardShell title="Daily Sales" subtitle="Last 7 days of sales volume." action="Weekly pulse">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={enhancedDailySales} barCategoryGap={18}>
                <CartesianGrid vertical={false} stroke="oklch(0.92 0.005 250)" />
                <XAxis dataKey="day" axisLine={false} tickLine={false} fontSize={12} />
                <YAxis axisLine={false} tickLine={false} fontSize={12} tickFormatter={(value) => `${Math.round(value / 1000)}k`} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} labelStyle={{ color: "#163020" }} contentStyle={{ borderRadius: 16, border: "1px solid oklch(0.92 0.005 250)" }} />
                <Bar dataKey="value" radius={[10, 10, 0, 0]}>
                  {enhancedDailySales.map((day) => (
                    <Cell key={day.day} fill={day.day === kpi.bestDay.day ? "oklch(0.60 0.15 145)" : "oklch(0.50 0.13 150)"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardShell>

        <CardShell title="Payment Mix" subtitle="How customers are paying this month." action="Collection quality">
          <div className="grid md:grid-cols-[220px_1fr] gap-4 items-center">
            <div className="h-60">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={analytics.paymentMix} dataKey="value" innerRadius={58} outerRadius={88} paddingAngle={3}>
                    {analytics.paymentMix.map((item) => (
                      <Cell key={item.name} fill={item.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-3">
              {analytics.paymentMix.map((item) => (
                <div key={item.name} className="rounded-2xl border border-border bg-background/70 p-3 flex items-center gap-3">
                  <span className="w-3 h-3 rounded-full" style={{ background: item.color }} />
                  <div className="flex-1">
                    <div className="font-medium text-foreground">{item.name}</div>
                    <div className="text-xs text-muted-foreground">Share of payment volume</div>
                  </div>
                  <div className="text-right font-semibold text-foreground">{item.value}%</div>
                </div>
              ))}
            </div>
          </div>
        </CardShell>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <CardShell title="Fast Movers" subtitle="Products driving daily throughput." action="High demand">
          <MoverList items={analytics.fastMovers} accent="bg-success" />
        </CardShell>
        <CardShell title="Slow Movers" subtitle="Products needing attention or bundling." action="Watch list">
          <MoverList items={analytics.slowMovers} accent="bg-warning" reverse />
        </CardShell>
      </section>

      <section className="w-full">
        <div className="bg-card border border-border rounded-[24px] p-6 shadow-card">
          <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
            <div>
              <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                <Radio className="w-5 h-5 text-primary animate-pulse" />
                Broadcasted Marketing Performance
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Sales performance & revenue growth of promoted items compared to their 7-month historical baseline.
              </p>
            </div>

            {!loadingBroadcast && broadcastPerformance.length > 0 && (
              <div className="flex flex-wrap gap-4">
                <div className="bg-success/5 border border-success/15 rounded-xl px-4 py-2 text-center">
                  <div className="text-xs text-muted-foreground">Active Growth Promos</div>
                  <div className="text-lg font-bold text-success mt-0.5">
                    {broadcastStats.positiveCount} / {broadcastPerformance.length}
                  </div>
                </div>
                <div className="bg-primary/5 border border-primary/15 rounded-xl px-4 py-2 text-center">
                  <div className="text-xs text-muted-foreground">Promotional Volume Growth</div>
                  <div className="text-lg font-bold text-primary mt-0.5 flex items-center justify-center">
                    <TrendingUp className="w-4 h-4 mr-1 text-primary" />
                    +{broadcastStats.totalGrowth.toFixed(0)} units
                  </div>
                </div>
                <div className="bg-success/5 border border-success/15 rounded-xl px-4 py-2 text-center">
                  <div className="text-xs text-muted-foreground">Incremental Revenue</div>
                  <div className="text-lg font-bold text-success mt-0.5 flex items-center justify-center">
                    <DollarSign className="w-4 h-4 mr-0.5" />
                    +₹{broadcastStats.totalRevGrowth.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>
              </div>
            )}
          </div>

          {loadingBroadcast ? (
            <div className="h-64 flex items-center justify-center animate-pulse">
              <div className="text-sm text-muted-foreground">Aggregating checkout streams...</div>
            </div>
          ) : !broadcastPerformance.length ? (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-muted rounded-xl">
              <Radio className="w-8 h-8 text-muted-foreground mb-2" />
              <div className="text-sm font-semibold text-muted-foreground">No broadcasted campaigns found</div>
              <div className="text-xs text-muted-foreground/80 mt-1">Broadcast an offer to customers first to view performance stats.</div>
            </div>
          ) : (
            <div className="space-y-8">
              {/* Double Bar Chart comparing Baseline and Current Sales */}
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={broadcastPerformance}
                    margin={{ top: 20, right: 10, left: 10, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                    <XAxis
                      dataKey="product_name"
                      stroke="oklch(0.5 0.05 150)"
                      fontSize={11}
                      tickLine={false}
                      tickFormatter={(name) => name.length > 15 ? name.substring(0, 15) + "..." : name}
                    />
                    <YAxis
                      stroke="oklch(0.5 0.05 150)"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "oklch(0.2 0.05 150)",
                        borderRadius: "12px",
                        border: "1px solid rgba(255,255,255,0.1)",
                      }}
                      labelStyle={{ color: "#fff", fontWeight: "bold" }}
                    />
                    <Legend />
                    <Bar
                      name="Usual Weekly Quantity"
                      dataKey="usual_weekly_qty"
                      fill="oklch(0.7 0.08 150)"
                      radius={[6, 6, 0, 0]}
                    />
                    <Bar
                      name="This Week Sales Quantity"
                      dataKey="this_week_qty"
                      fill="oklch(0.55 0.16 150)"
                      radius={[6, 6, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Performance Details Table */}
              <div className="overflow-x-auto rounded-xl border border-muted">
                <table className="w-full text-left text-sm border-collapse">
                  <thead className="bg-muted/50 text-muted-foreground uppercase text-xs font-bold border-b">
                    <tr>
                      <th className="p-4">Item Details</th>
                      <th className="p-4 text-center">Usual Qty (Wk)</th>
                      <th className="p-4 text-center">This Week Qty</th>
                      <th className="p-4 text-center">Volume Growth</th>
                      <th className="p-4 text-right">Usual Rev (Wk)</th>
                      <th className="p-4 text-right">This Week Rev</th>
                      <th className="p-4 text-right">Revenue Growth</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y text-foreground">
                    {broadcastPerformance.map((item) => {
                      const isPositive = item.qty_growth >= 0;
                      const isRevPositive = item.rev_growth >= 0;
                      return (
                        <tr key={item.product_id} className="hover:bg-muted/15 transition-all">
                          <td className="p-4">
                            <div className="font-semibold">{item.product_name}</div>
                            <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                              <span className="font-mono bg-muted px-1.5 py-0.5 rounded text-foreground">#{item.product_id}</span>
                              <span>•</span>
                              <span>{item.category}</span>
                            </div>
                          </td>
                          <td className="p-4 text-center font-semibold font-mono">{item.usual_weekly_qty}</td>
                          <td className="p-4 text-center font-bold font-mono">{item.this_week_qty}</td>
                          <td className="p-4 text-center">
                            <span
                              className={`inline-flex items-center px-2 py-1 rounded-lg text-xs font-bold font-mono gap-1 ${
                                isPositive ? "bg-success/15 text-success" : "bg-alert/15 text-alert"
                              }`}
                            >
                              {isPositive ? "+" : ""}
                              {item.qty_growth}
                              {isPositive ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                            </span>
                          </td>
                          <td className="p-4 text-right font-mono text-muted-foreground">₹{item.usual_weekly_rev.toFixed(2)}</td>
                          <td className="p-4 text-right font-mono font-semibold">₹{item.this_week_rev.toFixed(2)}</td>
                          <td className="p-4 text-right">
                            <span
                              className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-bold font-mono gap-1 ${
                                isRevPositive ? "bg-success/15 text-success" : "bg-alert/15 text-alert"
                              }`}
                            >
                              {isRevPositive ? "+" : ""}
                              ₹{item.rev_growth.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr_1fr]">
        <InsightTile icon={<TrendingUp className="w-5 h-5 text-success" />} title="Sales Momentum" value={`${Math.round(((kpi.bestDay.value - kpi.avgDailySales) / kpi.avgDailySales) * 100)}% above average`} description={`${kpi.bestDay.day} was the best trading day this week.`} />
        <InsightTile icon={<PackageSearch className="w-5 h-5 text-warning" />} title="Mover Gap" value={`${analytics.fastMovers[0]?.qty ?? 0} vs ${analytics.slowMovers[0]?.qty ?? 0} qty`} description="Gap between the top fast mover and slowest-moving SKU." />
        <InsightTile icon={<Megaphone className="w-5 h-5 text-primary" />} title="Campaign Reach" value={`${offerSummary?.averageRecipientsPerBroadcast.toFixed(1) ?? "0"} avg recipients`} description="Average audience size per broadcast sent from CART-EL." />
      </section>
    </div>
  );
}

function CardShell({ title, subtitle, action, children }: { title: string; subtitle: string; action: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl bg-card shadow-card border border-border overflow-hidden">
      <div className="px-5 py-4 border-b border-border flex items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold text-foreground">{title}</h2>
          <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
        </div>
        <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary whitespace-nowrap">
          {action}
        </span>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function HeroMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-white/12 p-4">
      <div className="text-[11px] uppercase tracking-[0.16em] text-white/70">{label}</div>
      <div className="mt-2 text-lg font-bold text-white leading-snug">{value}</div>
    </div>
  );
}

function MoverList({ items, accent, reverse = false }: { items: { name: string; qty: number }[]; accent: string; reverse?: boolean }) {
  const max = Math.max(...items.map((item) => item.qty), 1);

  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={item.name}>
          <div className="flex items-center justify-between text-sm mb-1.5">
            <span className="text-foreground font-medium">
              <span className="text-muted-foreground mr-2">{index + 1}.</span>
              {item.name}
            </span>
            <span className="text-muted-foreground">{item.qty} qty</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div className={`h-full rounded-full ${accent}`} style={{ width: `${(item.qty / max) * 100}%`, opacity: reverse ? 0.75 + index * 0.04 : 1 }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function InsightTile({ icon, title, value, description }: { icon: ReactNode; title: string; value: string; description: string }) {
  return (
    <div className="rounded-2xl bg-card shadow-card border border-border p-5 hover:shadow-lg hover:border-primary/30 transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            {icon}
          </div>
          <div>
            <div className="text-sm font-semibold text-foreground">{title}</div>
          </div>
        </div>
        <div className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-success/10 text-success text-[10px] font-bold">
          <Zap className="w-3 h-3" /> Active
        </div>
      </div>
      <div className="mt-3 text-2xl font-bold text-foreground">{value}</div>
      <div className="mt-2 text-xs text-muted-foreground leading-relaxed">{description}</div>
      <div className="mt-4 h-1 bg-muted rounded-full overflow-hidden">
        <div className="h-full bg-gradient-to-r from-primary to-success" style={{ width: "75%" }} />
      </div>
    </div>
  );
}

function EmptyState({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <div className="py-10 flex flex-col items-center justify-center text-center">
      <div className="w-12 h-12 rounded-2xl bg-muted flex items-center justify-center mb-3">{icon}</div>
      <div className="text-sm text-muted-foreground">{text}</div>
    </div>
  );
}

function formatCurrency(value: number) {
  return `Rs. ${Math.round(value).toLocaleString("en-IN")}`;
}

function formatLakh(value: number) {
  return `Rs. ${(value / 100000).toFixed(2)}L`;
}

function prettifyActionType(value: string) {
  return value
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}
