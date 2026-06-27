"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { DataTable, Column } from "@/components/ui/data-table";
import { Plus, Trash2, RefreshCw, Upload } from "lucide-react";

interface Proxy {
  id: string;
  host: string;
  port: number;
  protocol: string;
  status: "active" | "inactive" | "checking";
  username?: string;
}

export function ProxySettings() {
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [loading, setLoading] = useState(true);
  const [newProxy, setNewProxy] = useState("");

  useEffect(() => {
    // Mock data for now
    setProxies([
      { id: "1", host: "192.168.1.100", port: 8080, protocol: "http", status: "active" },
      { id: "2", host: "10.0.0.50", port: 1080, protocol: "socks5", status: "inactive" },
    ]);
    setLoading(false);
  }, []);

  const columns: Column<Proxy>[] = [
    {
      key: "host",
      header: "Host",
      render: (proxy) => (
        <span className="font-mono text-sm">{proxy.host}:{proxy.port}</span>
      ),
    },
    {
      key: "protocol",
      header: "Protocol",
      render: (proxy) => (
        <Badge variant="outline">{proxy.protocol.toUpperCase()}</Badge>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (proxy) => (
        <Badge
          variant="secondary"
          className={
            proxy.status === "active"
              ? "bg-green-500/10 text-green-500"
              : proxy.status === "checking"
              ? "bg-yellow-500/10 text-yellow-500"
              : "bg-red-500/10 text-red-500"
          }
        >
          {proxy.status}
        </Badge>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Proxy List</CardTitle>
              <CardDescription>
                Manage proxies for registration tasks.
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm">
                <RefreshCw className="mr-2 h-4 w-4" />
                Check All
              </Button>
              <Button variant="outline" size="sm">
                <Upload className="mr-2 h-4 w-4" />
                Import
              </Button>
              <Button size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Add Proxy
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={proxies}
            loading={loading}
            emptyTitle="No proxies"
            emptyDescription="Add proxies to use with registration tasks."
            keyExtractor={(proxy) => proxy.id}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Quick Add</CardTitle>
          <CardDescription>
            Add a proxy in format: protocol://user:pass@host:port
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="http://user:pass@host:port"
              value={newProxy}
              onChange={(e) => setNewProxy(e.target.value)}
            />
            <Button>Add</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
