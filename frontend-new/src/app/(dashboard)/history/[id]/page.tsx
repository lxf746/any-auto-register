"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, X, RefreshCw } from "lucide-react";
import { toast } from "sonner";

interface Task {
  id: string;
  platform: string;
  status: string;
  count: number;
  created_at: string;
  updated_at: string;
}

interface TaskEvent {
  id: string;
  type: string;
  message: string;
  timestamp: string;
  level?: string;
}

const statusColors: Record<string, string> = {
  running: "bg-blue-500/10 text-blue-500",
  completed: "bg-green-500/10 text-green-500",
  success: "bg-green-500/10 text-green-500",
  failed: "bg-red-500/10 text-red-500",
  cancelled: "bg-yellow-500/10 text-yellow-500",
};

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.id as string;

  const [task, setTask] = useState<Task | null>(null);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [taskData, eventsData] = await Promise.all([
          api.get<Task>(`/tasks/${taskId}`),
          api.get<TaskEvent[]>(`/tasks/${taskId}/events`),
        ]);
        setTask(taskData);
        setEvents(eventsData);
      } catch (err) {
        console.error("Failed to load task:", err);
        toast.error("Failed to load task details");
      } finally {
        setLoading(false);
      }
    }
    load();

    // Poll for updates if task is running
    const interval = setInterval(async () => {
      try {
        const taskData = await api.get<Task>(`/tasks/${taskId}`);
        setTask(taskData);
        if (taskData.status !== "running") {
          clearInterval(interval);
        }
      } catch {
        // Ignore polling errors
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [taskId]);

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await api.post(`/tasks/${taskId}/cancel`, {});
      toast.success("Task cancelled");
      setTask((prev) => (prev ? { ...prev, status: "cancelled" } : null));
    } catch (err) {
      toast.error("Failed to cancel task");
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Task not found</p>
        <Button variant="link" onClick={() => router.push("/history")}>
          Back to history
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push("/history")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Task Details</h2>
          <p className="text-muted-foreground font-mono text-sm">{task.id}</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Platform</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold capitalize">{task.platform}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Status</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge
              variant="secondary"
              className={statusColors[task.status] || ""}
            >
              {task.status}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Actions</CardTitle>
          </CardHeader>
          <CardContent className="flex gap-2">
            {task.status === "running" && (
              <Button
                variant="destructive"
                size="sm"
                onClick={handleCancel}
                disabled={cancelling}
              >
                <X className="mr-2 h-4 w-4" />
                Cancel
              </Button>
            )}
            {task.status === "failed" && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push("/register")}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Events</CardTitle>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No events recorded</p>
          ) : (
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {events.map((event) => (
                <div
                  key={event.id}
                  className="flex gap-3 text-sm border-b pb-2 last:border-0"
                >
                  <span className="text-muted-foreground whitespace-nowrap">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                  <Badge
                    variant="outline"
                    className="text-xs"
                  >
                    {event.type}
                  </Badge>
                  <span className="flex-1">{event.message}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
