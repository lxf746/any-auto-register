"""
LuckMailClient - 主客户端入口

整合用户端和供应商端 API，提供统一的访问入口。
支持同步/异步双模式，智能识别调用上下文。
"""

from typing import Optional

from .http_client import LuckMailHttpClient
from .user import UserAPI
from .supplier import SupplierAPI


class LuckMailClient:
    """
    LuckMail SDK 主客户端
    
    提供用户端（user）和供应商端（supplier）两套 API 访问入口。
    所有 API 方法均支持同步/异步双模式，根据调用上下文自动识别，
    无需手动区分，大幅降低接入成本。
    
    Args:
        base_url: API 基础 URL，如 https://your-domain.com
        api_key: API Key（在平台「个人设置」页面生成）
        api_secret: API Secret（可选，用于 HMAC 签名验证，安全性更高）
        timeout: 请求超时时间（秒），默认 30
        use_hmac: 是否使用 HMAC 签名验证，默认 False
    
    用户端示例（同步）::
    
        from luckmail import LuckMailClient
        
        client = LuckMailClient(
            base_url="https://your-domain.com",
            api_key="your_api_key_here"
        )
        
        # 查询余额
        balance = client.user.get_balance()
        print(f"余额: {balance}")
        
        # 接码（一行搞定）
        code = client.user.create_and_wait('twitter')
        print(f"验证码: {code.verification_code}")
    
    用户端示例（异步）::
    
        import asyncio
        from luckmail import LuckMailClient
        
        client = LuckMailClient(
            base_url="https://your-domain.com",
            api_key="your_api_key_here"
        )
        
        async def main():
            balance = await client.user.get_balance()
            print(f"余额: {balance}")
            
            code = await client.user.create_and_wait('twitter')
            print(f"验证码: {code.verification_code}")
        
        asyncio.run(main())
    
    供应商端示例::
    
        # 查看数据看板
        summary = client.supplier.get_dashboard()
        print(f"今日接码: {summary.today_assigned}")
        
        # 处理申述
        client.supplier.reply_appeal("APL001", result=1, reply="同意退款")
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_secret: Optional[str] = None,
        timeout: float = 30.0,
        use_hmac: bool = False,
    ):
        self._http = LuckMailHttpClient(
            base_url=base_url,
            api_key=api_key,
            api_secret=api_secret,
            timeout=timeout,
            use_hmac=use_hmac,
        )
        # 用户端 API
        self.user = UserAPI(self._http)
        # 供应商端 API
        self.supplier = SupplierAPI(self._http)
    
    # ===== 快捷方法（用户端常用操作）=====
    
    def create_and_wait(
        self,
        project_code: str,
        email_type: Optional[str] = None,
        domain: Optional[str] = None,
        specified_email: Optional[str] = None,
        variant_mode: Optional[str] = None,
        timeout: int = 300,
        interval: float = 3.0,
        on_poll=None,
    ):
        """
        创建接码订单并等待验证码（一站式方法）
        
        自动创建订单并轮询等待验证码，智能识别同步/异步上下文。
        
        Args:
            project_code: 项目编码，如 'twitter', 'facebook'
            email_type: 邮箱类型（可选）
            domain: 指定域名（可选）
            specified_email: 指定邮箱（可选）
            variant_mode: 谷歌变种模式（可选，仅 email_type=google_variant 时有效）: dot / plus / mixed / all
            timeout: 最大等待时间（秒），默认 300
            interval: 轮询间隔（秒），默认 3.0
            on_poll: 每次轮询的回调函数（可选）
        
        Returns:
            OrderCode: 验证码结果
        
        同步示例::
        
            result = client.create_and_wait('twitter')
            if result.status == 'success':
                print(f"✅ 验证码: {result.verification_code}")
                print(f"📧 来自: {result.mail_from}")
            else:
                print(f"❌ 接码失败: {result.status}")
        
        异步示例::
        
            result = await client.create_and_wait('twitter', email_type='ms_graph')
            if result.status == 'success':
                print(f"✅ 验证码: {result.verification_code}")
        
        带进度回调的示例::
        
            def on_poll(code_result):
                print(f"轮询中... 状态: {code_result.status}")
            
            result = client.create_and_wait('twitter', on_poll=on_poll)
        """
        from .http_client import _is_async_context
        if _is_async_context():
            return self._async_create_and_wait(
                project_code, email_type, domain, specified_email, variant_mode,
                timeout, interval, on_poll
            )
        return self._sync_create_and_wait(
            project_code, email_type, domain, specified_email, variant_mode,
            timeout, interval, on_poll
        )
    
    async def _async_create_and_wait(
        self, project_code, email_type, domain, specified_email, variant_mode,
        timeout, interval, on_poll
    ):
        """异步创建并等待验证码"""
        body = {"project_code": project_code}
        if email_type:
            body["email_type"] = email_type
        if domain:
            body["domain"] = domain
        if specified_email:
            body["specified_email"] = specified_email
        if variant_mode:
            body["variant_mode"] = variant_mode
        
        order = await self.user._async_create_order(body)
        return await self.user._async_wait_for_code(
            order.order_no, timeout, interval, on_poll
        )
    
    def _sync_create_and_wait(
        self, project_code, email_type, domain, specified_email, variant_mode,
        timeout, interval, on_poll
    ):
        """同步创建并等待验证码"""
        body = {"project_code": project_code}
        if email_type:
            body["email_type"] = email_type
        if domain:
            body["domain"] = domain
        if specified_email:
            body["specified_email"] = specified_email
        if variant_mode:
            body["variant_mode"] = variant_mode
        
        order = self.user._sync_create_order(body)
        return self.user._sync_wait_for_code(
            order.order_no, timeout, interval, on_poll
        )
    
    def close(self):
        """关闭客户端（同步）"""
        self._http.close()
    
    async def aclose(self):
        """关闭客户端（异步）"""
        await self._http.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def __repr__(self) -> str:
        return (
            f"LuckMailClient(base_url={self._http.base_url!r}, "
            f"api_key={self._http.api_key[:8]}...)"
        )
