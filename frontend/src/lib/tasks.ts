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

export function getTaskStatusText(status: string, t?: (key: string, fallback: string) => string) {
  if (t) {
    return t(`history.status.${status}`, getRawStatusText(status))
  }
  return getRawStatusText(status)
}

function getRawStatusText(status: string) {
  switch (status) {
    case 'succeeded':
      return '已完成'
    case 'failed':
      return '失败'
    case 'interrupted':
      return '已中断'
    case 'cancelled':
      return '已取消'
    case 'cancel_requested':
      return '取消中'
    case 'running':
      return '执行中'
    case 'claimed':
      return '已领取'
    case 'pending':
      return '排队中'
    default:
      return status
  }
}
