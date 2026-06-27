"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { DataTable, Column } from "@/components/ui/data-table";
import { FilterSelect } from "@/components/ui/filter-select";
import { SearchInput } from "@/components/ui/search-input";
import { Badge } from "@/components/ui/badge";
import { useTaskUpdates } from "@/hooks/use-websocket";

interface Task {
  id: string;
  platform: string;
  status: string;
  count: number;
  created_at: string;
  updated_at: string;
}

const statusColors: Record<string, string> = {
  running: "bg-blue-500/10 text-blue-500",
  completed: "bg-green-500/10 text-green-500",
  success: "bg-green-500/10 text-green-500",
  failed: "bg-red-500/10 text-red-500",
  cancelled: "bg-yellow-500/10 text-yellow-500",
  pending: "bg-gray-500/10 text-gray-500",
};

const statusOptions = [
  { label: "Running", value: "running" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
  { label: "Cancelled", value: "cancelled" },
];

export default function HistoryPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const { messages: taskUpdates } = useTaskUpdates();

  // Refresh tasks when updates arrive
  useEffect(() => {
    if (taskUpdates.length > 0) {
      const params = new URLSearchParams();
      if (statusFilter !== "all") params.set("status", statusFilter);
      api.get<Task[]>(`/tasks?${params}`).then(setTasks).catch(console.error);
    }
  }, [taskUpdates, statusFilter]);

  useEffect(() => {
    async function load() {
      try {
        const params = new URLSearchParams();
        if (statusFilter !== "all") params.set("status", statusFilter);
        const data = await api.get<Task[]>(`/tasks?${params}`);
        setTasks(data);
      } catch (err) {
        console.error("Failed to load tasks:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [statusFilter]);

  const filteredTasks = tasks.filter(
    (t) =>
      t.platform.toLowerCase().includes(search.toLowerCase()) ||
      t.id.toLowerCase().includes(search.toLowerCase())
  );

  const columns: Column<Task>[] = [
    {
      key: "id",
      header: "Task ID",
      render: (task) => (
        <span className="font-mono text-xs">{task.id.slice(0, 8)}</span>
      ),
    },
    {
      key: "platform",
      header: "Platform",
      render: (task) => (
        <span className="capitalize">{task.platform}</span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (task) => (
        <Badge
          variant="secondary"
          className={statusColors[task.status] || ""}
        >
          {task.status}
        </Badge>
      ),
    },
    {
      key: "count",
      header: "Count",
    },
    {
      key: "created_at",
      header: "Created",
      render: (task) =>
        new Date(task.created_at).toLocaleString(),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Task History</h2>
        <p className="text-muted-foreground">
          View and manage your registration tasks.
        </p>
      </div>

      <div className="flex gap-4">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search by platform or task ID..."
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
        data={filteredTasks}
        loading={loading}
        emptyTitle="No tasks found"
        emptyDescription="Create a registration task to get started."
        onRowClick={(task) => router.push(`/history/${task.id}`)}
        keyExtractor={(task) => task.id}
      />
    </div>
  );
}
