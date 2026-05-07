"""
供应商端 API 接口
Base URL: {base_url}/api/v1/openapi/supplier

所有方法均支持同步/异步双模式，根据调用上下文自动识别。
"""

from typing import Any, Dict, List, Optional

from .http_client import LuckMailHttpClient, _is_async_context
from .models import (
    AppealDetail,
    AppealItem,
    DashboardSummary,
    ImportResult,
    PageResult,
    SupplierEmailItem,
    SupplierProfile,
)

_SUPPLIER_PREFIX = "/api/v1/openapi/supplier"


def _parse_supplier_profile(data: dict) -> SupplierProfile:
    return SupplierProfile(
        id=data.get("id", 0),
        username=data.get("username", ""),
        email=data.get("email", ""),
        balance=data.get("balance", "0.0000"),
        frozen_balance=data.get("frozen_balance", "0.0000"),
        code_commission_rate=data.get("code_commission_rate", "0.0000"),
        buy_commission_rate=data.get("buy_commission_rate", "0.0000"),
        status=data.get("status", 1),
    )


def _parse_supplier_email(data: dict) -> SupplierEmailItem:
    return SupplierEmailItem(
        id=data.get("id", 0),
        address=data.get("address", ""),
        type=data.get("type", ""),
        status=data.get("status", 1),
        domain=data.get("domain", ""),
        total_used=data.get("total_used", 0),
        success_count=data.get("success_count", 0),
        fail_count=data.get("fail_count", 0),
        is_short_term=data.get("is_short_term", 0),
    )


def _parse_appeal_item(data: dict) -> AppealItem:
    return AppealItem(
        id=data.get("id", 0),
        appeal_no=data.get("appeal_no", ""),
        order_no=data.get("order_no", ""),
        reason=data.get("reason", ""),
        status=data.get("status", 1),
        created_at=data.get("created_at", ""),
    )


def _parse_appeal_detail(data: dict) -> AppealDetail:
    return AppealDetail(
        appeal_no=data.get("appeal_no", ""),
        order_no=data.get("order_no", ""),
        reason=data.get("reason", ""),
        status=data.get("status", 1),
        supplier_reply=data.get("supplier_reply"),
        created_at=data.get("created_at"),
    )


def _parse_page_result(data: dict, item_parser=None) -> PageResult:
    items = data.get("list", [])
    if item_parser:
        items = [item_parser(i) for i in items]
    return PageResult(
        list=items,
        total=data.get("total", 0),
        page=data.get("page", 1),
        page_size=data.get("page_size", 20),
    )


