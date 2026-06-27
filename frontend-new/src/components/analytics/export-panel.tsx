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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Download, FileJson, FileSpreadsheet } from "lucide-react";
import { toast } from "sonner";

interface ExportPanelProps {
  dateRange: string;
}

export function ExportPanel({ dateRange }: ExportPanelProps) {
  const [format, setFormat] = useState("json");
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      // Generate mock export data
      const data = {
        dateRange,
        exportedAt: new Date().toISOString(),
        summary: {
          totalRegistrations: 1234,
          successRate: 87.5,
          platforms: ["chatgpt", "cursor", "windsurf"],
        },
      };

      let content: string;
      let filename: string;
      let mimeType: string;

      if (format === "json") {
        content = JSON.stringify(data, null, 2);
        filename = `analytics-${dateRange}.json`;
        mimeType = "application/json";
      } else {
        // CSV format
        const rows = [
          "Date,Success,Failed,Total",
          ...Array.from({ length: 7 }, (_, i) => {
            const date = new Date();
            date.setDate(date.getDate() - i);
            const success = Math.floor(Math.random() * 50) + 10;
            const failed = Math.floor(Math.random() * 10);
            return `${date.toISOString().split("T")[0]},${success},${failed},${success + failed}`;
          }),
        ];
        content = rows.join("\n");
        filename = `analytics-${dateRange}.csv`;
        mimeType = "text/csv";
      }

      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);

      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (err) {
      toast.error("Export failed");
    } finally {
      setExporting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Export Data</CardTitle>
        <CardDescription>
          Download analytics data in your preferred format.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="text-sm font-medium">Format</label>
            <Select value={format} onValueChange={(v) => setFormat(v ?? "json")}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="json">
                  <div className="flex items-center gap-2">
                    <FileJson className="h-4 w-4" />
                    JSON
                  </div>
                </SelectItem>
                <SelectItem value="csv">
                  <div className="flex items-center gap-2">
                    <FileSpreadsheet className="h-4 w-4" />
                    CSV
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <Button onClick={handleExport} disabled={exporting}>
          <Download className="mr-2 h-4 w-4" />
          {exporting ? "Exporting..." : "Export Data"}
        </Button>
      </CardContent>
    </Card>
  );
}
