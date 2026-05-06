import { translate, type Language } from '@/lib/i18n'

export const TASK_STATUS_VARIANTS: Record<string, any> = {
  pending: 'secondary',
  claimed: 'secondary',
  running: 'default',
  succeeded: 'success',
  failed: 'danger',
  interrupted: 'warning',
  cancel_requested: 'warning',
  cancelled: 'warning',
}

export const TERMINAL_TASK_STATUSES = new Set([
  'succeeded',
  'failed',
  'interrupted',
  'cancelled',
])

export function isTerminalTaskStatus(status: string) {
  return TERMINAL_TASK_STATUSES.has(status)
}

export function getTaskStatusText(status: string, language?: Language) {
  switch (status) {
    case 'succeeded':
      return translate('taskStatus.succeeded', language)
    case 'failed':
      return translate('taskStatus.failed', language)
    case 'interrupted':
      return translate('taskStatus.interrupted', language)
    case 'cancelled':
      return translate('taskStatus.cancelled', language)
    case 'cancel_requested':
      return translate('taskStatus.cancel_requested', language)
    case 'running':
      return translate('taskStatus.running', language)
    case 'claimed':
      return translate('taskStatus.claimed', language)
    case 'pending':
      return translate('taskStatus.pending', language)
    default:
      return status
  }
}
