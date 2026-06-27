"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatsOverview } from "@/components/analytics/stats-overview";
import { RegistrationChart } from "@/components/analytics/registration-chart";
import { PlatformBreakdown } from "@/components/analytics/platform-breakdown";
import { PerformanceMetrics } from "@/components/analytics/performance-metrics";
import { ExportPanel } from "@/components/analytics/export-panel";

export default function AnalyticsPage() {
  const [dateRange, setDateRange] = useState("7d");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Analytics</h2>
          <p className="text-muted-foreground">
            Registration statistics and performance metrics.
          </p>
        </div>
        <div className="flex gap-2">
          {["7d", "30d", "90d"].map((range) => (
            <button
              key={range}
              onClick={() => setDateRange(range)}
              className={`px-3 py-1 text-sm rounded-md transition-colors ${
                dateRange === range
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {range === "7d" ? "7 Days" : range === "30d" ? "30 Days" : "90 Days"}
            </button>
          ))}
        </div>
      </div>

      <StatsOverview dateRange={dateRange} />

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="platforms">Platforms</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="export">Export</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <RegistrationChart dateRange={dateRange} />
        </TabsContent>

        <TabsContent value="platforms" className="space-y-4">
          <PlatformBreakdown dateRange={dateRange} />
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <PerformanceMetrics dateRange={dateRange} />
        </TabsContent>

        <TabsContent value="export" className="space-y-4">
          <ExportPanel dateRange={dateRange} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
