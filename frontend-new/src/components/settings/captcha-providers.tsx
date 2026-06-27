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
import { Switch } from "@/components/ui/switch";
import { Plus, Settings, Trash2, CheckCircle } from "lucide-react";

interface CaptchaProvider {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  successRate?: number;
}

export function CaptchaProviders() {
  const [providers, setProviders] = useState<CaptchaProvider[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock data for now
    setProviders([
      { id: "1", name: "2Captcha", type: "2captcha", enabled: true, successRate: 95 },
      { id: "2", name: "CapSolver", type: "capsolver", enabled: false, successRate: 0 },
    ]);
    setLoading(false);
  }, []);

  const toggleProvider = (id: string) => {
    setProviders((prev) =>
      prev.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p))
    );
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Captcha Providers</CardTitle>
            <CardDescription>
              Configure captcha solving services.
            </CardDescription>
          </div>
          <Button size="sm">
            <Plus className="mr-2 h-4 w-4" />
            Add Provider
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {providers.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No captcha providers configured.
          </p>
        ) : (
          <div className="space-y-4">
            {providers.map((provider) => (
              <div
                key={provider.id}
                className="flex items-center justify-between border rounded-lg p-4"
              >
                <div className="flex items-center gap-4">
                  <div>
                    <p className="font-medium">{provider.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {provider.type}
                    </p>
                  </div>
                  <Badge variant={provider.enabled ? "default" : "secondary"}>
                    {provider.enabled ? "Active" : "Inactive"}
                  </Badge>
                  {provider.successRate !== undefined && provider.successRate > 0 && (
                    <div className="flex items-center gap-1 text-sm text-muted-foreground">
                      <CheckCircle className="h-3 w-3" />
                      {provider.successRate}% success
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={provider.enabled}
                    onCheckedChange={() => toggleProvider(provider.id)}
                  />
                  <Button variant="ghost" size="icon">
                    <Settings className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
