"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { DataTable, Column } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Download, Trash2 } from "lucide-react";

interface Account {
  id: number;
  platform: string;
  email: string;
  lifecycle_status: string;
  created_at: string;
}

const statusColors: Record<string, string> = {
  registered: "bg-green-500/10 text-green-500",
  active: "bg-green-500/10 text-green-500",
  banned: "bg-red-500/10 text-red-500",
  unknown: "bg-gray-500/10 text-gray-500",
};

export default function PlatformAccountsPage() {
  const params = useParams();
  const router = useRouter();
  const platform = params.platform as string;

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const result = await api.get<{ total: number; page: number; items: Account[] }>(
          `/accounts?platform=${platform}`
        );
        setAccounts(result.items || []);
      } catch (err) {
        console.error("Failed to load accounts:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [platform]);

  const columns: Column<Account>[] = [
    {
      key: "email",
      header: "Email",
      render: (account) => (
        <span className="font-medium">{account.email}</span>
      ),
    },
    {
      key: "lifecycle_status",
      header: "Status",
      render: (account) => (
        <Badge
          variant="secondary"
          className={statusColors[account.lifecycle_status] || ""}
        >
          {account.lifecycle_status}
        </Badge>
      ),
    },
    {
      key: "created_at",
      header: "Created",
      render: (account) =>
        new Date(account.created_at).toLocaleDateString(),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/accounts")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h2 className="text-2xl font-bold tracking-tight capitalize">
            {platform} Accounts
          </h2>
          <p className="text-muted-foreground">
            {accounts.length} accounts registered
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Platform Stats</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold">{accounts.length}</p>
              <p className="text-xs text-muted-foreground">Total</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-500">
                {accounts.filter((a) => a.lifecycle_status === "active").length}
              </p>
              <p className="text-xs text-muted-foreground">Active</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-red-500">
                {accounts.filter((a) => a.lifecycle_status === "banned").length}
              </p>
              <p className="text-xs text-muted-foreground">Banned</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <DataTable
        columns={columns}
        data={accounts}
        loading={loading}
        emptyTitle="No accounts"
        emptyDescription={`No ${platform} accounts registered yet.`}
        keyExtractor={(account) => String(account.id)}
      />
    </div>
  );
}
