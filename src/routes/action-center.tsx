import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BadgeCheck,
  BarChart3,
  CalendarRange,
  MessageCircleMore,
  PackageOpen,
  PiggyBank,
  PlayCircle,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import {
  insightService,
  type ExpiryAlert,
  type FinancialRiskItem,
  type InterventionInsights,
  type OverstockPrediction,
  type RevenueOpportunityAlert,
  type SlowMoverPrediction,
} from "@/lib/api/insightService";
import {
  impactService,
  type ImpactMetrics,
  type ImpactReportItem,
  type InterventionRecord,
} from "@/lib/api/impactService";

export const Route = createFileRoute("/action-center")({
  component: ActionCenter,
});

function ActionCenter() {
  const [data, setData] = useState<InterventionInsights | null>(null);
  const [impactOverview, setImpactOverview] = useState<ImpactMetrics | null>(null);
  const [impactRecommendations, setImpactRecommendations] = useState<InterventionRecord[]>([]);
  const [weeklyImpact, setWeeklyImpact] = useState<ImpactReportItem[]>([]);
  const [monthlyImpact, setMonthlyImpact] = useState<ImpactReportItem[]>([]);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshSyncing, setRefreshSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string>("Loading data…");
  const [error, setError] = useState<string | null>(null);

  const loadImpactData = async () => {
    const [overview, recommendations, weekly, monthly] = await Promise.all([
      impactService.overview(),
      impactService.getRecommendations(),
      impactService.weeklyReport(),
      impactService.monthlyReport(),
    ]);
    setImpactOverview(overview);
    setImpactRecommendations(recommendations);
    setWeeklyImpact(weekly);
    setMonthlyImpact(monthly);
  };

  const runBackgroundRefresh = async () => {
    try {
      setRefreshSyncing(true);
      setSyncMessage("Syncing AI recommendations…");
      await impactService.startRefresh();
      await impactService.waitForRefreshComplete();
      setSyncMessage("Loading impact data…");
      await loadImpactData();
    } catch (err) {
      console.error("Failed to sync recommendations:", err);
    } finally {
      setRefreshSyncing(false);
      setSyncMessage("Done");
    }
  };

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        setLoading(true);
        setSyncMessage("Fetching intervention insights…");

        // 1. Fetch insight data and pre-existing impact records in parallel
        const [response] = await Promise.all([
          insightService.getInterventions(),
          loadImpactData(),
        ]);
        setData(response);
        setError(null);

        // 2. Kick off background sync to populate / refresh intervention records,
        //    then reload impact data so Intervention Tracking is populated.
        await runBackgroundRefresh();
      } catch (err) {
        console.error("Failed to load intervention insights:", err);
        setError("Failed to load action recommendations");
      } finally {
        setLoading(false);
      }
    };

    fetchInsights();
  }, []);

  const refreshImpact = async () => {
    try {
      await loadImpactData();
    } catch (err) {
      console.error("Failed to refresh impact metrics:", err);
    }
  };

  const approveRecommendation = async (record: InterventionRecord) => {
    try {
      setBusyKey(`approve-${record.recommendation_key}`);
      await impactService.approve({
        recommendationKey: record.recommendation_key,
        merchant: sessionStorage.getItem("merchant_username") || "Merchant",
        actionPerformed: record.recommended_action || `Approved ${record.intervention_type}`,
        notes: record.recommendation_reason,
      });
      await refreshImpact();
    } catch (err) {
      console.error("Failed to approve intervention:", err);
      alert("Could not approve this recommendation.");
    } finally {
      setBusyKey(null);
    }
  };

  const executeRecommendation = async (record: InterventionRecord) => {
    try {
      setBusyKey(`execute-${record.recommendation_key}`);
      await impactService.execute({
        recommendationKey: record.recommendation_key,
        merchant: sessionStorage.getItem("merchant_username") || "Merchant",
        actionPerformed: record.recommended_action || `Executed ${record.intervention_type}`,
        notes: record.recommendation_reason,
      });
      await refreshImpact();
    } catch (err) {
      console.error("Failed to execute intervention:", err);
      alert("Could not mark this recommendation as executed.");
    } finally {
      setBusyKey(null);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-12 h-12 rounded-full border-4 border-primary border-t-transparent animate-spin" />
          <div>
            <h1 className="text-2xl font-bold text-foreground text-center">Action Center</h1>
            <p className="text-sm text-muted-foreground mt-1 text-center">{syncMessage}</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Action Center</h1>
        </div>
        <div className="rounded-2xl border border-alert/30 bg-alert/10 p-6 text-alert">
          <p className="font-semibold">{error || "Unable to load recommendations"}</p>
        </div>
      </div>
    );
  }

  const {
    summary,
    expiryAlerts,
    broadcastPrediction,
    financialRiskRanking,
    slowMoverPredictions,
    overstockPredictions,
    revenueOpportunityAlerts,
  } = data;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <section
        className="rounded-[28px] overflow-hidden text-white shadow-card relative"
        style={{ background: "linear-gradient(135deg, #10311D 0%, #1A7A45 55%, #E6B800 140%)" }}
      >
        <div className="absolute -top-16 -right-10 w-56 h-56 rounded-full bg-white/10" />
        <div className="absolute bottom-0 left-0 right-0 h-24 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.16),transparent_60%)]" />
        <div className="relative p-6 md:p-8 space-y-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div className="space-y-2 max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full bg-white/12 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em]">
                <Sparkles className="w-3.5 h-3.5" />
                Recommended Next Actions
              </div>
              <h1 className="text-3xl md:text-4xl font-black tracking-tight">Action Center</h1>
              <p className="text-sm md:text-base text-white/82 max-w-2xl">
                The highest-impact inventory and campaign actions for today, ranked by recoverable money and urgency.
              </p>
            </div>
            <div className="rounded-2xl bg-black/15 backdrop-blur-sm px-4 py-3 text-sm">
              <div className="text-white/70">Store signals</div>
              <div className="font-semibold mt-1">
                {summary.activeCustomers} customers • {summary.offersRun} offers • {summary.broadcastsSent} broadcasts
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-4">
            <SummaryCard label="Money At Risk" value={formatCurrency(summary.moneyAtRisk)} tone="warm" />
            <SummaryCard label="Money Recoverable" value={formatCurrency(summary.moneyRecoverable)} tone="cool" />
            <SummaryCard label="Top Recommendation" value={summary.recommendedAction} tone="plain" />
            <SummaryCard label="Expected Outcome" value={summary.expectedOutcome} tone="plain" />
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
        <div className="rounded-2xl bg-card shadow-card overflow-hidden h-fit">
          <div className="px-5 py-4 border-b border-border flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-alert" />
            <div>
              <h2 className="font-semibold text-foreground">Expiry Actions</h2>
              <p className="text-xs text-muted-foreground mt-0.5">Products needing immediate intervention.</p>
            </div>
          </div>
          <div className="divide-y divide-border overflow-y-auto" style={{ maxHeight: "960px" }}>
            {expiryAlerts.length > 0 ? expiryAlerts.map((alert) => (
              <ExpiryCard key={alert.title} alert={alert} />
            )) : (
              <EmptyState text="No urgent expiry action found right now." />
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl bg-card shadow-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center gap-3">
              <PiggyBank className="w-5 h-5 text-primary" />
              <div>
                <h2 className="font-semibold text-foreground">Risk Priority</h2>
                <p className="text-xs text-muted-foreground mt-0.5">Where the merchant should focus first.</p>
              </div>
            </div>
            <div className="divide-y divide-border">
              {financialRiskRanking.length > 0 ? financialRiskRanking.map((item, index) => (
                <RiskRow key={`${item.product}-${index}`} item={item} index={index} />
              )) : (
                <EmptyState text="No ranked risks available." />
              )}
            </div>
          </div>

          <div className="rounded-2xl bg-card shadow-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center gap-3">
              <MessageCircleMore className="w-5 h-5 text-primary" />
              <div>
                <h2 className="font-semibold text-foreground">Broadcast Opportunity</h2>
                <p className="text-xs text-muted-foreground mt-0.5">{broadcastPrediction.title}</p>
              </div>
            </div>
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <MetricChip label="Target Customers" value={String(broadcastPrediction.target_customers)} />
                <MetricChip label="Expected Conversion" value={`${broadcastPrediction.expected_conversion_rate}%`} />
                <MetricChip label="Expected Sales" value={formatCurrency(broadcastPrediction.expected_sales)} />
                <MetricChip label="Inventory Reduction" value={`${broadcastPrediction.expected_inventory_reduction}%`} />
              </div>
              <ConfidenceBar value={broadcastPrediction.confidence} />
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <PredictionPanel
          icon={<BarChart3 className="w-5 h-5 text-warning" />}
          title="Slow Mover Actions"
          subtitle="Promotions recommended for idle stock."
          items={slowMoverPredictions}
          renderItem={(item) => <SlowMoverCard key={item.title} item={item} />}
        />
        <PredictionPanel
          icon={<PackageOpen className="w-5 h-5 text-primary" />}
          title="Overstock Actions"
          subtitle="Bundles or flash sales to reduce carrying cost."
          items={overstockPredictions}
          renderItem={(item) => <OverstockCard key={item.title} item={item} />}
        />
      </section>

      <section>
        <PredictionPanel
          icon={<Target className="w-5 h-5 text-success" />}
          title="Revenue Opportunities"
          subtitle="Cross-sell and combo ideas that can add monthly revenue."
          items={revenueOpportunityAlerts}
          renderItem={(item) => <RevenueCard key={item.title} item={item} />}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl bg-card shadow-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <BadgeCheck className="w-5 h-5 text-success" />
              <div>
                <h2 className="font-semibold text-foreground">Intervention Tracking</h2>
                <p className="text-xs text-muted-foreground mt-0.5">Approve and execute recommendations with measurable impact.</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => void runBackgroundRefresh()}
              disabled={refreshSyncing}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-border bg-muted/40 hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {refreshSyncing ? "Syncing…" : "Sync recommendations"}
            </button>
          </div>
          <div className="p-5 space-y-4">
            {impactOverview ? (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <MetricChip label="Generated" value={String(impactOverview.generatedRecommendations)} />
                <MetricChip label="Approved" value={String(impactOverview.approvedRecommendations)} />
                <MetricChip label="Executed" value={String(impactOverview.executedRecommendations)} />
                <MetricChip label="Revenue Recovered" value={formatCurrency(impactOverview.estimatedRevenueRecovered)} />
                <MetricChip label="Loss Avoided" value={formatCurrency(impactOverview.estimatedLossAvoided)} />
                <MetricChip label="Inventory Cleared" value={String(Math.round(impactOverview.inventoryCleared))} />
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">Loading impact metrics...</div>
            )}

            <div className="divide-y divide-border rounded-2xl border border-border overflow-hidden">
              {impactRecommendations.length > 0 ? impactRecommendations.slice(0, 6).map((record) => (
                <div key={record.recommendation_key} className="p-4 space-y-3">
                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div>
                      <div className="font-semibold text-foreground">{record.product_name}</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {record.intervention_type.replace(/_/g, " ")} • {record.status}
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {new Date(record.generated_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}
                    </div>
                  </div>
                  <div className="text-sm text-foreground bg-muted/40 rounded-xl p-3">
                    {record.recommendation_reason}
                  </div>
                  <div className="grid gap-2 md:grid-cols-3 text-xs">
                    <MetricChip label="Stock Before" value={String(Math.round(record.stock_before ?? 0))} />
                    <MetricChip label="Stock After" value={String(Math.round(record.stock_after ?? 0))} />
                    <MetricChip label="Recovered" value={formatCurrency(record.estimated_revenue_recovered ?? 0)} />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => approveRecommendation(record)}
                      disabled={busyKey === `approve-${record.recommendation_key}` || record.status === "approved" || record.status === "executed"}
                      className="inline-flex items-center gap-2 rounded-full bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground disabled:opacity-50"
                    >
                      <BadgeCheck className="w-3.5 h-3.5" />
                      {busyKey === `approve-${record.recommendation_key}` ? "Approving..." : "Approve"}
                    </button>
                    <button
                      onClick={() => executeRecommendation(record)}
                      disabled={busyKey === `execute-${record.recommendation_key}` || record.status === "executed"}
                      className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-3 py-2 text-xs font-semibold text-foreground disabled:opacity-50"
                    >
                      <PlayCircle className="w-3.5 h-3.5" />
                      {busyKey === `execute-${record.recommendation_key}` ? "Executing..." : "Mark Executed"}
                    </button>
                  </div>
                </div>
              )) : (
                <div className="p-5 text-sm text-muted-foreground">No intervention records yet. Open the dashboard again to sync current AI recommendations.</div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl bg-card shadow-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-primary" />
              <div>
                <h2 className="font-semibold text-foreground">Weekly Impact</h2>
                <p className="text-xs text-muted-foreground mt-0.5">Recommendation conversion trend for the last 7 days.</p>
              </div>
            </div>
            <div className="divide-y divide-border">
              {weeklyImpact.length > 0 ? weeklyImpact.map((item) => (
                <div key={item.label} className="p-4 grid grid-cols-2 gap-2 text-xs">
                  <div className="col-span-2 font-semibold text-foreground">{item.label}</div>
                  <div className="text-muted-foreground">Generated</div>
                  <div className="text-right font-medium">{item.generatedRecommendations}</div>
                  <div className="text-muted-foreground">Approved</div>
                  <div className="text-right font-medium">{item.approvedRecommendations}</div>
                  <div className="text-muted-foreground">Executed</div>
                  <div className="text-right font-medium">{item.executedRecommendations}</div>
                  <div className="text-muted-foreground">Recovered</div>
                  <div className="text-right font-medium">{formatCurrency(item.estimatedRevenueRecovered)}</div>
                </div>
              )) : (
                <EmptyState text="Weekly impact will appear after interventions are tracked." />
              )}
            </div>
          </div>

          <div className="rounded-2xl bg-card shadow-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center gap-3">
              <CalendarRange className="w-5 h-5 text-warning" />
              <div>
                <h2 className="font-semibold text-foreground">Monthly Impact</h2>
                <p className="text-xs text-muted-foreground mt-0.5">Business value across the last 6 months.</p>
              </div>
            </div>
            <div className="divide-y divide-border">
              {monthlyImpact.length > 0 ? monthlyImpact.map((item) => (
                <div key={item.label} className="p-4">
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <div className="font-semibold text-foreground">{item.label}</div>
                    <div className="text-xs text-muted-foreground">{item.executedRecommendations} executed</div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <MetricChip label="Recovered" value={formatCurrency(item.estimatedRevenueRecovered)} />
                    <MetricChip label="Loss Avoided" value={formatCurrency(item.estimatedLossAvoided)} />
                  </div>
                </div>
              )) : (
                <EmptyState text="Monthly impact will populate once interventions are executed." />
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function SummaryCard({ label, value, tone }: { label: string; value: string; tone: "warm" | "cool" | "plain" }) {
  const toneClass =
    tone === "warm"
      ? "bg-[#FDEFD8] text-[#7C4A00]"
      : tone === "cool"
        ? "bg-[#E3F7EA] text-[#0D4F2E]"
        : "bg-white/12 text-white";

  return (
    <div className={`rounded-2xl p-4 ${toneClass}`}>
      <div className="text-xs uppercase tracking-[0.16em] opacity-80">{label}</div>
      <div className="mt-2 text-lg font-bold leading-snug">{value}</div>
    </div>
  );
}

function ExpiryCard({ alert }: { alert: ExpiryAlert }) {
  return (
    <div className="p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold text-foreground">{alert.title}</div>
          <div className="text-xs text-muted-foreground mt-1">
            {alert.days_to_expiry} day{alert.days_to_expiry === 1 ? "" : "s"} left • {alert.recommendation}
          </div>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase ${alert.severity === "high" ? "bg-alert/10 text-alert" : "bg-warning/10 text-warning"}`}>
          {alert.severity}
        </span>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <MetricChip label="Inventory At Risk" value={formatCurrency(alert.inventory_at_risk)} />
        <MetricChip label="Revenue Recovery" value={formatCurrency(alert.predicted_revenue_recovery)} />
        <MetricChip label="Waste Reduction" value={`${alert.predicted_waste_reduction}%`} />
      </div>
      <ConfidenceBar value={alert.confidence} />
    </div>
  );
}

function RiskRow({ item, index }: { item: FinancialRiskItem; index: number }) {
  const priorityClass =
    item.priority === "High"
      ? "bg-alert/10 text-alert"
      : item.priority === "Medium"
        ? "bg-warning/10 text-warning"
        : "bg-success/10 text-success";

  return (
    <div className="px-5 py-4 flex items-center gap-4">
      <div className="w-8 h-8 rounded-full bg-background flex items-center justify-center text-sm font-bold text-muted-foreground">
        {index + 1}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-foreground">{item.product}</div>
        <div className="text-xs text-muted-foreground mt-1">
          Loss {formatCurrency(item.potential_loss)} <ArrowRight className="inline w-3 h-3 mx-1" /> Recovery {formatCurrency(item.potential_recovery)}
        </div>
      </div>
      <div className="text-right">
        <div className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${priorityClass}`}>{item.priority}</div>
        <div className="text-xs text-muted-foreground mt-1">{item.urgency}</div>
      </div>
    </div>
  );
}

function PredictionPanel<T>({
  icon,
  title,
  subtitle,
  items,
  renderItem,
}: {
  icon: ReactNode;
  title: string;
  subtitle: string;
  items: T[];
  renderItem: (item: T) => ReactNode;
}) {
  return (
    <div className="rounded-2xl bg-card shadow-card overflow-hidden">
      <div className="px-5 py-4 border-b border-border flex items-center gap-3">
        {icon}
        <div>
          <h2 className="font-semibold text-foreground">{title}</h2>
          <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
        </div>
      </div>
      <div className="divide-y divide-border">
        {items.length > 0 ? items.map(renderItem) : <EmptyState text="No recommendations available in this section." />}
      </div>
    </div>
  );
}

function SlowMoverCard({ item }: { item: SlowMoverPrediction }) {
  return (
    <div className="p-5 space-y-3">
      <div className="font-semibold text-foreground">{item.title}</div>
      <div className="grid gap-3 md:grid-cols-3">
        <MetricChip label="Inventory Value" value={formatCurrency(item.inventory_value)} />
        <MetricChip label="Sales Lift" value={`${item.predicted_sales_lift}%`} />
        <MetricChip label="Recovery" value={formatCurrency(item.predicted_revenue_recovery)} />
      </div>
      <div className="text-xs text-muted-foreground">
        {item.recommendation} • {item.days_idle} idle day{item.days_idle === 1 ? "" : "s"}
      </div>
      <ConfidenceBar value={item.confidence} />
    </div>
  );
}

function OverstockCard({ item }: { item: OverstockPrediction }) {
  return (
    <div className="p-5 space-y-3">
      <div className="font-semibold text-foreground">{item.title}</div>
      <div className="grid gap-3 md:grid-cols-3">
        <MetricChip label="Excess Units" value={String(item.excess_units)} />
        <MetricChip label="Carrying Cost Risk" value={formatCurrency(item.carrying_cost_risk)} />
        <MetricChip label="Predicted Reduction" value={`${item.predicted_inventory_reduction}%`} />
      </div>
      <div className="text-xs text-muted-foreground">{item.recommendation}</div>
      <ConfidenceBar value={item.confidence} />
    </div>
  );
}

function RevenueCard({ item }: { item: RevenueOpportunityAlert }) {
  return (
    <div className="p-5 space-y-3">
      <div className="font-semibold text-foreground">{item.title}</div>
      <div className="text-sm text-muted-foreground">{item.bundle_recommendation}</div>
      <div className="flex flex-wrap gap-2">
        {item.products.map((product) => (
          <span key={product} className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            {product}
          </span>
        ))}
      </div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Predicted additional revenue</span>
        <span className="font-semibold text-foreground">{formatCurrency(item.predicted_additional_revenue)}/month</span>
      </div>
      <ConfidenceBar value={item.confidence} />
    </div>
  );
}

function MetricChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-background/70 border border-border p-3">
      <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
      <div className="mt-1 text-base font-semibold text-foreground">{value}</div>
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const width = `${Math.round(value * 100)}%`;

  return (
    <div>
      <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
        <span>Confidence</span>
        <span>{Math.round(value * 100)}%</span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ width, background: "linear-gradient(90deg, #1A7A45, #F6C90E)" }}
        />
      </div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="p-5 text-sm text-muted-foreground">{text}</div>;
}

function formatCurrency(value: number) {
  return `Rs. ${Math.round(value).toLocaleString("en-IN")}`;
}
