"use client";

import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Activity {
  id: string;
  platform: string;
  email: string;
  status: "success" | "failed" | "running";
  timestamp: string;
}

interface ActivityFeedProps {
  activities: Activity[];
}

const statusColors = {
  success: "bg-green-500/10 text-green-500",
  failed: "bg-red-500/10 text-red-500",
  running: "bg-blue-500/10 text-blue-500",
};

export function ActivityFeed({ activities }: ActivityFeedProps) {
  if (activities.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-4">
        No recent activity
      </p>
    );
  }

  return (
    <ScrollArea className="h-[300px]">
      <div className="space-y-4">
        {activities.map((activity) => (
          <div
            key={activity.id}
            className="flex items-center justify-between border-b pb-2 last:border-0"
          >
            <div className="space-y-1">
              <p className="text-sm font-medium">{activity.email}</p>
              <p className="text-xs text-muted-foreground capitalize">
                {activity.platform}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge
                variant="secondary"
                className={statusColors[activity.status]}
              >
                {activity.status}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {new Date(activity.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}
