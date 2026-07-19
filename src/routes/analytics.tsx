import { createFileRoute } from "@tanstack/react-router";
import { AnalyticsSection } from "@/components/AnalyticsSection";

export const Route = createFileRoute("/analytics")({
  component: AnalyticsDashboard,
});

function AnalyticsDashboard() {
  return (
    <div className="max-w-7xl mx-auto">
      <AnalyticsSection />
    </div>
  );
}