class SupplierAPI:
    """
    供应商端 API 接口集合
    
    所有方法智能支持同步/异步调用：
    - 在 async 函数中：await client.supplier.get_profile()
    - 在普通函数中：client.supplier.get_profile()
    
    Args:
        http_client: LuckMailHttpClient 实例
    """
    
    def __init__(self, http_client: LuckMailHttpClient):
        self._client = http_client
    
    def _path(self, path: str) -> str:
        """拼接供应商 API 路径"""
        return f"{_SUPPLIER_PREFIX}{path}"
    
    # ===== 供应商信息 =====
    
    def get_profile(self):
        """
        获取供应商个人信息
        
        Returns:
            SupplierProfile: 供应商信息（余额、佣金率等）
        
        示例::
            profile = client.supplier.get_profile()
            print(profile.username, profile.balance)
        """
        if _is_async_context():
            return self._async_get_profile()
        return self._sync_get_profile()
    
    async def _async_get_profile(self) -> SupplierProfile:
        data = await self._client._async_request("GET", self._path("/profile"))
        return _parse_supplier_profile(data)
    
    def _sync_get_profile(self) -> SupplierProfile:
        data = self._client._sync_request("GET", self._path("/profile"))
        return _parse_supplier_profile(data)
    
    # ===== 邮箱管理 =====
    
    def get_emails(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        email_type: Optional[str] = None,
        is_short_term: Optional[int] = None,
        status: Optional[int] = None,
    ):
        """
        获取邮箱列表（分页）
        
        Args:
            page: 页码，默认 1
            page_size: 每页数量，默认 20
            keyword: 邮箱地址关键词搜索
            email_type: 邮箱类型：ms_graph / ms_imap / google_variant / self_built
            is_short_term: 仅微软邮箱有效：0=长效 1=短效
            status: 状态：1=正常 2=异常 4=禁用
        
        Returns:
            PageResult: 分页结果，list 为 SupplierEmailItem 列表
        
        示例::
            result = client.supplier.get_emails(email_type='ms_graph', is_short_term=0)
            print(f"长效 MS Graph 邮箱: {result.total} 个")
        """
        params = {
            "page": page,
            "page_size": page_size,
            "keyword": keyword,
            "type": email_type,
            "is_short_term": is_short_term,
            "status": status,
        }
        if _is_async_context():
            return self._async_get_emails(params)
        return self._sync_get_emails(params)
    
    async def _async_get_emails(self, params: dict) -> PageResult:
        data = await self._client._async_request("GET", self._path("/emails"), params=params)
        return _parse_page_result(data, _parse_supplier_email)
    
    def _sync_get_emails(self, params: dict) -> PageResult:
        data = self._client._sync_request("GET", self._path("/emails"), params=params)
        return _parse_page_result(data, _parse_supplier_email)
    
    def import_emails(
        self,
        email_type: str,
        emails: List[dict],
        is_short_term: int = 0,
    ):
        """
        批量导入邮箱到供应商资源池
        
        Args:
            email_type: 邮箱类型：microsoft / ms_graph / ms_imap / google_variant / self_built
            emails: 邮箱列表，每项包含 address、password、client_id、refresh_token 等
            is_short_term: 仅微软邮箱有效，0=长效（默认）1=短效
        
        Returns:
            ImportResult: 导入结果
        
        示例::
            result = client.supplier.import_emails(
                email_type='ms_graph',
                is_short_term=0,
                emails=[
                    {
                        'address': 'user1@outlook.com',
                        'client_id': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
                        'refresh_token': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
                    }
                ]
            )
            print(f"成功: {result.success}, 重复: {result.duplicate}")
        """
        body: Dict[str, Any] = {
            "type": email_type,
            "is_short_term": is_short_term,
            "emails": emails,
        }
        if _is_async_context():
            return self._async_import_emails(body)
        return self._sync_import_emails(body)
    
    async def _async_import_emails(self, body: dict) -> ImportResult:
        data = await self._client._async_request(
            "POST", self._path("/emails/import"), json_data=body
        )
        return ImportResult(
            success=data.get("success", 0),
            duplicate=data.get("duplicate", 0),
            failed=data.get("failed", 0),
        )
    
    def _sync_import_emails(self, body: dict) -> ImportResult:
        data = self._client._sync_request(
            "POST", self._path("/emails/import"), json_data=body
        )
        return ImportResult(
            success=data.get("success", 0),
            duplicate=data.get("duplicate", 0),
            failed=data.get("failed", 0),
        )
    
    def export_emails(
        self,
        keyword: Optional[str] = None,
        email_type: Optional[str] = None,
        is_short_term: Optional[int] = None,
        status: Optional[int] = None,
    ):
        """
        导出邮箱（txt 文件流）
        
        Args:
            keyword: 关键词过滤
            email_type: 邮箱类型过滤
            is_short_term: 0=长效 1=短效
            status: 状态过滤
        
        Returns:
            bytes: txt 文件内容
        
        示例::
            content = client.supplier.export_emails(email_type='ms_graph')
            with open("emails.txt", "wb") as f:
                f.write(content)
        """
        params = {
            "keyword": keyword,
            "type": email_type,
            "is_short_term": is_short_term,
            "status": status,
        }
        if _is_async_context():
            return self._client._async_get_stream(self._path("/emails/export"), params=params)
        return self._client._sync_get_stream(self._path("/emails/export"), params=params)
    
    # ===== 申述管理 =====
    
    def get_appeals(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[int] = None,
        appeal_type: Optional[int] = None,
    ):
        """
        获取申述列表（分页）
        
        Args:
            page: 页码
            page_size: 每页数量
            status: 申述状态：1=待处理 2=已同意 3=待仲裁 4=已拒绝
            appeal_type: 申述类型过滤
        
        Returns:
            PageResult: 分页结果，list 为 AppealItem 列表
        
        示例::
            result = client.supplier.get_appeals(status=1)
            print(f"待处理申述: {result.total} 个")
        """
        params = {
            "page": page,
            "page_size": page_size,
            "status": status,
            "type": appeal_type,
        }
        if _is_async_context():
            return self._async_get_appeals(params)
        return self._sync_get_appeals(params)
    
    async def _async_get_appeals(self, params: dict) -> PageResult:
        data = await self._client._async_request("GET", self._path("/appeals"), params=params)
        return _parse_page_result(data, _parse_appeal_item)
    
    def _sync_get_appeals(self, params: dict) -> PageResult:
        data = self._client._sync_request("GET", self._path("/appeals"), params=params)
        return _parse_page_result(data, _parse_appeal_item)
    
    def get_appeal(self, appeal_no: str):
        """
        获取申述详情
        
        Args:
            appeal_no: 申述单号
        
        Returns:
            AppealDetail: 申述详情
        
        示例::
            detail = client.supplier.get_appeal("APL20240310001")
            print(detail.reason, detail.status)
        """
        if _is_async_context():
            return self._async_get_appeal(appeal_no)
        return self._sync_get_appeal(appeal_no)
    
    async def _async_get_appeal(self, appeal_no: str) -> AppealDetail:
        data = await self._client._async_request(
            "GET", self._path(f"/appeal/{appeal_no}")
        )
        return _parse_appeal_detail(data)
    
    def _sync_get_appeal(self, appeal_no: str) -> AppealDetail:
        data = self._client._sync_request(
            "GET", self._path(f"/appeal/{appeal_no}")
        )
        return _parse_appeal_detail(data)
    
    def reply_appeal(self, appeal_no: str, result: int, reply: str):
        """
        处理申述（回复）
        
        Args:
            appeal_no: 申述单号
            result: 处理结果：1=同意退款 2=拒绝申述 3=申请仲裁
            reply: 回复内容说明
        
        Returns:
            None
        
        示例::
            # 同意退款
            client.supplier.reply_appeal("APL20240310001", result=1, reply="邮箱确有问题，同意退款")
            
            # 拒绝申述
            client.supplier.reply_appeal("APL20240310001", result=2, reply="邮箱状态正常，拒绝申述")
        """
        body = {"result": result, "reply": reply}
        if _is_async_context():
            return self._async_reply_appeal(appeal_no, body)
        return self._sync_reply_appeal(appeal_no, body)
    
    async def _async_reply_appeal(self, appeal_no: str, body: dict) -> None:
        await self._client._async_request(
            "POST", self._path(f"/appeal/{appeal_no}/reply"), json_data=body
        )
    
    def _sync_reply_appeal(self, appeal_no: str, body: dict) -> None:
        self._client._sync_request(
            "POST", self._path(f"/appeal/{appeal_no}/reply"), json_data=body
        )
    
    def batch_reply_appeals(
        self,
        appeal_nos: List[str],
        result: int,
        reply: str,
    ):
        """
        批量处理申述
        
        Args:
            appeal_nos: 申述单号列表（最多 100 条）
            result: 处理结果：1=同意退款 2=拒绝申述 3=申请仲裁
            reply: 回复内容说明
        
        Returns:
            dict: 包含 success 和 failed 数量
        
        示例::
            result = client.supplier.batch_reply_appeals(
                appeal_nos=["APL001", "APL002", "APL003"],
                result=2,
                reply="经验证邮箱正常，拒绝申述"
            )
            print(f"成功处理: {result['success']}")
        """
        body = {
            "appeal_nos": appeal_nos,
            "result": result,
            "reply": reply,
        }
        if _is_async_context():
            return self._async_batch_reply_appeals(body)
        return self._sync_batch_reply_appeals(body)
    
    async def _async_batch_reply_appeals(self, body: dict) -> dict:
        return await self._client._async_request(
            "POST", self._path("/appeals/batch-reply"), json_data=body
        )
    
    def _sync_batch_reply_appeals(self, body: dict) -> dict:
        return self._client._sync_request(
            "POST", self._path("/appeals/batch-reply"), json_data=body
        )
    
    # ===== 数据看板 =====
    
    def get_dashboard(self):
        """
        获取数据看板总览
        
        Returns:
            DashboardSummary: 看板数据，包含邮箱总量、接码统计、佣金数据等
        
        示例::
            summary = client.supplier.get_dashboard()
            print(f"总邮箱: {summary.total_emails}")
            print(f"今日佣金: {summary.today_commission}")
            print(f"成功率: {summary.success_rate}%")
        """
        if _is_async_context():
            return self._async_get_dashboard()
        return self._sync_get_dashboard()
    
    async def _async_get_dashboard(self) -> DashboardSummary:
        data = await self._client._async_request("GET", self._path("/dashboard/summary"))
        return self._build_dashboard(data)
    
    def _sync_get_dashboard(self) -> DashboardSummary:
        data = self._client._sync_request("GET", self._path("/dashboard/summary"))
        return self._build_dashboard(data)
    
    def _build_dashboard(self, data: dict) -> DashboardSummary:
        return DashboardSummary(
            total_emails=data.get("total_emails", 0),
            active_emails=data.get("active_emails", 0),
            total_assigned=data.get("total_assigned", 0),
            total_success=data.get("total_success", 0),
            success_rate=data.get("success_rate", 0.0),
            total_commission=data.get("total_commission", "0.0000"),
            available_balance=data.get("available_balance", "0.0000"),
            today_assigned=data.get("today_assigned", 0),
            today_success=data.get("today_success", 0),
            today_commission=data.get("today_commission", "0.0000"),
            email_category=data.get("email_category", {}),
        )
