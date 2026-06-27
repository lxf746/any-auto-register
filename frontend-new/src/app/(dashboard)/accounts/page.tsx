"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { DataTable, Column } from "@/components/ui/data-table";
import { FilterSelect } from "@/components/ui/filter-select";
import { SearchInput } from "@/components/ui/search-input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Download, Trash2 } from "lucide-react";

interface Account {
  id: number;
  platform: string;
  email: string;
  lifecycle_status: string;
  created_at: string;
  updated_at: string;
}

const statusColors: Record<string, string> = {
  registered: "bg-green-500/10 text-green-500",
  active: "bg-green-500/10 text-green-500",
  banned: "bg-red-500/10 text-red-500",
  unknown: "bg-gray-500/10 text-gray-500",
};

const statusOptions = [
  { label: "Active", value: "active" },
  { label: "Registered", value: "registered" },
  { label: "Banned", value: "banned" },
  { label: "Unknown", value: "unknown" },
];

export default function AccountsPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<number[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const params = new URLSearchParams();
        if (statusFilter !== "all") params.set("status", statusFilter);
        const data = await api.get<Account[]>(`/accounts?${params}`);
        setAccounts(data);
      } catch (err) {
        console.error("Failed to load accounts:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [statusFilter]);

  const filteredAccounts = accounts.filter(
    (a) =>
      a.email.toLowerCase().includes(search.toLowerCase()) ||
      a.platform.toLowerCase().includes(search.toLowerCase())
  );

  const handleExport = async () => {
    try {
      const data = await api.post<{ content: string }>("/accounts/export/json", {
        ids: selected.length > 0 ? selected : undefined,
        select_all: selected.length === 0,
      });
      const blob = new Blob([data.content], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "accounts.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
    }
  };

  const columns: Column<Account>[] = [
    {
      key: "email",
      header: "Email",
      render: (account) => (
        <span className="font-medium">{account.email}</span>
      ),
    },
    {
      key: "platform",
      header: "Platform",
      render: (account) => (
        <span className="capitalize">{account.platform}</span>
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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Accounts</h2>
          <p className="text-muted-foreground">
            Manage your registered accounts.
          </p>
        </div>
        <div className="flex gap-2">
          {selected.length > 0 && (
            <Button variant="destructive" size="sm">
              <Trash2 className="mr-2 h-4 w-4" />
              Delete ({selected.length})
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      <div className="flex gap-4">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search by email or platform..."
          className="w-[300px]"
        />
        <FilterSelect
          value={statusFilter}
          onChange={setStatusFilter}
          options={statusOptions}
          placeholder="Filter by status"
        />
      </div>

      <DataTable
        columns={columns}
        data={filteredAccounts}
        loading={loading}
        emptyTitle="No accounts found"
        emptyDescription="Register an account to get started."
        onRowClick={(account) => router.push(`/accounts/${account.platform}`)}
        keyExtractor={(account) => String(account.id)}
      />
    </div>
  );
}
