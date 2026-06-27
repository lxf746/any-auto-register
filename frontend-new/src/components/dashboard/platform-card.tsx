"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowRight } from "lucide-react";
import Link from "next/link";

interface PlatformCardProps {
  name: string;
  accountCount: number;
  status?: "active" | "inactive";
}

export function PlatformCard({ name, accountCount, status = "active" }: PlatformCardProps) {
  return (
    <Link href={`/accounts/${name}`}>
      <Card className="transition-colors hover:bg-muted/50 cursor-pointer">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium capitalize">{name}</CardTitle>
          <Badge variant={status === "active" ? "default" : "secondary"}>
            {status}
          </Badge>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold">{accountCount}</div>
              <p className="text-xs text-muted-foreground">accounts</p>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
