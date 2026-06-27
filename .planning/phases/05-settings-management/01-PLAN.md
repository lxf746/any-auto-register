---
phase: 5
phase_name: Settings Management
plan_id: 5-01
plan_name: Provider Configuration + Proxy Management + Platform Settings
objective: |
  Build settings management UI for mailbox providers, SMS providers, captcha providers,
  proxy settings, and per-platform configuration (rate limits, executor types).
requirements: [SM-01, SM-02, SM-03, SM-04, SM-05]
wave: 1
files_modified:
  - frontend-new/src/app/(dashboard)/settings/
  - frontend-new/src/components/settings/
  - frontend-new/src/lib/config.ts
---

# Plan: Settings Management UI

## Objective

Create a comprehensive settings interface for managing all provider configurations, proxy settings, and platform-specific options through the UI.

## Tasks

### Task 1: Settings Layout

Create the settings page structure:

- Create `src/app/(dashboard)/settings/page.tsx`:
  - Tabbed layout: General, Providers, Proxies, Platforms, Advanced
  - Save indicator (shows unsaved changes)
  - Reset to defaults button
- Create `src/components/settings/settings-layout.tsx`:
  - Tab navigation
  - Save/cancel buttons
  - Unsaved changes warning
- Add settings route to sidebar navigation

### Task 2: Mailbox Provider Settings (SM-01)

Build mailbox provider configuration:

- Create `src/components/settings/mailbox-providers.tsx`:
  - List of configured providers
  - Enable/disable toggle for each
  - Configure button opens detail dialog
  - Add new provider button
- Create `src/components/settings/mailbox-provider-dialog.tsx`:
  - Provider type selector (tempmail, etc.)
  - API key input
  - Domain whitelist
  - Rate limit settings
  - Test connection button
  - Save/cancel
- Fetch from `GET /api/v2/config`
- Save to `PUT /api/v2/config`

### Task 3: SMS Provider Settings (SM-02)

Build SMS provider configuration:

- Create `src/components/settings/sms-providers.tsx`:
  - List of SMS providers (HeroSMS, SMSBower, etc.)
  - Enable/disable toggle
  - Balance display
  - Configure button
- Create `src/components/settings/sms-provider-dialog.tsx`:
  - API key/secret inputs
  - Default country selector
  - Default service selector
  - Test SMS button
  - Balance check button
- Integrate with existing `/api/v2/sms/*` endpoints

### Task 4: Captcha Provider Settings (SM-03)

Build captcha solver configuration:

- Create `src/components/settings/captcha-providers.tsx`:
  - List of captcha solvers
  - Enable/disable toggle
  - Success rate display
  - Configure button
- Create `src/components/settings/captcha-provider-dialog.tsx`:
  - Provider type (2captcha, capsolver, etc.)
  - API key input
  - Max concurrent requests
  - Timeout settings
  - Test solve button

### Task 5: Proxy Settings (SM-04)

Build proxy management interface:

- Create `src/app/(dashboard)/settings/proxies/page.tsx`:
  - Proxy list table (IP, Port, Protocol, Status, Location)
  - Add proxy button
  - Bulk import button
  - Check all button
  - Delete selected button
- Create `src/components/settings/proxy-form.tsx`:
  - Protocol selector (HTTP, SOCKS5)
  - IP/hostname input
  - Port input
  - Username/password inputs (optional)
  - Test connection button
- Create `src/components/settings/proxy-bulk-import.tsx`:
  - Text area for bulk paste
  - Format: `protocol://user:pass@host:port` or `host:port`
  - Parse and validate
  - Import button
- Integrate with `/api/v2/proxies/*` endpoints

### Task 6: Platform Configuration (SM-05)

Build per-platform settings:

- Create `src/components/settings/platform-config.tsx`:
  - Platform selector dropdown
  - Rate limit settings (requests per minute)
  - Executor type selector (playwright, camoufox, patchright)
  - Auto-retry toggle
  - Max concurrent registrations
- Create `src/components/settings/platform-capabilities.tsx`:
  - Show platform capabilities
  - Enable/disable specific capabilities
  - Custom field mappings
- Fetch from `GET /api/v2/platforms/{name}/capabilities`
- Save to `PUT /api/v2/platforms/{name}/capabilities`

### Task 7: Advanced Settings

Build advanced configuration:

- Create `src/components/settings/advanced-settings.tsx`:
  - Database settings (read-only, display current)
  - Scheduler settings (max concurrent tasks)
  - Log level selector
  - Debug mode toggle
  - Clear cache button
  - Export/import config buttons
- Create `src/components/settings/config-export.tsx`:
  - Export config as JSON
  - Import config from JSON
  - Validation before import

## Verification

After execution:
1. `/settings` page loads with all tabs
2. Mailbox providers can be configured and tested
3. SMS providers show balance and can be tested
4. Captcha providers can be configured and tested
5. Proxies can be added, bulk imported, and checked
6. Platform settings save correctly
7. Advanced settings work without breaking the app
8. All settings persist after page reload
