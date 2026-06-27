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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Save } from "lucide-react";

interface PlatformSettings {
  name: string;
  rateLimit: number;
  executorType: string;
  autoRetry: boolean;
  maxConcurrent: number;
}

export function PlatformConfig() {
  const [platforms, setPlatforms] = useState<PlatformSettings[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlatform, setSelectedPlatform] = useState<string>("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Mock data for now
    setPlatforms([
      { name: "chatgpt", rateLimit: 3, executorType: "protocol", autoRetry: true, maxConcurrent: 5 },
      { name: "cursor", rateLimit: 5, executorType: "playwright", autoRetry: false, maxConcurrent: 3 },
      { name: "windsurf", rateLimit: 2, executorType: "protocol", autoRetry: true, maxConcurrent: 2 },
    ]);
    setLoading(false);
  }, []);

  const currentPlatform = platforms.find((p) => p.name === selectedPlatform);

  const handleSave = async () => {
    setSaving(true);
    // TODO: Save to API
    setTimeout(() => setSaving(false), 500);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Platform Configuration</CardTitle>
        <CardDescription>
          Configure per-platform settings like rate limits and executor types.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Select Platform</Label>
          <Select value={selectedPlatform} onValueChange={(v) => setSelectedPlatform(v ?? "")}>
            <SelectTrigger>
              <SelectValue placeholder="Choose a platform" />
            </SelectTrigger>
            <SelectContent>
              {platforms.map((p) => (
                <SelectItem key={p.name} value={p.name}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {currentPlatform && (
          <div className="space-y-4 border-t pt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Rate Limit (req/min)</Label>
                <Input
                  type="number"
                  value={currentPlatform.rateLimit}
                  onChange={(e) => {
                    const value = parseInt(e.target.value) || 1;
                    setPlatforms((prev) =>
                      prev.map((p) =>
                        p.name === selectedPlatform
                          ? { ...p, rateLimit: value }
                          : p
                      )
                    );
                  }}
                />
              </div>

              <div className="space-y-2">
                <Label>Executor Type</Label>
                <Select
                  value={currentPlatform.executorType}
                  onValueChange={(v) => {
                    setPlatforms((prev) =>
                      prev.map((p) =>
                        p.name === selectedPlatform
                          ? { ...p, executorType: v ?? "protocol" }
                          : p
                      )
                    );
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="protocol">Protocol</SelectItem>
                    <SelectItem value="playwright">Playwright</SelectItem>
                    <SelectItem value="camoufox">Camoufox</SelectItem>
                    <SelectItem value="patchright">Patchright</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Max Concurrent</Label>
                <Input
                  type="number"
                  value={currentPlatform.maxConcurrent}
                  onChange={(e) => {
                    const value = parseInt(e.target.value) || 1;
                    setPlatforms((prev) =>
                      prev.map((p) =>
                        p.name === selectedPlatform
                          ? { ...p, maxConcurrent: value }
                          : p
                      )
                    );
                  }}
                />
              </div>

              <div className="space-y-2">
                <Label>Auto Retry</Label>
                <div className="flex items-center h-10">
                  <Switch
                    checked={currentPlatform.autoRetry}
                    onCheckedChange={(checked) => {
                      setPlatforms((prev) =>
                        prev.map((p) =>
                          p.name === selectedPlatform
                            ? { ...p, autoRetry: checked }
                            : p
                        )
                      );
                    }}
                  />
                </div>
              </div>
            </div>

            <Button onClick={handleSave} disabled={saving}>
              <Save className="mr-2 h-4 w-4" />
              {saving ? "Saving..." : "Save Settings"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
