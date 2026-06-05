import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      "common": {
        "loading": "Loading...",
        "select_placeholder": "Please select...",
        "search_placeholder": "Search...",
        "no_match": "No matching results",
        "cancel": "Cancel",
        "unknown": "Unknown",
        "yes": "Yes",
        "no": "No"
      },
      "app": {
        "title": "Any Auto Register",
        "description": "Multi-platform automated account registration engine",
        "loading": "Loading application...",
        "nav": {
          "dashboard": "Dashboard",
          "register": "Bulk Register",
          "accounts": "Accounts",
          "proxies": "Proxies",
          "settings": "Settings",
          "history": "Task History"
        },
        "theme": {
          "light": "Light Mode",
          "dark": "Dark Mode",
          "system": "Follow System",
          "to_dark": "Switch to Dark Mode",
          "to_system": "Switch to System Mode",
          "to_light": "Switch to Light Mode"
        },
        "sidebar": {
          "expand": "Expand Sidebar",
          "collapse": "Collapse Sidebar"
        }
      },
      "login": {
        "title": "Please enter access password",
        "placeholder": "Password",
        "error_password": "Incorrect password",
        "request_failed": "Request failed",
        "btn_verifying": "Verifying...",
        "btn_login": "Login"
      },
      "dashboard": {
        "title": "Dashboard",
        "stats": {
          "total_accounts": "Total Accounts",
          "trialing": "Trialing",
          "subscribed": "Subscribed",
          "invalidated": "Invalid/Expired",
          "loading": "Loading statistics..."
        },
        "platforms": "Platform Distribution",
        "refresh": "Refresh",
        "no_data": "No data available",
        "no_platform_data": "No platform distribution data available",
        "desktop": {
          "title": "Desktop App Status",
          "installed": "Installed",
          "not_installed": "Not Installed",
          "configured": "Configured",
          "not_configured": "Not Configured",
          "running": "Running",
          "not_running": "Not Running",
          "ready": "Ready",
          "not_ready": "Not Ready",
          "status_ready": "Ready",
          "status_standby": "Standby",
          "not_supported": "Desktop status detection is not supported on this platform",
          "desc": "Desktop account switching and local readiness status"
        },
        "status_dist": "Status Distribution",
        "plan": "Plan",
        "lifecycle": "Lifecycle",
        "validity": "Validity",
        "no_plan_data": "No plan distribution data",
        "no_lifecycle_data": "No lifecycle distribution data",
        "no_validity_data": "No validity distribution data",
        "status_labels": {
          "registered": "Registered",
          "trial": "Trial",
          "subscribed": "Subscribed",
          "expired": "Expired",
          "invalid": "Invalid",
          "free": "Free",
          "eligible": "Eligible",
          "unknown": "Unknown",
          "valid": "Valid",
          "active": "Active",
          "inactive": "Inactive",
          "pending": "Pending"
        }
      },
      "proxies": {
        "title": "Proxy Management",
        "total_label": "Total",
        "active_label": "Active",
        "check_btn": "Check All",
        "add_label": "Add New",
        "add_desc": "Add single proxy or bulk import",
        "region_placeholder": "Region tag (e.g. US, SG)",
        "add_hint": "Supports direct entry of a single proxy or multi-line bulk import. The region tag will be saved for filtering and exit/entry recognition.",
        "add_btn": "Add to Proxy Pool",
        "list_title": "Proxy List",
        "empty": "The proxy pool is empty. Enter a proxy on the left or bulk import to get started.",
        "stats": {
          "total": "Proxies",
          "active": "Enabled",
          "success": "Successes",
          "fail": "Failures"
        },
        "table": {
          "url": "Proxy Address",
          "region": "Region",
          "stats": "Success/Fail",
          "status": "Status",
          "actions": "Actions"
        },
        "row": {
          "active": "Active",
          "inactive": "Disabled",
          "disable_btn": "Disable",
          "enable_btn": "Enable",
          "delete_btn": "Delete"
        }
      },
      "history": {
        "title": "Task History",
        "refresh_btn": "Refresh",
        "recent_title": "Recent Tasks",
        "empty": "No task history logs found",
        "events_count": "{{count}} log entries",
        "error_reason": "Failure Reason",
        "live_log": "Live Log",
        "live_log_desc": "Real-time task execution log",
        "copy_logs": "Copy Logs",
        "waiting_logs": "Waiting for task logs...",
        "stats": {
          "total": "Tasks",
          "success": "Success",
          "fail": "Failed",
          "running": "Running"
        },
        "filter": {
          "all_platforms": "All Platforms",
          "all_statuses": "All Statuses",
          "running": "Running",
          "success": "Success",
          "fail": "Failed",
          "cancelled": "Cancelled",
          "interrupted": "Interrupted",
          "clear": "Clear"
        },
        "table": {
          "time": "Time",
          "id": "Task ID",
          "platform": "Platform",
          "status": "Status",
          "progress": "Progress",
          "stats": "Success/Fail",
          "error": "Error",
          "events": "Logs"
        },
        "status": {
          "succeeded": "Completed",
          "failed": "Failed",
          "interrupted": "Interrupted",
          "cancelled": "Cancelled",
          "cancel_requested": "Cancelling",
          "running": "Running",
          "claimed": "Claimed",
          "pending": "Queueing"
        }
      },
      "update": {
        "available": "New version",
        "downloadable": "is available",
        "current": "current",
        "go_download": "Download",
        "dismiss": "Ignore"
      },
      "settings": {
        "tabs": {
          "general": "General Settings",
          "register": "Registration Strategy",
          "mailbox": "Mailbox Services",
          "captcha": "Captcha Solver",
          "sms": "SMS Provider",
          "proxies": "Proxy Pool",
          "chatgpt": "ChatGPT Settings",
          "advanced": "Advanced Parameters",
          "about": "About App",
          "platform_caps": "Platform Capabilities"
        },
        "general": {
          "theme": {
            "title": "Theme Theme",
            "desc": "Select the application theme, takes effect immediately."
          },
          "strategy": {
            "title": "Default Registration Strategy",
            "desc": "Configure the default registration options. Page forms and accounts page reuse these configurations.",
            "identity": "Default Registration Identity",
            "oauth": "Default OAuth Entrance",
            "oauth_none": "Do not pre-select, choose on registration page",
            "executor": "Default Executor Channel"
          },
          "browser": {
            "title": "Browser Session Reuse",
            "desc": "When third-party OAuth goes with automated background browsers, you can reuse your local Google Chrome session.",
            "email": "Target Account Email",
            "chrome_profile": "Chrome Profile Path",
            "chrome_cdp": "Chrome CDP Address"
          },
          "save_success": "Saved successfully! ✓",
          "saving": "Saving...",
          "save_btn": "Save Settings"
        },
        "about": {
          "version": {
            "title": "Version Info",
            "desc": "Current application version and updates checker.",
            "current": "Current Version",
            "up_to_date": "Up-to-date",
            "check_btn": "Check for Updates",
            "new_available": "New version v{{tag}} available",
            "published_at": "Published at "
          },
          "project": {
            "title": "Project Details",
            "name": "Project Name",
            "stack": "Tech Stack",
            "license": "License"
          }
        },
        "advanced": {
          "solver": {
            "title": "Turnstile Solver",
            "desc": "Local Turnstile solver service status for browserless solving.",
            "checking": "Detecting...",
            "running": "Running",
            "not_running": "Not Running",
            "restart_btn": "Restart Solver"
          },
          "caps": {
            "title": "Platform Capabilities",
            "desc": "Customize executor channels, registration identity, and OAuth entrances supported by platforms.",
            "reset_btn": "Restore Default",
            "exec_mode": "Executor Mode",
            "identity": "Identity Mode",
            "oauth": "OAuth Providers",
            "saved": "Saved! ✓",
            "saving": "Saving...",
            "save_btn": "Save Capabilities"
          }
        },
        "providers": {
          "cat": {
            "free": {
              "label": "Free / Out-of-the-box",
              "desc": "Directly usable, no self-hosting required"
            },
            "selfhost": {
              "label": "Self-hosted Services",
              "desc": "Requires manual deployment of a backend helper"
            },
            "thirdparty": {
              "label": "Third-party APIs",
              "desc": "Requires API key credentials from third-party platforms"
            },
            "custom": {
              "label": "Custom Providers",
              "desc": "Integrate any API via custom HTTP endpoint drivers"
            }
          },
          "no_config": "This provider does not require additional settings.",
          "enabled": "Enabled",
          "disabled": "Disabled",
          "test_failed": "Test connection request failed",
          "saved": "Saved successfully! ✓",
          "saving": "Saving settings...",
          "save_btn": "Save Settings",
          "testing": "Testing connection...",
          "test_btn": "Test Connection",
          "default_badge": "Default",
          "edit_btn": "Edit",
          "testing_compact": "Testing",
          "test_btn_compact": "Test",
          "default_btn_active": "Default ✓",
          "default_btn": "Set Default",
          "delete_btn": "Delete",
          "add_custom_btn": "Add Custom {{type}} Service",
          "type_mail": "Mailbox",
          "type_captcha": "Captcha Solver",
          "type_sms": "SMS Provider"
        },
        "providers_meta": {
          "mailbox": {
            "tabLabel": "Mailbox Services",
            "detailTitle": "Mailbox Provider Details",
            "addTitle": "Add Mailbox Provider",
            "createTitle": "Create Dynamic Mailbox Provider",
            "addDialogHint": "Select from mailbox provider catalog",
            "usageHint": "This mailbox service configuration is only used when the registration identity is set to \"System Mailbox\". You can view details, edit, set default, and delete directly in the list rows.",
            "listTitle": "Mailbox Provider List",
            "listDescription": "{{count}} configurations, support details, edit, default, delete.",
            "noAvailableText": "No mailbox providers available to add",
            "availableText": "There are {{count}} mailbox providers available to add",
            "emptyText": "No mailbox provider configurations currently. Please add one first.",
            "metricLabel": "Mailbox Services"
          },
          "captcha": {
            "tabLabel": "Captcha Services",
            "detailTitle": "Captcha Provider Details",
            "addTitle": "Add Captcha Provider",
            "createTitle": "Create Dynamic Captcha Provider",
            "addDialogHint": "Select from captcha provider catalog",
            "usageHint": "Protocol mode automatically selects remote captcha solving services in the enabled order; browser mode uses the current default captcha provider. You can view details, edit, set default, and delete directly in the list rows.",
            "listTitle": "Captcha Provider List",
            "listDescription": "{{count}} configurations, protocol mode will read enabled items in order.",
            "noAvailableText": "No captcha providers available to add",
            "availableText": "There are {{count}} captcha providers available to add",
            "emptyText": "No captcha provider configurations currently. Please add one first.",
            "metricLabel": "Captcha Services"
          },
          "sms": {
            "tabLabel": "SMS Services",
            "detailTitle": "SMS Provider Details",
            "addTitle": "Add SMS Provider",
            "createTitle": "Create Dynamic SMS Provider",
            "addDialogHint": "Select from SMS provider catalog",
            "usageHint": "When a platform requires phone number verification, it will request a temporary number using the enabled SMS providers here and fill in the SMS verification code. You can view details, edit, set default, and delete directly in the list rows.",
            "listTitle": "SMS Provider List",
            "listDescription": "{{count}} configurations, phone & SMS validation will prioritize using the default item.",
            "noAvailableText": "No SMS providers available to add",
            "availableText": "There are {{count}} SMS providers available to add",
            "emptyText": "No SMS provider configurations currently. Please add one first.",
            "metricLabel": "SMS Services"
          }
        },
        "herosms_tools": {
          "title": "HeroSMS Tools",
          "desc": "Query balance/price using the current API Key, service code, and country ID.",
          "query_balance": "Check Balance",
          "query_price": "Check Price",
          "querying": "Querying...",
          "balance_result": "Balance: ${{balance}}",
          "balance_failed": "Failed to query balance",
          "price_result": "Current Price: ${{cost}}, Available Count: {{count}}",
          "price_not_found": "No price information found for the current service/country",
          "price_failed": "Failed to query price"
        },
        "field_categories": {
          "connection": "Connection & Endpoints",
          "auth": "Authentication",
          "identity": "Mailbox Identity",
          "other": "Other Settings"
        },
        "platform_caps_tab": {
          "title": "Advanced: Platform Capabilities",
          "exec_mode": "Executor Mode",
          "identity": "Identity Mode",
          "oauth": "OAuth Providers",
          "restore_btn": "Restore Defaults",
          "save_btn": "Save Settings",
          "saving": "Saving...",
          "saved": "Saved ✓"
        }
      },
      "accounts": {
        "meta": {
          "lifecycle": "Lifecycle",
          "plan": "Plan",
          "validity": "Validity",
          "credits": "Credits",
          "used": "Used"
        },
        "action_result_labels": {
          "valid": "Valid",
          "membership_type": "Membership Type",
          "plan": "Plan",
          "plan_id": "Plan ID",
          "has_valid_payment_method": "Has Card",
          "trial_eligible": "Trial Eligible",
          "trial_length_days": "Trial Days",
          "remaining_credits": "Remaining Credits",
          "usage_total": "Usage Total",
          "plan_credits": "Plan Credits",
          "kiro_plan": "Kiro Plan",
          "days_until_reset": "Days Until Reset",
          "next_reset_at": "Next Reset At",
          "portal_available": "Portal Available",
          "desktop_app": "Desktop App",
          "desktop_running": "Desktop Running",
          "desktop_ready": "Desktop Ready",
          "key_prefix": "Key Prefix",
          "key_name": "Key Name",
          "key_id": "Key ID"
        },
        "title": "Account Management",
        "total": "Total: {{count}}",
        "trial_count": "Trial: {{count}}",
        "subscribed_count": "Subscribed: {{count}}",
        "link_count": "Link: {{count}}",
        "invalid_count": "Invalid: {{count}}",
        "selected_count": "Selected: {{count}}",
        "auto_register_btn": "Auto Register",
        "import_btn": "Import",
        "export_btn": "Export",
        "export_selected_btn": "Export Selected ({{count}})",
        "add_manual_btn": "Add Manually",
        "search_placeholder": "Search email...",
        "all_statuses": "All Statuses",
        "status_registered": "Registered",
        "status_trial": "Trialing",
        "status_subscribed": "Subscribed",
        "status_free": "Free",
        "status_eligible": "Eligible",
        "status_expired": "Expired",
        "status_invalid": "Invalid",
        "refresh_limits": "Refresh Credits",
        "refreshing_limits": "Refreshing...",
        "delete_selected": "Delete",
        "deleting": "Deleting...",
        "confirm_delete_selected": "Are you sure you want to delete the selected {{count}} accounts? This action cannot be undone.",
        "confirm_delete_single": "Are you sure you want to delete {{email}}?",
        "table": {
          "email": "Email",
          "password": "Password",
          "status": "Status",
          "link": "Link",
          "date": "Date",
          "actions": "Actions"
        },
        "no_data": "No Data",
        "no_data_desc": "No account records found for the current platform. You can add manually or bulk import via file.",
        "mailbox_verification": "Verification Mailbox",
        "remote_mailbox": "Remote Mailbox",
        "detail_modal": {
          "title": "Account Details",
          "core_status": "Core Status",
          "lifecycle": "Lifecycle",
          "validity": "Validity",
          "plan_state": "Plan State",
          "mailbox_verification_email": "Verification email",
          "provider_accounts": "Provider Accounts",
          "login_identifier": "Login Identifier",
          "platform_credentials": "Platform Credentials",
          "primary_token": "Primary Token",
          "cashier_url": "Trial Link",
          "saving": "Saving...",
          "save": "Save",
          "cancel": "Cancel",
          "edit_switch": "Edit"
        },
        "import_modal": {
          "title": "Bulk Import",
          "format_hint": "Format per line: email password [cashier_url]",
          "importing": "Importing...",
          "import": "Import",
          "success": "Successfully imported {{count}} accounts",
          "failed": "Failed: {{message}}"
        },
        "add_modal": {
          "title": "Add Account Manually",
          "email": "Email",
          "password": "Password",
          "primary_token": "Primary Token",
          "cashier_url": "Trial Link",
          "lifecycle": "Lifecycle Status",
          "saving": "Saving...",
          "save": "Save"
        },
        "action_task_modal": {
          "title": "Platform Action",
          "subtitle": "Task status, error summary and real-time logs in one view"
        },
        "action_params_modal": {
          "title": "Action Parameters",
          "subtitle": "Fill in the required parameters to execute this action",
          "executing": "Executing...",
          "execute": "Execute"
        },
        "action_result_modal": {
          "title": "Action Result",
          "subtitle": "Operation result",
          "copy": "Copy",
          "url_copied_toast": "Payment link has been opened in a new tab, link copied to clipboard"
        },
        "action_menu": {
          "detail": "Detail",
          "more": "More",
          "delete": "Delete",
          "executing": "Executing..."
        },
        "register_modal": {
          "title": "Register {{platform}}",
          "loading": "Loading registration configuration...",
          "step1": "Step 1 · Choose Identity",
          "step1_desc": "What is supported by the current platform is displayed here, no need to study capability settings first.",
          "step2": "Step 2 · Choose Executor Mode",
          "step2_desc": "All modes run automatically, only the protocol or browser channel is different.",
          "count": "Registration Count",
          "concurrency": "Concurrency",
          "summary": {
            "identity": "Registration Identity",
            "executor": "Executor Mode",
            "captcha": "Captcha Strategy"
          },
          "browser_warn": "Browser background automatic mode relies on Chrome Profile or Chrome CDP. Visual browser automatic mode is used when not configured.",
          "start_btn": "Start Auto Registration",
          "starting": "Starting...",
          "no_mailbox_provider": "No default mailbox provider configured, please enable a mailbox provider in settings first."
        }
      },
      "register": {
        "basic_config": "Basic Configuration",
        "platform": "Platform",
        "batch_count": "Registration Count",
        "proxy_opt": "Proxy (Optional)",
        "step1_title": "Step 1 · Registration Identity",
        "step2_title": "Step 2 · Executor Channel",
        "oauth_email_opt": "Target Email Hint (Optional)",
        "chrome_profile_path": "Chrome Profile Path",
        "chrome_cdp_address": "Chrome CDP Address",
        "browser_reuse_hint": "For third-party OAuth background browser tasks, configuring Chrome Profile or CDP helps reuse local logged-in sessions.",
        "system_mailbox_config": "System Mailbox Configuration",
        "mailbox_service": "Mailbox Service",
        "no_mailbox_providers": "No enabled mailbox provider found. Please add and enable a default mailbox provider in settings first.",
        "sms_config": "SMS Service Configuration",
        "sms_service": "SMS Service",
        "summary_title": "Orchestration Summary",
        "btn_registering": "Registering...",
        "btn_start": "Start Registration",
        "task_status": "Execution Status",
        "task_status_label": "Status",
        "task_progress_label": "Progress",
        "task_success_label": "Success",
        "task_fail_label": "Failed",
        "task_id_label": "Task ID",
        "task_interrupted": "Task was interrupted due to backend service restart",
        "task_cancelled": "Task has been cancelled",
        "live_log": "Real-time Log",
        "waiting_execution": "Waiting to Execute",
        "waiting_desc": "Execution logs and status details will appear here once the task starts.",
        "metadata_error": "Failed to load provider metadata. Please restart backend and refresh the page."
      }
    }
  },
  zh: {
    translation: {
      "common": {
        "loading": "加载中...",
        "select_placeholder": "请选择...",
        "search_placeholder": "搜索...",
        "no_match": "无匹配结果",
        "cancel": "取消",
        "unknown": "未知",
        "yes": "是",
        "no": "否"
      },
      "app": {
        "title": "Any Auto Register",
        "description": "多平台自动化账号注册引擎",
        "loading": "应用加载中...",
        "nav": {
          "dashboard": "控制台",
          "register": "批量注册",
          "accounts": "账号管理",
          "proxies": "代理管理",
          "settings": "系统设置",
          "history": "任务历史"
        },
        "theme": {
          "light": "浅色",
          "dark": "深色",
          "system": "跟随系统",
          "to_dark": "切换到深色模式",
          "to_system": "切换到跟随系统",
          "to_light": "切换到浅色模式"
        },
        "sidebar": {
          "expand": "展开侧边栏",
          "collapse": "折叠侧边栏"
        }
      },
      "login": {
        "title": "请输入访问密码",
        "placeholder": "密码",
        "error_password": "密码错误",
        "request_failed": "请求失败",
        "btn_verifying": "验证中...",
        "btn_login": "登 录"
      },
      "dashboard": {
        "title": "控制台",
        "stats": {
          "total_accounts": "总账号数",
          "trialing": "试用中",
          "subscribed": "已订阅",
          "invalidated": "已失效",
          "loading": "正在加载统计数据..."
        },
        "platforms": "平台分布",
        "refresh": "刷新",
        "no_data": "暂无数据",
        "no_platform_data": "暂无平台分布数据",
        "desktop": {
          "title": "桌面应用状态",
          "installed": "已安装",
          "not_installed": "未安装",
          "configured": "已配置",
          "not_configured": "未配置",
          "running": "已打开",
          "not_running": "未打开",
          "ready": "已就绪",
          "not_ready": "未就绪",
          "status_ready": "就绪",
          "status_standby": "待命",
          "not_supported": "当前平台暂未接入桌面状态探测",
          "desc": "桌面账号切换与本地就绪状态"
        },
        "status_dist": "状态分布",
        "plan": "套餐",
        "lifecycle": "生命周期",
        "validity": "有效性",
        "no_plan_data": "暂无套餐分布数据",
        "no_lifecycle_data": "暂无生命周期分布数据",
        "no_validity_data": "暂无有效性分布数据",
        "status_labels": {
          "registered": "已注册",
          "trial": "试用",
          "subscribed": "订阅",
          "expired": "过期",
          "invalid": "失效",
          "free": "空闲",
          "eligible": "可用",
          "unknown": "未知",
          "valid": "有效",
          "active": "活跃",
          "inactive": "未激活",
          "pending": "待处理"
        }
      },
      "proxies": {
        "title": "代理管理",
        "total_label": "总量",
        "active_label": "活跃",
        "check_btn": "检测全部",
        "add_label": "新增",
        "add_desc": "添加代理或批量导入",
        "region_placeholder": "地区标签 (如 US, SG)",
        "add_hint": "支持单条代理直接录入，也支持多行批量导入。地区标签会一起写入，用于后续筛选和出入口识别。",
        "add_btn": "添加到代理池",
        "list_title": "代理列表",
        "empty": "当前代理池为空，可以先从左侧输入一个或批量导入。",
        "stats": {
          "total": "代理数",
          "active": "启用",
          "success": "成功次数",
          "fail": "失败次数"
        },
        "table": {
          "url": "代理地址",
          "region": "地区",
          "stats": "成功/失败",
          "status": "状态",
          "actions": "操作"
        },
        "row": {
          "active": "活跃",
          "inactive": "禁用",
          "disable_btn": "停用",
          "enable_btn": "启用",
          "delete_btn": "删除"
        }
      },
      "history": {
        "title": "任务记录",
        "refresh_btn": "刷新",
        "recent_title": "最近任务",
        "empty": "暂无任务记录",
        "events_count": "{{count}} 条日志",
        "error_reason": "失败原因",
        "live_log": "Live Log",
        "live_log_desc": "实时执行日志",
        "copy_logs": "复制日志",
        "waiting_logs": "等待任务日志...",
        "stats": {
          "total": "任务数",
          "success": "成功",
          "fail": "失败",
          "running": "进行中"
        },
        "filter": {
          "all_platforms": "全部平台",
          "all_statuses": "全部状态",
          "running": "运行中",
          "success": "成功",
          "fail": "失败",
          "cancelled": "已取消",
          "interrupted": "已中断",
          "clear": "清除"
        },
        "table": {
          "time": "时间",
          "id": "任务 ID",
          "platform": "平台",
          "status": "状态",
          "progress": "进度",
          "stats": "成功/失败",
          "error": "错误",
          "events": "日志"
        },
        "status": {
          "succeeded": "已完成",
          "failed": "失败",
          "interrupted": "已中断",
          "cancelled": "已取消",
          "cancel_requested": "取消中",
          "running": "执行中",
          "claimed": "已领取",
          "pending": "排队中"
        }
      },
      "update": {
        "available": "有新版本",
        "downloadable": "可下载",
        "current": "当前",
        "go_download": "前往下载",
        "dismiss": "忽略"
      },
      "settings": {
        "tabs": {
          "general": "常规设置",
          "register": "注册策略",
          "mailbox": "邮箱服务",
          "captcha": "验证服务",
          "sms": "接码服务",
          "proxies": "代理资源",
          "chatgpt": "ChatGPT",
          "advanced": "高级设置",
          "about": "关于",
          "platform_caps": "高级：平台能力"
        },
        "general": {
          "theme": {
            "title": "外观主题",
            "desc": "选择应用的外观主题，立即生效。"
          },
          "strategy": {
            "title": "默认注册策略",
            "desc": "这里配置的是默认行为，账号列表和注册页会直接复用这些设置。",
            "identity": "默认注册身份",
            "oauth": "默认第三方入口",
            "oauth_none": "不预选，由当前页面选择",
            "executor": "默认执行方式"
          },
          "browser": {
            "title": "浏览器复用",
            "desc": "第三方账号走后台浏览器自动时，通常需要复用本机已登录浏览器。",
            "email": "预期登录邮箱",
            "chrome_profile": "Chrome Profile 路径",
            "chrome_cdp": "Chrome CDP 地址"
          },
          "save_success": "配置保存成功！ ✓",
          "saving": "保存中...",
          "save_btn": "保存系统配置"
        },
        "about": {
          "version": {
            "title": "版本信息",
            "desc": "当前应用版本与更新检测。",
            "current": "当前版本",
            "up_to_date": "已是最新",
            "check_btn": "检查更新",
            "new_available": "新版本 v{{tag}} 可用",
            "published_at": "发布于 "
          },
          "project": {
            "title": "项目信息",
            "name": "项目名称",
            "stack": "技术栈",
            "license": "开源协议"
          }
        },
        "advanced": {
          "solver": {
            "title": "Turnstile 求解器",
            "desc": "本地 Turnstile 验证码求解服务状态。",
            "checking": "检测中",
            "running": "运行中",
            "not_running": "未运行",
            "restart_btn": "重启 Solver"
          },
          "caps": {
            "title": "平台能力",
            "desc": "自定义各平台支持的执行方式、注册身份和第三方入口。",
            "reset_btn": "恢复默认",
            "exec_mode": "执行方式",
            "identity": "注册身份",
            "oauth": "第三方入口",
            "saved": "已保存 ✓",
            "saving": "保存中...",
            "save_btn": "保存"
          }
        },
        "providers": {
          "cat": {
            "free": {
              "label": "免费 / 开箱即用",
              "desc": "无需自建服务，直接使用"
            },
            "selfhost": {
              "label": "需要自建服务",
              "desc": "需要自行部署后端服务"
            },
            "thirdparty": {
              "label": "第三方服务",
              "desc": "需要注册第三方平台获取凭据"
            },
            "custom": {
              "label": "自定义",
              "desc": "通过通用 HTTP 驱动对接任意 API"
            }
          },
          "no_config": "此服务无需额外配置。",
          "enabled": "已启用",
          "disabled": "未启用",
          "test_failed": "测试请求失败",
          "saved": "已保存 ✓",
          "saving": "保存中...",
          "save_btn": "保存",
          "testing": "测试中...",
          "test_btn": "测试连接",
          "default_badge": "默认",
          "edit_btn": "编辑",
          "testing_compact": "测试中",
          "test_btn_compact": "测试",
          "default_btn_active": "默认 ✓",
          "default_btn": "设默认",
          "delete_btn": "删除",
          "add_custom_btn": "添加自定义{{type}}服务",
          "type_mail": "邮箱",
          "type_captcha": "验证",
          "type_sms": "接码"
        },
        "providers_meta": {
          "mailbox": {
            "tabLabel": "邮箱服务",
            "detailTitle": "邮箱 Provider 详情",
            "addTitle": "新增邮箱 Provider",
            "createTitle": "新建动态邮箱 Provider",
            "addDialogHint": "从邮箱 provider catalog 中选择",
            "usageHint": "只有在注册身份选择“系统邮箱”时，才会使用这里的邮箱服务配置。列表行内可以直接查看详情、编辑、设默认和删除。",
            "listTitle": "邮箱 Provider 列表",
            "listDescription": "{{count}} 个配置，支持查看详情、编辑、设默认、删除。",
            "noAvailableText": "当前没有可新增的邮箱 provider",
            "availableText": "还有 {{count}} 个邮箱 provider 可新增",
            "emptyText": "当前没有邮箱 provider 配置，请先新增一个 provider。",
            "metricLabel": "邮箱服务"
          },
          "captcha": {
            "tabLabel": "验证服务",
            "detailTitle": "验证 Provider 详情",
            "addTitle": "新增验证 Provider",
            "createTitle": "新建动态验证 Provider",
            "addDialogHint": "从验证 provider catalog 中选择",
            "usageHint": "协议模式会按已启用顺序自动选择远程打码服务；浏览器模式使用当前默认的验证码 provider。列表行内可以直接查看详情、编辑、设默认、删除。",
            "listTitle": "验证 Provider 列表",
            "listDescription": "{{count}} 个配置，协议模式会依次读取这里的可用项。",
            "noAvailableText": "当前没有可新增的验证 provider",
            "availableText": "还有 {{count}} 个验证 provider 可新增",
            "emptyText": "当前没有验证 provider 配置，请先新增一个 provider。",
            "metricLabel": "验证码服务"
          },
          "sms": {
            "tabLabel": "接码服务",
            "detailTitle": "接码 Provider 详情",
            "addTitle": "新增接码 Provider",
            "createTitle": "新建动态接码 Provider",
            "addDialogHint": "从接码 provider catalog 中选择",
            "usageHint": "当平台需要手机号验证时，会按这里启用的接码 provider 创建临时号码并回填短信验证码。列表行内可以直接查看详情、编辑、设默认和删除。",
            "listTitle": "接码 Provider 列表",
            "listDescription": "{{count}} 个配置，补手机和短信校验会优先使用这里的默认项。",
            "noAvailableText": "当前没有可新增的接码 provider",
            "availableText": "还有 {{count}} 个接码 provider 可新增",
            "emptyText": "当前没有接码 provider 配置，请先新增一个 provider。",
            "metricLabel": "接码服务"
          }
        },
        "herosms_tools": {
          "title": "HeroSMS 工具",
          "desc": "使用当前 API Key、服务代码和国家 ID 查询余额/价格。",
          "query_balance": "查余额",
          "query_price": "查价格",
          "querying": "查询中...",
          "balance_result": "余额: ${{balance}}",
          "balance_failed": "余额查询失败",
          "price_result": "当前价格: ${{cost}}，可用数量: {{count}}",
          "price_not_found": "未找到当前服务/国家的价格信息",
          "price_failed": "价格查询失败"
        },
        "field_categories": {
          "connection": "连接与端点",
          "auth": "认证",
          "identity": "邮箱身份",
          "other": "其他设置"
        },
        "platform_caps_tab": {
          "title": "高级：平台能力",
          "exec_mode": "执行方式",
          "identity": "注册身份",
          "oauth": "第三方入口",
          "restore_btn": "恢复默认",
          "save_btn": "保存",
          "saving": "保存中...",
          "saved": "已保存 ✓"
        }
      },
      "accounts": {
        "meta": {
          "lifecycle": "生命周期",
          "plan": "套餐",
          "validity": "有效性",
          "credits": "额度",
          "used": "已用"
        },
        "action_result_labels": {
          "valid": "账号有效",
          "membership_type": "套餐",
          "plan": "套餐",
          "plan_id": "Plan ID",
          "has_valid_payment_method": "已绑卡",
          "trial_eligible": "可试用",
          "trial_length_days": "试用天数",
          "remaining_credits": "剩余额度",
          "usage_total": "已用额度",
          "plan_credits": "总额度",
          "kiro_plan": "Kiro 套餐",
          "days_until_reset": "重置倒计时",
          "next_reset_at": "下次重置",
          "portal_available": "Portal 可用",
          "desktop_app": "桌面应用",
          "desktop_running": "桌面已打开",
          "desktop_ready": "桌面就绪",
          "key_prefix": "API Key 前缀",
          "key_name": "Key 名称",
          "key_id": "Key ID"
        },
        "title": "账号管理",
        "total": "共 {{count}} 个",
        "trial_count": "试用 {{count}}",
        "subscribed_count": "订阅 {{count}}",
        "link_count": "链接 {{count}}",
        "invalid_count": "失效 {{count}}",
        "selected_count": "已选 {{count}}",
        "auto_register_btn": "自动注册",
        "import_btn": "导入",
        "export_btn": "导出",
        "export_selected_btn": "导出已选({{count}})",
        "add_manual_btn": "手动新增",
        "search_placeholder": "搜索账号邮箱...",
        "all_statuses": "全部状态",
        "status_registered": "已注册",
        "status_trial": "试用中",
        "status_subscribed": "已订阅",
        "status_free": "免费",
        "status_eligible": "可试用",
        "status_expired": "已过期",
        "status_invalid": "已失效",
        "refresh_limits": "刷新额度",
        "refreshing_limits": "刷新中...",
        "delete_selected": "删除",
        "deleting": "删除中...",
        "confirm_delete_selected": "确认删除选中的 {{count}} 个账号？此操作不可撤销。",
        "confirm_delete_single": "确认删除 {{email}}？",
        "table": {
          "email": "邮箱 (Email)",
          "password": "密码 (Pwd)",
          "status": "状态 (Status)",
          "link": "试用链接 (Link)",
          "date": "注册时间 (Date)",
          "actions": "操作 (Action)"
        },
        "no_data": "暂无数据",
        "no_data_desc": "当前平台没有找到任何账号记录。您可以手动新增或通过导入文件批量添加账号。",
        "mailbox_verification": "验证邮箱",
        "remote_mailbox": "远端邮箱",
        "detail_modal": {
          "title": "账号详情",
          "core_status": "核心状态",
          "lifecycle": "生命周期",
          "validity": "有效性",
          "plan_state": "套餐状态",
          "mailbox_verification_email": "验证码邮箱",
          "provider_accounts": "Provider Accounts",
          "login_identifier": "登录标识",
          "platform_credentials": "Platform Credentials",
          "primary_token": "主凭证",
          "cashier_url": "试用链接",
          "saving": "保存中...",
          "save": "保存",
          "cancel": "取消",
          "edit_switch": "切换到编辑"
        },
        "import_modal": {
          "title": "批量导入",
          "format_hint": "每行格式: email password [cashier_url]",
          "importing": "导入中...",
          "import": "导入",
          "success": "导入成功 {{count}} 个",
          "failed": "失败: {{message}}"
        },
        "add_modal": {
          "title": "手动新增账号",
          "email": "邮箱",
          "password": "密码",
          "primary_token": "主凭证",
          "cashier_url": "试用链接",
          "lifecycle": "生命周期状态",
          "saving": "保存中...",
          "save": "保存"
        },
        "action_task_modal": {
          "title": "Platform Action",
          "subtitle": "任务状态、错误摘要与实时日志集中展示"
        },
        "action_params_modal": {
          "title": "动作参数",
          "subtitle": "填写执行该动作所需的参数",
          "executing": "执行中...",
          "execute": "执行"
        },
        "action_result_modal": {
          "title": "操作结果",
          "subtitle": "操作结果",
          "copy": "复制",
          "url_copied_toast": "支付链接已在新标签打开，链接已复制"
        },
        "action_menu": {
          "detail": "详情",
          "more": "更多",
          "delete": "删除",
          "executing": "执行中..."
        },
        "register_modal": {
          "title": "注册 {{platform}}",
          "loading": "正在加载注册配置...",
          "step1": "Step 1 · 选择注册身份",
          "step1_desc": "当前平台支持什么，这里就显示什么，不再让你先研究平台能力配置。",
          "step2": "Step 2 · 选择执行方式",
          "step2_desc": "所有方式都自动执行，只是协议或浏览器通道不同。",
          "count": "注册数量",
          "concurrency": "并发数",
          "summary": {
            "identity": "注册身份",
            "executor": "执行方式",
            "captcha": "验证策略"
          },
          "browser_warn": "后台浏览器自动依赖 Chrome Profile 或 Chrome CDP，未配置时只允许可视浏览器自动。",
          "start_btn": "开始自动注册",
          "starting": "启动中...",
          "no_mailbox_provider": "未配置默认邮箱 provider，请先到设置页启用一个邮箱 provider"
        }
      },
      "register": {
        "basic_config": "基本配置",
        "platform": "平台",
        "batch_count": "批量数量",
        "proxy_opt": "代理 (可选)",
        "step1_title": "Step 1 · 注册身份",
        "step2_title": "Step 2 · 执行通道",
        "oauth_email_opt": "预期登录邮箱 (可选)",
        "chrome_profile_path": "Chrome Profile 路径",
        "chrome_cdp_address": "Chrome CDP 地址",
        "browser_reuse_hint": "第三方账号走后台浏览器自动时，建议先配置 Chrome Profile 或 Chrome CDP，以便复用本机已登录的浏览器会话。",
        "system_mailbox_config": "系统邮箱配置",
        "mailbox_service": "邮箱服务",
        "no_mailbox_providers": "当前没有已启用的邮箱 provider，请先到设置页新增并启用一个默认邮箱 provider。",
        "sms_config": "短信接码配置",
        "sms_service": "短信服务",
        "summary_title": "当前编排摘要",
        "btn_registering": "注册中...",
        "btn_start": "开始注册",
        "task_status": "执行状态",
        "task_status_label": "状态",
        "task_progress_label": "进度",
        "task_success_label": "成功",
        "task_fail_label": "失败",
        "task_id_label": "任务 ID",
        "task_interrupted": "任务在服务重启后被中断",
        "task_cancelled": "任务已取消",
        "live_log": "实时日志",
        "waiting_execution": "等待执行",
        "waiting_desc": "创建后显示状态与日志。",
        "metadata_error": "未加载到 provider 元数据。请重启后端后刷新页面。"
      }
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: localStorage.getItem('app_lang') || 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
