"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { platformsApi } from "@/lib/api-client";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Loader2, CheckCircle } from "lucide-react";

interface Platform {
  name: string;
  [key: string]: unknown;
}

interface RegisterTaskResponse {
  task_id: string;
  status: string;
}

export default function RegisterPage() {
  const router = useRouter();
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [platform, setPlatform] = useState("");
  const [count, setCount] = useState(1);
  const [proxy, setProxy] = useState("");
  const [captchaSolver, setCaptchaSolver] = useState("auto");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);

  useEffect(() => {
    platformsApi.list().then((data) => setPlatforms(data as Platform[]));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!platform) {
      toast.error("Please select a platform");
      return;
    }

    setLoading(true);
    try {
      const result = await api.post<RegisterTaskResponse>("/tasks/register", {
        platform,
        count,
        proxy: proxy || undefined,
        captcha_solver: captchaSolver,
      });
      setTaskId(result.task_id);
      setSuccess(true);
      toast.success("Registration task created!");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create task";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  if (success && taskId) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
            <CardTitle className="mt-4">Task Created!</CardTitle>
            <CardDescription>
              Registration task is now running
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-md bg-muted p-3 text-center">
              <p className="text-sm text-muted-foreground">Task ID</p>
              <p className="font-mono text-sm">{taskId}</p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => router.push(`/history/${taskId}`)}
              >
                View Task
              </Button>
              <Button
                className="flex-1"
                onClick={() => {
                  setSuccess(false);
                  setTaskId(null);
                  setPlatform("");
                  setCount(1);
                }}
              >
                Register More
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Register Account</h2>
        <p className="text-muted-foreground">
          Create a new registration task for a platform.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Registration Details</CardTitle>
          <CardDescription>
            Configure your registration task parameters.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="platform">Platform</Label>
              <Select value={platform} onValueChange={(v) => setPlatform(v ?? "")}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a platform" />
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

            <div className="space-y-2">
              <Label htmlFor="count">Number of Accounts</Label>
              <Input
                id="count"
                type="number"
                min={1}
                max={100}
                value={count}
                onChange={(e) => setCount(parseInt(e.target.value) || 1)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="proxy">Proxy (optional)</Label>
              <Input
                id="proxy"
                placeholder="protocol://user:pass@host:port"
                value={proxy}
                onChange={(e) => setProxy(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="captcha">Captcha Solver</Label>
              <Select value={captchaSolver} onValueChange={(v) => setCaptchaSolver(v ?? "auto")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto</SelectItem>
                  <SelectItem value="2captcha">2Captcha</SelectItem>
                  <SelectItem value="capsolver">CapSolver</SelectItem>
                  <SelectItem value="none">None</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating Task...
                </>
              ) : (
                "Start Registration"
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
