"""
用户端 API 接口
Base URL: {base_url}/api/v1/openapi

所有方法均支持同步/异步双模式，根据调用上下文自动识别：
- 在 async 函数中 await 调用：异步模式
- 在普通函数中直接调用：同步模式
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Union

from .http_client import LuckMailHttpClient, _is_async_context
from .models import (
    AppealInfo,
    EmailItem,
    ImportResult,
    OrderCode,
    OrderInfo,
    PageResult,
    ProjectItem,
    ProjectPrice,
    PurchaseItem,
    TagItem,
    TokenCode,
    TokenAliveResult,
    TokenMailDetail,
    TokenMailItem,
    TokenMailList,
    UserInfo,
)


def _parse_page_result(data: dict, item_parser=None) -> PageResult:
    """解析分页结果"""
    items = data.get("list", [])
    if item_parser:
        items = [item_parser(i) for i in items]
    return PageResult(
        list=items,
        total=data.get("total", 0),
        page=data.get("page", 1),
        page_size=data.get("page_size", 20),
    )


def _parse_user_info(data: dict) -> UserInfo:
    return UserInfo(
        id=data.get("id", 0),
        username=data.get("username", ""),
        email=data.get("email", ""),
        balance=data.get("balance", "0.0000"),
        status=data.get("status", 1),
        api_email_enabled=data.get("api_email_enabled", 0),
        api_email_price=data.get("api_email_price", "0.0000"),
    )


def _parse_email_item(data: dict) -> EmailItem:
    return EmailItem(
        id=data.get("id", 0),
        address=data.get("address", ""),
        type=data.get("type", ""),
        status=data.get("status", 1),
        domain=data.get("domain", ""),
        total_used=data.get("total_used", 0),
        success_count=data.get("success_count", 0),
        fail_count=data.get("fail_count", 0),
    )


def _parse_project_item(data: dict) -> ProjectItem:
    prices = [
        ProjectPrice(
            email_type=p.get("email_type", ""),
            code_price=p.get("code_price", "0.0000"),
            buy_price=p.get("buy_price", "0.0000"),
        )
        for p in data.get("prices", [])
    ]
    return ProjectItem(
        id=data.get("id", 0),
        name=data.get("name", ""),
        code=data.get("code", ""),
        email_types=data.get("email_types", []),
        timeout_seconds=data.get("timeout_seconds", 300),
        warranty_hours=data.get("warranty_hours", 0),
        daily_limit=data.get("daily_limit", 0),
        description=data.get("description", ""),
        prices=prices,
    )


def _parse_order_info(data: dict) -> OrderInfo:
    return OrderInfo(
        order_no=data.get("order_no", ""),
        email_address=data.get("email_address", ""),
        project=data.get("project", ""),
        price=data.get("price", "0.0000"),
        timeout_seconds=data.get("timeout_seconds", 300),
        expired_at=data.get("expired_at", ""),
    )


def _parse_order_code(data: dict) -> OrderCode:
    return OrderCode(
        order_no=data.get("order_no", ""),
        status=data.get("status", "pending"),
        verification_code=data.get("verification_code"),
        mail_from=data.get("mail_from"),
        mail_subject=data.get("mail_subject"),
        mail_body_html=data.get("mail_body_html"),
    )


def _parse_purchase_item(data: dict) -> PurchaseItem:
    return PurchaseItem(
        id=data.get("id", 0),
        email_address=data.get("email_address", ""),
        token=data.get("token", ""),
        project_name=data.get("project_name", ""),
        price=data.get("price", "0.0000"),
        status=data.get("status", 1),
        tag_id=data.get("tag_id", 0),
        tag_name=data.get("tag_name", ""),
        user_disabled=data.get("user_disabled", 0),
        warranty_hours=data.get("warranty_hours", 0),
        warranty_until=data.get("warranty_until"),
        created_at=data.get("created_at"),
    )


def _parse_tag_item(data: dict) -> TagItem:
    return TagItem(
        id=data.get("id", 0),
        name=data.get("name", ""),
        remark=data.get("remark", ""),
        limit_type=data.get("limit_type", 0),
        purchase_count=data.get("purchase_count", 0),
        created_at=data.get("created_at"),
    )


def _parse_token_code(data: dict) -> TokenCode:
    return TokenCode(
        email_address=data.get("email_address", ""),
        project=data.get("project", ""),
        has_new_mail=data.get("has_new_mail", False),
        verification_code=data.get("verification_code"),
        mail=data.get("mail"),
    )


def _parse_token_alive_result(data: dict) -> TokenAliveResult:
    return TokenAliveResult(
        email_address=data.get("email_address", ""),
        project=data.get("project", ""),
        alive=data.get("alive", False),
        status=data.get("status", "failed"),
        message=data.get("message", ""),
        mail_count=data.get("mail_count", 0),
    )


def _parse_token_mail_item(data: dict) -> TokenMailItem:
    return TokenMailItem(
        message_id=data.get("message_id", ""),
        from_addr=data.get("from", ""),
        subject=data.get("subject", ""),
        body=data.get("body", ""),
        html_body=data.get("html_body", ""),
        received_at=data.get("received_at", ""),
    )


def _parse_token_mail_list(data: dict) -> TokenMailList:
    mails_raw = data.get("mails", [])
    mails = [_parse_token_mail_item(m) for m in mails_raw] if mails_raw else []
    return TokenMailList(
        email_address=data.get("email_address", ""),
        project=data.get("project", ""),
        warranty_until=data.get("warranty_until", ""),
        mails=mails,
    )


def _parse_token_mail_detail(data: dict) -> TokenMailDetail:
    return TokenMailDetail(
        message_id=data.get("message_id", ""),
        from_addr=data.get("from", ""),
        to=data.get("to", ""),
        subject=data.get("subject", ""),
        body_text=data.get("body_text", ""),
        body_html=data.get("body_html", ""),
        received_at=data.get("received_at", ""),
        verification_code=data.get("verification_code", ""),
    )


class UserAPI:
    """
    用户端 API 接口集合
    
    所有方法智能支持同步/异步调用：
    - 在 async 函数中：await client.user.get_user_info()
    - 在普通函数中：client.user.get_user_info()
    
    Args:
        http_client: LuckMailHttpClient 实例
    """
    
    def __init__(self, http_client: LuckMailHttpClient):
        self._client = http_client
    
    # ===== 用户信息 =====
    
    def get_user_info(self):
        """
        获取用户信息及余额
        
        Returns:
            UserInfo: 用户信息对象
        
        同步调用::
            info = client.user.get_user_info()
            print(info.username, info.balance)
        
        异步调用::
            info = await client.user.get_user_info()
            print(info.username, info.balance)
        """
        if _is_async_context():
            return self._async_get_user_info()
        return self._sync_get_user_info()
    
    async def _async_get_user_info(self) -> UserInfo:
        data = await self._client._async_request("GET", "/api/v1/openapi/user/info")
        return _parse_user_info(data)
    
    def _sync_get_user_info(self) -> UserInfo:
        data = self._client._sync_request("GET", "/api/v1/openapi/user/info")
        return _parse_user_info(data)
    
    def get_balance(self):
        """
        查询余额
        
        Returns:
            str: 余额字符串，如 "150.0000"
        
        示例::
            balance = client.user.get_balance()
            print(f"余额: {balance}")
        """
        if _is_async_context():
            return self._async_get_balance()
        return self._sync_get_balance()
    
    async def _async_get_balance(self) -> str:
        data = await self._client._async_request("GET", "/api/v1/openapi/balance")
        return data.get("balance", "0.0000")
    
    def _sync_get_balance(self) -> str:
        data = self._client._sync_request("GET", "/api/v1/openapi/balance")
        return data.get("balance", "0.0000")
    
    # ===== 邮箱类型 =====
    
    def get_email_types(self):
        """
        获取支持的邮箱类型列表
        
        Returns:
            List[dict]: 邮箱类型列表，每项含 type、name、description
        
        示例::
            types = client.user.get_email_types()
            for t in types:
                print(t['type'], t['name'])
        """
        if _is_async_context():
            return self._async_get_email_types()
        return self._sync_get_email_types()
    
    async def _async_get_email_types(self) -> List[dict]:
        return await self._client._async_request("GET", "/api/v1/openapi/email-types")
    
    def _sync_get_email_types(self) -> List[dict]:
        return self._client._sync_request("GET", "/api/v1/openapi/email-types")
    
    # ===== 我的邮箱管理 =====
    
    def get_emails(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        status: Optional[int] = None,
    ):
        """
        获取我的邮箱列表（分页）
        
        Args:
            page: 页码，默认 1
            page_size: 每页数量，默认 20
            keyword: 邮箱地址关键词搜索
            status: 状态过滤：1=正常 2=异常 4=禁用
        
        Returns:
            PageResult: 分页结果，list 为 EmailItem 列表
        
        示例::
            result = client.user.get_emails(page=1, keyword="outlook")
            for email in result.list:
                print(email.address, email.status)
        """
        params = {
            "page": page,
            "page_size": page_size,
            "keyword": keyword,
            "status": status,
        }
        if _is_async_context():
            return self._async_get_emails(params)
        return self._sync_get_emails(params)
    
    async def _async_get_emails(self, params: dict) -> PageResult:
        data = await self._client._async_request("GET", "/api/v1/openapi/emails", params=params)
        return _parse_page_result(data, _parse_email_item)
    
    def _sync_get_emails(self, params: dict) -> PageResult:
        data = self._client._sync_request("GET", "/api/v1/openapi/emails", params=params)
        return _parse_page_result(data, _parse_email_item)
    
    def import_emails(self, email_type: str, emails: List[dict]):
        """
        导入邮箱到私有邮箱池
        
        Args:
            email_type: 邮箱类型，如 'ms_graph', 'ms_imap', 'google_variant', 'self_built'
            emails: 邮箱列表，每项为 dict，包含 address、password、client_id、refresh_token 等
        
        Returns:
            ImportResult: 导入结果（success/duplicate/failed 数量）
        
        示例::
            result = client.user.import_emails(
                email_type='ms_graph',
                emails=[
                    {
                        'address': 'user@outlook.com',
                        'password': 'pass123',
                        'client_id': 'xxx-xxx-xxx',
                        'refresh_token': 'xxxxxxxxxxxxxxxx'
                    }
                ]
            )
            print(f"成功: {result.success}, 重复: {result.duplicate}, 失败: {result.failed}")
        """
        body = {"type": email_type, "emails": emails}
        if _is_async_context():
            return self._async_import_emails(body)
        return self._sync_import_emails(body)
    
    async def _async_import_emails(self, body: dict) -> ImportResult:
        data = await self._client._async_request("POST", "/api/v1/openapi/emails/import", json_data=body)
        return ImportResult(
            success=data.get("success", 0),
            duplicate=data.get("duplicate", 0),
            failed=data.get("failed", 0),
        )
    
    def _sync_import_emails(self, body: dict) -> ImportResult:
        data = self._client._sync_request("POST", "/api/v1/openapi/emails/import", json_data=body)
        return ImportResult(
            success=data.get("success", 0),
            duplicate=data.get("duplicate", 0),
            failed=data.get("failed", 0),
        )
    
    def export_emails(
        self,
        keyword: Optional[str] = None,
        status: Optional[int] = None,
    ):
        """
        导出邮箱（txt 文件流）
        
        Args:
            keyword: 关键词过滤
            status: 状态过滤：1=正常 2=异常 4=禁用
        
        Returns:
            bytes: txt 文件内容，每行格式：address----password 或 address----client_id----refresh_token
        
        示例::
            content = client.user.export_emails(keyword="outlook")
            with open("emails.txt", "wb") as f:
                f.write(content)
        """
        params = {"keyword": keyword, "status": status}
        if _is_async_context():
            return self._client._async_get_stream("/api/v1/openapi/emails/export", params=params)
        return self._client._sync_get_stream("/api/v1/openapi/emails/export", params=params)
    
    # ===== 项目列表 =====
    
    def get_projects(self, page: int = 1, page_size: int = 50):
        """
        获取项目列表
        
        Args:
            page: 页码，默认 1
            page_size: 每页数量，默认 50，最大 500
        
        Returns:
            PageResult: 分页结果，list 为 ProjectItem 列表
        
        示例::
            result = client.user.get_projects()
            for p in result.list:
                print(p.name, p.code)
        """
        params = {"page": page, "page_size": page_size}
        if _is_async_context():
            return self._async_get_projects(params)
        return self._sync_get_projects(params)
    
    async def _async_get_projects(self, params: dict) -> PageResult:
        data = await self._client._async_request("GET", "/api/v1/openapi/projects", params=params)
        return _parse_page_result(data, _parse_project_item)
    
    def _sync_get_projects(self, params: dict) -> PageResult:
        data = self._client._sync_request("GET", "/api/v1/openapi/projects", params=params)
        return _parse_page_result(data, _parse_project_item)
    
    # ===== 接码订单 =====
    
    def create_order(
        self,
        project_code: str,
        email_type: Optional[str] = None,
        domain: Optional[str] = None,
        specified_email: Optional[str] = None,
        variant_mode: Optional[str] = None,
    ):
        """
        创建接码订单
        
        Args:
            project_code: 项目编码，如 'twitter', 'facebook'
            email_type: 邮箱类型（可选）：ms_graph / ms_imap / self_built / google_variant
            domain: 指定域名（可选），如 'outlook.com'
            specified_email: 指定邮箱地址（可选）
            variant_mode: 谷歌变种模式（可选，仅 email_type=google_variant 时有效）: dot=点号变种 / plus=+号变种 / mixed=混合变种 / all=随机选择
        
        Returns:
            OrderInfo: 订单信息，包含 order_no 和分配的 email_address
        
        示例::
            order = client.user.create_order('twitter', email_type='ms_graph')
            print(f"订单号: {order.order_no}")
            print(f"邮箱: {order.email_address}")
        """
        body: Dict[str, Any] = {"project_code": project_code}
        if email_type:
            body["email_type"] = email_type
        if domain:
            body["domain"] = domain
        if specified_email:
            body["specified_email"] = specified_email
        if variant_mode:
            body["variant_mode"] = variant_mode
        
        if _is_async_context():
            return self._async_create_order(body)
        return self._sync_create_order(body)
    
    async def _async_create_order(self, body: dict) -> OrderInfo:
        data = await self._client._async_request("POST", "/api/v1/openapi/order/create", json_data=body)
        return _parse_order_info(data)
    
    def _sync_create_order(self, body: dict) -> OrderInfo:
        data = self._client._sync_request("POST", "/api/v1/openapi/order/create", json_data=body)
        return _parse_order_info(data)
    
    def get_order_code(self, order_no: str):
        """
        查询验证码（单次查询）
        
        Args:
            order_no: 订单编号
        
        Returns:
            OrderCode: 验证码结果，status 为 'success' 时包含 verification_code
        
        示例::
            code = client.user.get_order_code(order.order_no)
            if code.status == 'success':
                print(f"验证码: {code.verification_code}")
        """
        if _is_async_context():
            return self._async_get_order_code(order_no)
        return self._sync_get_order_code(order_no)
    
    async def _async_get_order_code(self, order_no: str) -> OrderCode:
        data = await self._client._async_request(
            "GET", f"/api/v1/openapi/order/{order_no}/code"
        )
        return _parse_order_code(data)
    
    def _sync_get_order_code(self, order_no: str) -> OrderCode:
        data = self._client._sync_request(
            "GET", f"/api/v1/openapi/order/{order_no}/code"
        )
        return _parse_order_code(data)
    
    def cancel_order(self, order_no: str):
        """
        取消订单
        
        Args:
            order_no: 订单编号
        
        Returns:
            None
        
        示例::
            client.user.cancel_order(order.order_no)
        """
        if _is_async_context():
            return self._async_cancel_order(order_no)
        return self._sync_cancel_order(order_no)
    
    async def _async_cancel_order(self, order_no: str) -> None:
        await self._client._async_request(
            "POST", f"/api/v1/openapi/order/{order_no}/cancel"
        )
    
    def _sync_cancel_order(self, order_no: str) -> None:
        self._client._sync_request(
            "POST", f"/api/v1/openapi/order/{order_no}/cancel"
        )
    
    def get_orders(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[int] = None,
        project_id: Optional[int] = None,
    ):
        """
        获取订单列表（分页）
        
        Args:
            page: 页码
            page_size: 每页数量
            status: 状态过滤：1=待接码 2=已完成 3=已超时 4=已取消 5=已退款
            project_id: 按项目 ID 筛选
        
        Returns:
            PageResult: 分页结果，list 为订单 dict 列表
        
        示例::
            result = client.user.get_orders(status=2)
            print(f"共 {result.total} 条已完成订单")
        """
        params = {
            "page": page,
            "page_size": page_size,
            "status": status,
            "project_id": project_id,
        }
        if _is_async_context():
            return self._async_get_orders(params)
        return self._sync_get_orders(params)
    
    async def _async_get_orders(self, params: dict) -> PageResult:
        data = await self._client._async_request("GET", "/api/v1/openapi/orders", params=params)
        return _parse_page_result(data)
    
    def _sync_get_orders(self, params: dict) -> PageResult:
        data = self._client._sync_request("GET", "/api/v1/openapi/orders", params=params)
        return _parse_page_result(data)
    
    # ===== 接码轮询（高级方法）=====
    
    def wait_for_code(
        self,
        order_no: str,
        timeout: int = 300,
        interval: float = 3.0,
        on_poll: Optional[callable] = None,
    ):
        """
        等待接码（带自动轮询），智能识别同步/异步上下文
        
        会自动每隔 interval 秒查询一次，直到收到验证码或超时。
        
        Args:
            order_no: 订单编号
            timeout: 最大等待时间（秒），默认 300
            interval: 轮询间隔（秒），默认 3.0
            on_poll: 每次轮询时的回调函数，接收 OrderCode 参数（可选）
        
        Returns:
            OrderCode: 最终结果，status 为 'success' 或 'timeout'/'cancelled'
        
        同步调用示例::
            order = client.user.create_order('twitter')
            result = client.user.wait_for_code(order.order_no, timeout=300)
            if result.status == 'success':
                print(f"✅ 验证码: {result.verification_code}")
            else:
                print(f"❌ 接码失败: {result.status}")
        
        异步调用示例::
            order = await client.user.create_order('twitter')
            result = await client.user.wait_for_code(order.order_no, timeout=300)
            if result.status == 'success':
                print(f"✅ 验证码: {result.verification_code}")
        """
        if _is_async_context():
            return self._async_wait_for_code(order_no, timeout, interval, on_poll)
        return self._sync_wait_for_code(order_no, timeout, interval, on_poll)
    
    async def _async_wait_for_code(
        self,
        order_no: str,
        timeout: int,
        interval: float,
        on_poll: Optional[callable],
    ) -> OrderCode:
        """异步轮询等待验证码"""
        start = time.time()
        while True:
            result = await self._async_get_order_code(order_no)
            
            if on_poll:
                if asyncio.iscoroutinefunction(on_poll):
                    await on_poll(result)
                else:
                    on_poll(result)
            
            if result.status in ("success", "timeout", "cancelled"):
                return result
            
            elapsed = time.time() - start
            if elapsed >= timeout:
                return result
            
            await asyncio.sleep(interval)
    
    def _sync_wait_for_code(
        self,
        order_no: str,
        timeout: int,
        interval: float,
        on_poll: Optional[callable],
    ) -> OrderCode:
        """同步轮询等待验证码"""
        start = time.time()
        while True:
            result = self._sync_get_order_code(order_no)
            
            if on_poll:
                on_poll(result)
            
            if result.status in ("success", "timeout", "cancelled"):
                return result
            
            elapsed = time.time() - start
            if elapsed >= timeout:
                return result
            
            time.sleep(interval)
    
    # ===== 购买邮箱 =====
    
    def purchase_emails(
        self,
        project_code: str,
        quantity: int,
        email_type: Optional[str] = None,
        domain: Optional[str] = None,
        variant_mode: Optional[str] = None,
    ):
        """
        购买邮箱
        
        Args:
            project_code: 项目编码
            quantity: 购买数量（1-10000）
            email_type: 邮箱类型（可选）
            domain: 指定域名（可选）
            variant_mode: 谷歌变种模式（可选，仅 email_type=google_variant 时有效）: dot=点号变种 / plus=+号变种 / mixed=混合变种 / all=随机选择
        
        Returns:
            dict: 购买结果，包含 purchases 列表、total_cost、balance_after
        
        示例::
            result = client.user.purchase_emails('twitter', quantity=5, email_type='ms_graph')
            for item in result['purchases']:
                print(item['email_address'], item['token'])
        """
        body: Dict[str, Any] = {
            "project_code": project_code,
            "quantity": quantity,
        }
        if email_type:
            body["email_type"] = email_type
        if domain:
            body["domain"] = domain
        if variant_mode:
            body["variant_mode"] = variant_mode
        
        if _is_async_context():
            return self._async_purchase_emails(body)
        return self._sync_purchase_emails(body)
    
    async def _async_purchase_emails(self, body: dict) -> dict:
        return await self._client._async_request("POST", "/api/v1/openapi/email/purchase", json_data=body)
    
    def _sync_purchase_emails(self, body: dict) -> dict:
        return self._client._sync_request("POST", "/api/v1/openapi/email/purchase", json_data=body)
    
    def get_purchases(
        self,
        page: int = 1,
        page_size: int = 20,
        project_id: Optional[int] = None,
        tag_id: Optional[int] = None,
        keyword: Optional[str] = None,
        user_disabled: Optional[int] = None,
    ):
        """
        获取已购邮箱列表
        
        Args:
            page: 页码
            page_size: 每页数量
            project_id: 按项目 ID 筛选
            tag_id: 按标签 ID 筛选
            keyword: 邮箱地址关键词搜索
            user_disabled: 禁用状态：0=正常 1=已禁用
        
        Returns:
            PageResult: 分页结果，list 为 PurchaseItem 列表
        
        示例::
            result = client.user.get_purchases(tag_id=1, keyword="outlook")
            for item in result.list:
                print(item.email_address, item.token, item.tag_name)
        """
        params = {
            "page": page,
            "page_size": page_size,
            "project_id": project_id,
            "tag_id": tag_id,
            "keyword": keyword,
            "user_disabled": user_disabled,
        }
        if _is_async_context():
            return self._async_get_purchases(params)
        return self._sync_get_purchases(params)
    
    async def _async_get_purchases(self, params: dict) -> PageResult:
        data = await self._client._async_request("GET", "/api/v1/openapi/email/purchases", params=params)
        return _parse_page_result(data, _parse_purchase_item)
    
    def _sync_get_purchases(self, params: dict) -> PageResult:
        data = self._client._sync_request("GET", "/api/v1/openapi/email/purchases", params=params)
        return _parse_page_result(data, _parse_purchase_item)
    
    def get_token_code(self, token: str):
        """
        通过 Token 获取最新验证码（已购邮箱）
        
        Args:
            token: 已购邮箱的 token
        
        Returns:
            TokenCode: 验证码结果
        
        示例::
            result = client.user.get_token_code("tok_abc123def456")
            if result.has_new_mail:
                print(f"验证码: {result.verification_code}")
        """
        if _is_async_context():
            return self._async_get_token_code(token)
        return self._sync_get_token_code(token)
    
    async def _async_get_token_code(self, token: str) -> TokenCode:
        data = await self._client._async_request(
            "GET", f"/api/v1/openapi/email/token/{token}/code"
        )
        return _parse_token_code(data)
    
    def _sync_get_token_code(self, token: str) -> TokenCode:
        data = self._client._sync_request(
            "GET", f"/api/v1/openapi/email/token/{token}/code"
        )
        return _parse_token_code(data)

    def check_token_alive(self, token: str):
        """
        通过 Token 测试已购邮箱是否可以正常获取邮件列表

        Args:
            token: 已购邮箱 token

        Returns:
            TokenAliveResult: 测活结果

        示例::
            result = client.user.check_token_alive("tok_abc123def456")
            print(result.alive, result.message)
        """
        if _is_async_context():
            return self._async_check_token_alive(token)
        return self._sync_check_token_alive(token)

    async def _async_check_token_alive(self, token: str) -> TokenAliveResult:
        data = await self._client._async_request(
            "GET", f"/api/v1/openapi/email/token/{token}/alive"
        )
        return _parse_token_alive_result(data)

    def _sync_check_token_alive(self, token: str) -> TokenAliveResult:
        data = self._client._sync_request(
            "GET", f"/api/v1/openapi/email/token/{token}/alive"
        )
        return _parse_token_alive_result(data)
    
    def wait_for_token_code(
        self,
        token: str,
        timeout: int = 300,
        interval: float = 3.0,
        on_poll: Optional[callable] = None,
    ):
        """
        等待 Token 邮箱的验证码（带自动轮询），智能识别同步/异步上下文
        
        Args:
            token: 已购邮箱 token
            timeout: 最大等待时间（秒）
            interval: 轮询间隔（秒）
            on_poll: 每次轮询的回调
        
        Returns:
            TokenCode: 最终结果
        
        示例::
            result = client.user.wait_for_token_code("tok_abc123", timeout=120)
            if result.has_new_mail:
                print(f"✅ 验证码: {result.verification_code}")
        """
        if _is_async_context():
            return self._async_wait_for_token_code(token, timeout, interval, on_poll)
        return self._sync_wait_for_token_code(token, timeout, interval, on_poll)
    
    async def _async_wait_for_token_code(
        self, token: str, timeout: int, interval: float, on_poll
    ) -> TokenCode:
        start = time.time()
        while True:
            result = await self._async_get_token_code(token)
            
            if on_poll:
                if asyncio.iscoroutinefunction(on_poll):
                    await on_poll(result)
                else:
                    on_poll(result)
            
            if result.has_new_mail:
                return result
            
            if time.time() - start >= timeout:
                return result
            
            await asyncio.sleep(interval)
    
    def _sync_wait_for_token_code(
        self, token: str, timeout: int, interval: float, on_poll
    ) -> TokenCode:
        start = time.time()
        while True:
            result = self._sync_get_token_code(token)
            
            if on_poll:
                on_poll(result)
            
            if result.has_new_mail:
                return result
            
            if time.time() - start >= timeout:
                return result
            
            time.sleep(interval)
    
    # ===== 已购邮箱邮件列表和详情 =====
    
    def get_token_mails(self, token: str):
        """
        通过 Token 获取已购邮箱的邮件列表
        
        Args:
            token: 已购邮箱的 token
        
        Returns:
            TokenMailList: 邮件列表结果，包含 email_address、project、warranty_until、mails
        
        示例::
            result = client.user.get_token_mails("tok_abc123def456")
            print(f"邮箱: {result.email_address}, 项目: {result.project}")
            for mail in result.mails:
                print(f"  [{mail.received_at}] {mail.from_addr}: {mail.subject}")
        """
        if _is_async_context():
            return self._async_get_token_mails(token)
        return self._sync_get_token_mails(token)
    
    async def _async_get_token_mails(self, token: str) -> TokenMailList:
        data = await self._client._async_request(
            "GET", f"/api/v1/openapi/email/token/{token}/mails"
        )
        return _parse_token_mail_list(data)
    
    def _sync_get_token_mails(self, token: str) -> TokenMailList:
        data = self._client._sync_request(
            "GET", f"/api/v1/openapi/email/token/{token}/mails"
        )
        return _parse_token_mail_list(data)
    
    def get_token_mail_detail(self, token: str, message_id: str):
        """
        通过 Token 获取已购邮箱的邮件详情
        
        Args:
            token: 已购邮箱的 token
            message_id: 邮件 ID（从 get_token_mails 返回的列表中获取）
        
        Returns:
            TokenMailDetail: 邮件详情，包含 message_id、from_addr、to、subject、body_text、body_html、verification_code
        
        示例::
            detail = client.user.get_token_mail_detail("tok_abc123", "AAMkAGI2...")
            print(f"主题: {detail.subject}")
            print(f"正文: {detail.body_text}")
            if detail.verification_code:
                print(f"验证码: {detail.verification_code}")
        """
        if _is_async_context():
            return self._async_get_token_mail_detail(token, message_id)
        return self._sync_get_token_mail_detail(token, message_id)
    
    async def _async_get_token_mail_detail(self, token: str, message_id: str) -> TokenMailDetail:
        data = await self._client._async_request(
            "GET", f"/api/v1/openapi/email/token/{token}/mails/{message_id}"
        )
        return _parse_token_mail_detail(data)
    
    def _sync_get_token_mail_detail(self, token: str, message_id: str) -> TokenMailDetail:
        data = self._client._sync_request(
            "GET", f"/api/v1/openapi/email/token/{token}/mails/{message_id}"
        )
        return _parse_token_mail_detail(data)
    
    # ===== 申述 =====
    
    def create_appeal(
        self,
        appeal_type: int,
        reason: str,
        description: str,
        order_id: Optional[int] = None,
        purchase_id: Optional[int] = None,
        evidence_urls: Optional[List[str]] = None,
    ):
        """
        提交申述
        
        Args:
            appeal_type: 申述类型：1=接码订单 2=购买邮箱
            reason: 申述原因，如 'no_code', 'wrong_code', 'email_invalid'
            description: 详细描述
            order_id: 接码订单 ID（appeal_type=1 时必填）
            purchase_id: 购买记录 ID（appeal_type=2 时必填）
            evidence_urls: 证据截图 URL 列表（可选）
        
        Returns:
            dict: 包含 appeal_no 的字典
        
        示例::
            result = client.user.create_appeal(
                appeal_type=1,
                order_id=123,
                reason='no_code',
                description='等待 5 分钟未收到验证码'
            )
            print(f"申述单号: {result['appeal_no']}")
        """
        body: Dict[str, Any] = {
            "appeal_type": appeal_type,
            "reason": reason,
            "description": description,
        }
        if order_id is not None:
            body["order_id"] = order_id
        if purchase_id is not None:
            body["purchase_id"] = purchase_id
        if evidence_urls:
            body["evidence_urls"] = evidence_urls
        
        if _is_async_context():
            return self._async_create_appeal(body)
        return self._sync_create_appeal(body)
    
    async def _async_create_appeal(self, body: dict) -> dict:
        return await self._client._async_request(
            "POST", "/api/v1/openapi/appeal/create", json_data=body
        )
    
    def _sync_create_appeal(self, body: dict) -> dict:
        return self._client._sync_request(
            "POST", "/api/v1/openapi/appeal/create", json_data=body
        )

    # ===== 已购邮箱禁用管理 =====

    def set_purchase_disabled(self, purchase_id: int, disabled: int):
        """
        设置已购邮箱禁用状态

        Args:
            purchase_id: 已购邮箱 ID
            disabled: 禁用状态：0=启用 1=禁用

        Returns:
            None

        示例::
            client.user.set_purchase_disabled(1, 1)  # 禁用
            client.user.set_purchase_disabled(1, 0)  # 启用
        """
        body = {"disabled": disabled}
        if _is_async_context():
            return self._async_set_purchase_disabled(purchase_id, body)
        return self._sync_set_purchase_disabled(purchase_id, body)

    async def _async_set_purchase_disabled(self, purchase_id: int, body: dict) -> None:
        await self._client._async_request(
            "PUT", f"/api/v1/openapi/email/purchases/{purchase_id}/disabled", json_data=body
        )

    def _sync_set_purchase_disabled(self, purchase_id: int, body: dict) -> None:
        self._client._sync_request(
            "PUT", f"/api/v1/openapi/email/purchases/{purchase_id}/disabled", json_data=body
        )

    def batch_set_purchase_disabled(self, ids: List[int], disabled: int):
        """
        批量设置已购邮箱禁用状态

        Args:
            ids: 已购邮箱 ID 列表
            disabled: 禁用状态：0=启用 1=禁用

        Returns:
            None

        示例::
            client.user.batch_set_purchase_disabled([1, 2, 3], 1)  # 批量禁用
        """
        body = {"ids": ids, "disabled": disabled}
        if _is_async_context():
            return self._async_batch_set_purchase_disabled(body)
        return self._sync_batch_set_purchase_disabled(body)

    async def _async_batch_set_purchase_disabled(self, body: dict) -> None:
        await self._client._async_request(
            "POST", "/api/v1/openapi/email/purchases/batch-disabled", json_data=body
        )

    def _sync_batch_set_purchase_disabled(self, body: dict) -> None:
        self._client._sync_request(
            "POST", "/api/v1/openapi/email/purchases/batch-disabled", json_data=body
        )

    # ===== 已购邮箱标签管理 =====

    def set_purchase_tag(
        self,
        purchase_id: int,
        tag_id: Optional[int] = None,
        tag_name: Optional[str] = None,
    ):
        """
        设置已购邮箱标签

        Args:
            purchase_id: 已购邮箱 ID
            tag_id: 标签 ID（与 tag_name 二选一，传 0 表示移除标签）
            tag_name: 标签名称（与 tag_id 二选一）

        Returns:
            None

        示例::
            client.user.set_purchase_tag(1, tag_id=1)
            client.user.set_purchase_tag(1, tag_name="主力号")
            client.user.set_purchase_tag(1, tag_id=0)  # 移除标签
        """
        body: Dict[str, Any] = {}
        if tag_id is not None:
            body["tag_id"] = tag_id
        if tag_name is not None:
            body["tag_name"] = tag_name
        if _is_async_context():
            return self._async_set_purchase_tag(purchase_id, body)
        return self._sync_set_purchase_tag(purchase_id, body)

    async def _async_set_purchase_tag(self, purchase_id: int, body: dict) -> None:
        await self._client._async_request(
            "PUT", f"/api/v1/openapi/email/purchases/{purchase_id}/tag", json_data=body
        )

    def _sync_set_purchase_tag(self, purchase_id: int, body: dict) -> None:
        self._client._sync_request(
            "PUT", f"/api/v1/openapi/email/purchases/{purchase_id}/tag", json_data=body
        )

    def batch_set_purchase_tag(
        self,
        ids: List[int],
        tag_id: Optional[int] = None,
        tag_name: Optional[str] = None,
    ):
        """
        批量设置已购邮箱标签

        Args:
            ids: 已购邮箱 ID 列表
            tag_id: 标签 ID（与 tag_name 二选一，传 0 表示移除标签）
            tag_name: 标签名称（与 tag_id 二选一）

        Returns:
            None

        示例::
            client.user.batch_set_purchase_tag([1, 2, 3], tag_name="主力号")
        """
        body: Dict[str, Any] = {"ids": ids}
        if tag_id is not None:
            body["tag_id"] = tag_id
        if tag_name is not None:
            body["tag_name"] = tag_name
        if _is_async_context():
            return self._async_batch_set_purchase_tag(body)
        return self._sync_batch_set_purchase_tag(body)

    async def _async_batch_set_purchase_tag(self, body: dict) -> None:
        await self._client._async_request(
            "POST", "/api/v1/openapi/email/purchases/batch-tag", json_data=body
        )

    def _sync_batch_set_purchase_tag(self, body: dict) -> None:
        self._client._sync_request(
            "POST", "/api/v1/openapi/email/purchases/batch-tag", json_data=body
        )

    def api_get_purchases(
        self,
        count: int,
        tag_id: Optional[int] = None,
        tag_name: Optional[str] = None,
        mark_tag_id: Optional[int] = None,
        mark_tag_name: Optional[str] = None,
    ):
        """
        按标签获取已购邮箱（API 下发）

        仅返回未禁用且标签 limit_type=1（可下发）的邮箱。
        可选择将获取到的邮箱标记为另一个标签。

        Args:
            count: 获取数量（1-100）
            tag_id: 按标签 ID 筛选（与 tag_name 二选一）
            tag_name: 按标签名称筛选（与 tag_id 二选一）
            mark_tag_id: 获取后将邮箱标记为此标签 ID（与 mark_tag_name 二选一）
            mark_tag_name: 获取后将邮箱标记为此标签名称（与 mark_tag_id 二选一）

        Returns:
            List[PurchaseItem]: 已购邮箱列表

        示例::
            items = client.user.api_get_purchases(5, tag_name="主力号", mark_tag_name="已使用")
            for item in items:
                print(item.email_address, item.token)
        """
        body: Dict[str, Any] = {"count": count}
        if tag_id is not None:
            body["tag_id"] = tag_id
        if tag_name is not None:
            body["tag_name"] = tag_name
        if mark_tag_id is not None:
            body["mark_tag_id"] = mark_tag_id
        if mark_tag_name is not None:
            body["mark_tag_name"] = mark_tag_name
        if _is_async_context():
            return self._async_api_get_purchases(body)
        return self._sync_api_get_purchases(body)

    async def _async_api_get_purchases(self, body: dict) -> List[PurchaseItem]:
        data = await self._client._async_request(
            "POST", "/api/v1/openapi/email/purchases/api-get", json_data=body
        )
        return [_parse_purchase_item(i) for i in data]

    def _sync_api_get_purchases(self, body: dict) -> List[PurchaseItem]:
        data = self._client._sync_request(
            "POST", "/api/v1/openapi/email/purchases/api-get", json_data=body
        )
        return [_parse_purchase_item(i) for i in data]

    # ===== 标签管理 =====

    def create_tag(self, name: str, limit_type: int, remark: Optional[str] = None):
        """
        创建邮箱标签

        Args:
            name: 标签名称（用户下唯一）
            limit_type: 限制类型：0=不下发 1=可下发
            remark: 备注说明（可选）

        Returns:
            TagItem: 创建的标签信息

        示例::
            tag = client.user.create_tag("主力号", limit_type=1, remark="主力邮箱池")
            print(f"标签 ID: {tag.id}, 名称: {tag.name}")
        """
        body: Dict[str, Any] = {"name": name, "limit_type": limit_type}
        if remark is not None:
            body["remark"] = remark
        if _is_async_context():
            return self._async_create_tag(body)
        return self._sync_create_tag(body)

    async def _async_create_tag(self, body: dict) -> "TagItem":
        data = await self._client._async_request(
            "POST", "/api/v1/openapi/email/tags", json_data=body
        )
        return _parse_tag_item(data)

    def _sync_create_tag(self, body: dict) -> "TagItem":
        data = self._client._sync_request(
            "POST", "/api/v1/openapi/email/tags", json_data=body
        )
        return _parse_tag_item(data)

    def get_tags(self):
        """
        获取所有标签列表

        Returns:
            List[TagItem]: 标签列表

        示例::
            tags = client.user.get_tags()
            for tag in tags:
                print(tag.id, tag.name, tag.limit_type, tag.purchase_count)
        """
        if _is_async_context():
            return self._async_get_tags()
        return self._sync_get_tags()

    async def _async_get_tags(self) -> List["TagItem"]:
        data = await self._client._async_request("GET", "/api/v1/openapi/email/tags")
        return [_parse_tag_item(i) for i in data]

    def _sync_get_tags(self) -> List["TagItem"]:
        data = self._client._sync_request("GET", "/api/v1/openapi/email/tags")
        return [_parse_tag_item(i) for i in data]

    def update_tag(
        self,
        tag_id_or_name: Union[int, str],
        limit_type: int,
        name: Optional[str] = None,
        remark: Optional[str] = None,
    ):
        """
        更新标签

        Args:
            tag_id_or_name: 标签 ID（数字）或标签名称（字符串）
            limit_type: 限制类型：0=不下发 1=可下发
            name: 新的标签名称（可选）
            remark: 备注说明（可选）

        Returns:
            None

        示例::
            client.user.update_tag(1, limit_type=1, name="备用号")
            client.user.update_tag("主力号", limit_type=0)
        """
        body: Dict[str, Any] = {"limit_type": limit_type}
        if name is not None:
            body["name"] = name
        if remark is not None:
            body["remark"] = remark
        if _is_async_context():
            return self._async_update_tag(tag_id_or_name, body)
        return self._sync_update_tag(tag_id_or_name, body)

    async def _async_update_tag(self, tag_id_or_name: Union[int, str], body: dict) -> None:
        await self._client._async_request(
            "PUT", f"/api/v1/openapi/email/tags/{tag_id_or_name}", json_data=body
        )

    def _sync_update_tag(self, tag_id_or_name: Union[int, str], body: dict) -> None:
        self._client._sync_request(
            "PUT", f"/api/v1/openapi/email/tags/{tag_id_or_name}", json_data=body
        )

    def delete_tag(self, tag_id_or_name: Union[int, str]):
        """
        删除标签

        删除后，该标签下的已购邮箱将变为无标签状态。

        Args:
            tag_id_or_name: 标签 ID（数字）或标签名称（字符串）

        Returns:
            None

        示例::
            client.user.delete_tag(1)
            client.user.delete_tag("已使用")
        """
        if _is_async_context():
            return self._async_delete_tag(tag_id_or_name)
        return self._sync_delete_tag(tag_id_or_name)

    async def _async_delete_tag(self, tag_id_or_name: Union[int, str]) -> None:
        await self._client._async_request(
            "DELETE", f"/api/v1/openapi/email/tags/{tag_id_or_name}"
        )

    def _sync_delete_tag(self, tag_id_or_name: Union[int, str]) -> None:
        self._client._sync_request(
            "DELETE", f"/api/v1/openapi/email/tags/{tag_id_or_name}"
        )
