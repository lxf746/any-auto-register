"""
数据模型定义
"""
from dataclasses import dataclass, field
from typing import Optional, List, Any


@dataclass
class UserInfo:
    """用户信息"""
    id: int
    username: str
    email: str
    balance: str
    status: int
    api_email_enabled: int = 0
    api_email_price: str = "0.0000"


@dataclass
class EmailItem:
    """邮箱列表项"""
    id: int
    address: str
    type: str
    status: int
    domain: str
    total_used: int = 0
    success_count: int = 0
    fail_count: int = 0


@dataclass
class ProjectPrice:
    """项目定价"""
    email_type: str
    code_price: str
    buy_price: str


@dataclass
class ProjectItem:
    """项目信息"""
    id: int
    name: str
    code: str
    email_types: List[str]
    timeout_seconds: int
    warranty_hours: int
    daily_limit: int
    description: str
    prices: List[ProjectPrice] = field(default_factory=list)


@dataclass
class OrderInfo:
    """订单信息（创建后）"""
    order_no: str
    email_address: str
    project: str
    price: str
    timeout_seconds: int
    expired_at: str


@dataclass
class OrderCode:
    """订单验证码查询结果"""
    order_no: str
    status: str  # pending / success / timeout / cancelled
    verification_code: Optional[str] = None
    mail_from: Optional[str] = None
    mail_subject: Optional[str] = None
    mail_body_html: Optional[str] = None


@dataclass
class PurchaseItem:
    """已购邮箱"""
    id: int
    email_address: str
    token: str
    project_name: str
    price: str
    status: int = 1
    tag_id: int = 0
    tag_name: str = ""
    user_disabled: int = 0
    warranty_hours: int = 0
    warranty_until: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class TokenCode:
    """Token 查询验证码结果"""
    email_address: str
    project: str
    has_new_mail: bool
    verification_code: Optional[str] = None
    mail: Optional[dict] = None


@dataclass
class TokenAliveResult:
    """Token 测活结果"""
    email_address: str
    project: str
    alive: bool
    status: str
    message: str = ""
    mail_count: int = 0


@dataclass
class TokenMailItem:
    """Token 邮件列表项"""
    message_id: str
    from_addr: str = ""
    subject: str = ""
    body: str = ""
    html_body: str = ""
    received_at: str = ""


@dataclass
class TokenMailList:
    """Token 邮件列表结果"""
    email_address: str
    project: str
    warranty_until: str = ""
    mails: List[TokenMailItem] = field(default_factory=list)


@dataclass
class TokenMailDetail:
    """Token 邮件详情结果"""
    message_id: str
    from_addr: str = ""
    to: str = ""
    subject: str = ""
    body_text: str = ""
    body_html: str = ""
    received_at: str = ""
    verification_code: str = ""


@dataclass
class AppealInfo:
    """申述信息"""
    appeal_no: str
    appeal_type: int
    reason: str
    description: str
    status: int
    created_at: Optional[str] = None


@dataclass
class TagItem:
    """邮箱标签"""
    id: int
    name: str
    remark: str = ""
    limit_type: int = 0  # 0=不下发 1=可下发
    purchase_count: int = 0
    created_at: Optional[str] = None


@dataclass
class PageResult:
    """分页结果"""
    list: List[Any]
    total: int
    page: int
    page_size: int


# ===== 供应商模型 =====

@dataclass
class SupplierProfile:
    """供应商个人信息"""
    id: int
    username: str
    email: str
    balance: str
    frozen_balance: str
    code_commission_rate: str
    buy_commission_rate: str
    status: int


@dataclass
class SupplierEmailItem:
    """供应商邮箱列表项"""
    id: int
    address: str
    type: str
    status: int
    domain: str
    total_used: int = 0
    success_count: int = 0
    fail_count: int = 0
    is_short_term: int = 0


@dataclass
class AppealItem:
    """申述列表项（供应商端）"""
    id: int
    appeal_no: str
    order_no: str
    reason: str
    status: int
    created_at: str


@dataclass
class AppealDetail:
    """申述详情"""
    appeal_no: str
    order_no: str
    reason: str
    status: int
    supplier_reply: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class ImportResult:
    """导入邮箱结果"""
    success: int
    duplicate: int
    failed: int


@dataclass
class DashboardSummary:
    """供应商数据看板"""
    total_emails: int
    active_emails: int
    total_assigned: int
    total_success: int
    success_rate: float
    total_commission: str
    available_balance: str
    today_assigned: int
    today_success: int
    today_commission: str
    email_category: dict = field(default_factory=dict)
