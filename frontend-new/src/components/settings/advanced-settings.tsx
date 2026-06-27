"use client";

import { useState } from "react";
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
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Download, Upload, Trash2, RefreshCw } from "lucide-react";

export function AdvancedSettings() {
  const [debugMode, setDebugMode] = useState(false);
  const [logLevel, setLogLevel] = useState("info");
  const [maxConcurrent, setMaxConcurrent] = useState(5);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Advanced Settings</CardTitle>
          <CardDescription>
            Configure advanced options for the application.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Log Level</Label>
              <Select value={logLevel} onValueChange={(v) => setLogLevel(v ?? "info")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="debug">Debug</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                  <SelectItem value="warning">Warning</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Max Concurrent Tasks</Label>
              <Input
                type="number"
                value={maxConcurrent}
                onChange={(e) => setMaxConcurrent(parseInt(e.target.value) || 5)}
              />
            </div>

            <div className="space-y-2">
              <Label>Debug Mode</Label>
              <div className="flex items-center h-10">
                <Switch checked={debugMode} onCheckedChange={setDebugMode} />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Data Management</CardTitle>
          <CardDescription>
            Export, import, or clear application data.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              Export Config
            </Button>
            <Button variant="outline">
              <Upload className="mr-2 h-4 w-4" />
              Import Config
            </Button>
            <Button variant="outline">
              <RefreshCw className="mr-2 h-4 w-4" />
              Clear Cache
            </Button>
            <Button variant="destructive">
              <Trash2 className="mr-2 h-4 w-4" />
              Reset All
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
