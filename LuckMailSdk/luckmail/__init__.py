"""
LuckMailSdk - Python SDK for LuckMail Email System
支持同步/异步双模式，智能识别调用上下文自动切换
"""

from .client import LuckMailClient
from .user import UserAPI
from .supplier import SupplierAPI
from .exceptions import (
    LuckMailError,
    AuthError,
    APIError,
    NetworkError,
    TimeoutError,
)
from .models import (
    UserInfo,
    EmailItem,
    ProjectItem,
    OrderInfo,
    OrderCode,
    PurchaseItem,
    TagItem,
    TokenCode,
    TokenAliveResult,
    TokenMailItem,
    TokenMailList,
    TokenMailDetail,
    AppealInfo,
    SupplierProfile,
    SupplierEmailItem,
    AppealItem,
    DashboardSummary,
)

__version__ = "1.2.1"
__all__ = [
    "LuckMailClient",
    "UserAPI",
    "SupplierAPI",
    "LuckMailError",
    "AuthError",
    "APIError",
    "NetworkError",
    "TimeoutError",
    "UserInfo",
    "EmailItem",
    "ProjectItem",
    "OrderInfo",
    "OrderCode",
    "PurchaseItem",
    "TagItem",
    "TokenCode",
    "TokenAliveResult",
    "TokenMailItem",
    "TokenMailList",
    "TokenMailDetail",
    "AppealInfo",
    "SupplierProfile",
    "SupplierEmailItem",
    "AppealItem",
    "DashboardSummary",
]
