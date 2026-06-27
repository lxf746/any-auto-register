"use client";

import { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

interface RegistrationChartProps {
  dateRange: string;
}

interface ChartData {
  date: string;
  success: number;
  failed: number;
  total: number;
}

export function RegistrationChart({ dateRange }: RegistrationChartProps) {
  const [data, setData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        // Generate mock data for demonstration
        const days = dateRange === "7d" ? 7 : dateRange === "30d" ? 30 : 90;
        const mockData: ChartData[] = [];
        for (let i = days; i >= 0; i--) {
          const date = new Date();
          date.setDate(date.getDate() - i);
          const success = Math.floor(Math.random() * 50) + 10;
          const failed = Math.floor(Math.random() * 10);
          mockData.push({
            date: date.toISOString().split("T")[0],
            success,
            failed,
            total: success + failed,
          });
        }
        setData(mockData);
      } catch (err) {
        console.error("Failed to load chart data:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [dateRange]);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex justify-center py-12">
          <LoadingSpinner />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Registration Trends</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              className="text-xs"
              tickFormatter={(value) => {
                const date = new Date(value);
                return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
              }}
            />
            <YAxis className="text-xs" />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
              }}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="success"
              stackId="1"
              stroke="hsl(142, 76%, 36%)"
              fill="hsl(142, 76%, 36%)"
              fillOpacity={0.6}
              name="Success"
            />
            <Area
              type="monotone"
              dataKey="failed"
              stackId="1"
              stroke="hsl(0, 84%, 60%)"
              fill="hsl(0, 84%, 60%)"
              fillOpacity={0.6}
              name="Failed"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
