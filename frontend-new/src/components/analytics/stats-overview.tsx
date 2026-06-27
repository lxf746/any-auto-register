"use client";

import { useEffect, useState } from "react";
import { statsApi } from "@/lib/api-client";
import { StatCard } from "@/components/dashboard/stat-card";
import { BarChart3, Users, CheckCircle, Clock } from "lucide-react";

interface Stats {
  total_registrations: number;
  success: number;
  failed: number;
  success_rate: number;
  total_accounts: number;
}

interface StatsOverviewProps {
  dateRange: string;
}

export function StatsOverview({ dateRange }: StatsOverviewProps) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await statsApi.overview();
        setStats(data);
      } catch (err) {
        console.error("Failed to load stats:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [dateRange]);

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Total Registrations"
        value={stats?.total_registrations ?? 0}
        icon={<BarChart3 className="h-4 w-4" />}
        description="All time"
      />
      <StatCard
        title="Success Rate"
        value={`${stats?.success_rate ?? 0}%`}
        icon={<CheckCircle className="h-4 w-4" />}
        description={`${stats?.success ?? 0} succeeded`}
      />
      <StatCard
        title="Failed"
        value={stats?.failed ?? 0}
        icon={<Clock className="h-4 w-4" />}
        description="Requires attention"
      />
      <StatCard
        title="Total Accounts"
        value={stats?.total_accounts ?? 0}
        icon={<Users className="h-4 w-4" />}
        description="Registered accounts"
      />
    </div>
  );
}
