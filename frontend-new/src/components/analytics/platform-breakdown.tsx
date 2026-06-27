"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

interface PlatformBreakdownProps {
  dateRange: string;
}

interface PlatformData {
  name: string;
  count: number;
  success: number;
  failed: number;
}

const COLORS = [
  "hsl(210, 100%, 50%)",
  "hsl(142, 76%, 36%)",
  "hsl(0, 84%, 60%)",
  "hsl(45, 93%, 47%)",
  "hsl(280, 67%, 50%)",
  "hsl(190, 70%, 45%)",
  "hsl(340, 75%, 55%)",
  "hsl(120, 60%, 45%)",
];

export function PlatformBreakdown({ dateRange }: PlatformBreakdownProps) {
  const [data, setData] = useState<PlatformData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        // Generate mock data for demonstration
        const platforms = ["chatgpt", "cursor", "windsurf", "grok", "fireworks", "kimchi", "trae"];
        const mockData: PlatformData[] = platforms.map((name) => ({
          name,
          count: Math.floor(Math.random() * 100) + 20,
          success: Math.floor(Math.random() * 80) + 15,
          failed: Math.floor(Math.random() * 15),
        }));
        setData(mockData);
      } catch (err) {
        console.error("Failed to load platform data:", err);
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
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Registrations by Platform</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="name" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                }}
              />
              <Bar dataKey="success" fill="hsl(142, 76%, 36%)" name="Success" />
              <Bar dataKey="failed" fill="hsl(0, 84%, 60%)" name="Failed" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Market Share</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={350}>
            <PieChart>
              <Pie
                data={data}
                dataKey="count"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={120}
                label={({ name, percent }) =>
                  `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                }
              >
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
