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

const TASK_STATUS_LABELS: Record<'en' | 'vi' | 'zh', Record<string, string>> = {
  en: {
    succeeded: 'Completed',
    failed: 'Failed',
    interrupted: 'Interrupted',
    cancelled: 'Cancelled',
    cancel_requested: 'Cancelling',
    running: 'Running',
    claimed: 'Claimed',
    pending: 'Queued',
  },
  vi: {
    succeeded: 'Hoàn thành',
    failed: 'Thất bại',
    interrupted: 'Bị gián đoạn',
    cancelled: 'Đã hủy',
    cancel_requested: 'Đang hủy',
    running: 'Đang chạy',
    claimed: 'Đã nhận',
    pending: 'Đang chờ',
  },
  zh: {
    succeeded: '已完成',
    failed: '失败',
    interrupted: '已中断',
    cancelled: '已取消',
    cancel_requested: '取消中',
    running: '执行中',
    claimed: '已领取',
    pending: '排队中',
  },
}

export function getTaskStatusText(status: string, locale: 'en' | 'vi' | 'zh' = 'zh') {
  return TASK_STATUS_LABELS[locale][status] || TASK_STATUS_LABELS.zh[status] || status
}
