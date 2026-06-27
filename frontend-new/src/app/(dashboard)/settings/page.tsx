"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MailboxProviders } from "@/components/settings/mailbox-providers";
import { SmsProviders } from "@/components/settings/sms-providers";
import { CaptchaProviders } from "@/components/settings/captcha-providers";
import { ProxySettings } from "@/components/settings/proxy-settings";
import { PlatformConfig } from "@/components/settings/platform-config";
import { AdvancedSettings } from "@/components/settings/advanced-settings";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Settings</h2>
        <p className="text-muted-foreground">
          Configure providers, proxies, and platform settings.
        </p>
      </div>

      <Tabs defaultValue="mailbox" className="space-y-4">
        <TabsList>
          <TabsTrigger value="mailbox">Mailbox</TabsTrigger>
          <TabsTrigger value="sms">SMS</TabsTrigger>
          <TabsTrigger value="captcha">Captcha</TabsTrigger>
          <TabsTrigger value="proxies">Proxies</TabsTrigger>
          <TabsTrigger value="platforms">Platforms</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
        </TabsList>

        <TabsContent value="mailbox">
          <MailboxProviders />
        </TabsContent>

        <TabsContent value="sms">
          <SmsProviders />
        </TabsContent>

        <TabsContent value="captcha">
          <CaptchaProviders />
        </TabsContent>

        <TabsContent value="proxies">
          <ProxySettings />
        </TabsContent>

        <TabsContent value="platforms">
          <PlatformConfig />
        </TabsContent>

        <TabsContent value="advanced">
          <AdvancedSettings />
        </TabsContent>
      </Tabs>
    </div>
  );
}
