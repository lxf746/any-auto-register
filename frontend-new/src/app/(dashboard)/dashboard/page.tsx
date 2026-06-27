"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { statsApi, platformsApi } from "@/lib/api-client";
import { StatCard } from "@/components/dashboard/stat-card";
import { PlatformCard } from "@/components/dashboard/platform-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConnectionStatus } from "@/components/ui/connection-status";
import { BarChart3, Users, CheckCircle, Activity, Plus, List } from "lucide-react";
import { useTaskUpdates } from "@/hooks/use-websocket";

interface Stats {
  total_registrations: number;
  success: number;
  failed: number;
  success_rate: number;
  total_accounts: number;
  account_distribution: Record<string, number>;
}

interface Platform {
  name: string;
  [key: string]: unknown;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [loading, setLoading] = useState(true);
  const { messages: taskUpdates } = useTaskUpdates();

  // Refresh stats when task updates arrive
  useEffect(() => {
    if (taskUpdates.length > 0) {
      statsApi.overview().then(setStats).catch(console.error);
    }
  }, [taskUpdates]);

  useEffect(() => {
    async function load() {
      try {
        const [statsData, platformsData] = await Promise.all([
          statsApi.overview(),
          platformsApi.list(),
        ]);
        setStats(statsData);
        setPlatforms(platformsData as Platform[]);
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      } finally {
        setLoading(false);
      }
    }
    load();

    // Auto-refresh every 30 seconds
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground">
            Overview of your registration activity.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <ConnectionStatus />
          <div className="flex gap-2">
            <Link href="/register">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Register Account
              </Button>
            </Link>
            <Link href="/accounts">
              <Button variant="outline">
                <List className="mr-2 h-4 w-4" />
                View Accounts
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Registrations"
          value={stats?.total_registrations ?? 0}
          icon={<BarChart3 className="h-4 w-4" />}
        />
        <StatCard
          title="Success Rate"
          value={`${stats?.success_rate ?? 0}%`}
          icon={<CheckCircle className="h-4 w-4" />}
          description={`${stats?.success ?? 0} succeeded, ${stats?.failed ?? 0} failed`}
        />
        <StatCard
          title="Total Accounts"
          value={stats?.total_accounts ?? 0}
          icon={<Users className="h-4 w-4" />}
        />
        <StatCard
          title="Active Platforms"
          value={platforms.length}
          icon={<Activity className="h-4 w-4" />}
        />
      </div>

      {/* Platform Grid */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Platforms</h3>
        {platforms.length === 0 ? (
          <p className="text-muted-foreground">No platforms found.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {platforms.map((platform) => (
              <PlatformCard
                key={platform.name}
                name={platform.name}
                accountCount={
                  stats?.account_distribution?.[platform.name] ?? 0
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-4">
          <Link href="/register">
            <Button variant="outline">New Registration</Button>
          </Link>
          <Link href="/history">
            <Button variant="outline">View History</Button>
          </Link>
          <Link href="/settings">
            <Button variant="outline">Settings</Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
