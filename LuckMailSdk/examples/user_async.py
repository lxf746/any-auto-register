"""
examples/user_async.py - 用户端异步调用示例

演示 LuckMailSdk 在异步（asyncio）场景下的完整使用方法。
与同步版本的代码几乎完全相同，只需在方法前加 await 即可。
"""

import asyncio
from luckmail import LuckMailClient

# 初始化客户端（同步/异步共用同一个客户端实例）
client = LuckMailClient(
    base_url="https://your-domain.com",
    api_key="your_api_key_here",
)


async def demo_user_info():
    """查询用户信息（异步）"""
    print("=" * 50)
    print("📋 用户信息（异步）")
    print("=" * 50)
    
    # 只需在方法前加 await，其余代码完全相同
    info = await client.user.get_user_info()
    print(f"用户名: {info.username}")
    print(f"余额: {info.balance}")


async def demo_create_order_simple():
    """一键接码（异步版本）"""
    print("\n" + "=" * 50)
    print("🚀 一键接码（异步）")
    print("=" * 50)
    
    async def on_poll(result):
        """异步轮询回调"""
        print(f"  轮询中... 状态: {result.status}")
    
    # 异步版本只需加 await
    result = await client.create_and_wait(
        project_code="twitter",
        email_type="ms_graph",
        timeout=300,
        interval=3.0,
        on_poll=on_poll,
    )
    
    if result.status == "success":
        print(f"✅ 验证码: {result.verification_code}")
        print(f"📧 来自: {result.mail_from}")
    else:
        print(f"❌ 接码失败: {result.status}")


async def demo_concurrent_orders():
    """并发接码（异步的核心优势）"""
    print("\n" + "=" * 50)
    print("⚡ 并发接码（异步独有优势）")
    print("=" * 50)
    
    print("同时为 3 个项目接码...")
    
    # 并发创建 3 个订单
    orders = await asyncio.gather(
        client.user.create_order("twitter", email_type="ms_graph"),
        client.user.create_order("facebook", email_type="ms_imap"),
        client.user.create_order("google", email_type="google_variant"),
    )
    
    print("3 个订单已创建，并发等待验证码...")
    
    # 并发等待所有验证码
    results = await asyncio.gather(
        client.user.wait_for_code(orders[0].order_no, timeout=300),
        client.user.wait_for_code(orders[1].order_no, timeout=300),
        client.user.wait_for_code(orders[2].order_no, timeout=300),
    )
    
    for i, result in enumerate(results):
        print(f"订单 {i+1}: {result.status} - {result.verification_code}")


async def demo_context_manager():
    """使用异步上下文管理器（自动管理连接）"""
    print("\n" + "=" * 50)
    print("🔒 异步上下文管理器")
    print("=" * 50)
    
    async with LuckMailClient(
        base_url="https://your-domain.com",
        api_key="your_api_key_here",
    ) as c:
        balance = await c.user.get_balance()
        print(f"余额: {balance}")
        # 退出 async with 块时自动关闭连接


async def demo_supplier():
    """供应商端异步示例"""
    print("\n" + "=" * 50)
    print("🏭 供应商端（异步）")
    print("=" * 50)
    
    # 获取数据看板
    summary = await client.supplier.get_dashboard()
    print(f"总邮箱: {summary.total_emails}")
    print(f"活跃邮箱: {summary.active_emails}")
    print(f"今日接码: {summary.today_assigned}")
    print(f"今日成功: {summary.today_success}")
    print(f"今日佣金: {summary.today_commission}")
    print(f"成功率: {summary.success_rate:.1f}%")
    
    # 处理待处理申述
    appeals = await client.supplier.get_appeals(status=1)
    print(f"\n待处理申述: {appeals.total} 个")
    
    for appeal in appeals.list[:3]:
        print(f"  {appeal.appeal_no}: {appeal.reason} - {appeal.status}")
        # 批量同意退款（示例注释，避免误操作）
        # await client.supplier.reply_appeal(
        #     appeal.appeal_no, result=1, reply="核查后同意退款"
        # )


async def demo_hmac_auth():
    """使用 HMAC 签名验证（高安全性）"""
    print("\n" + "=" * 50)
    print("🔐 HMAC 高安全模式")
    print("=" * 50)
    
    secure_client = LuckMailClient(
        base_url="https://your-domain.com",
        api_key="your_api_key_here",
        api_secret="your_api_secret_here",  # API Secret
        use_hmac=True,                       # 开启 HMAC 签名
    )
    
    # 使用方式完全相同
    info = await secure_client.user.get_user_info()
    print(f"HMAC 模式连接成功: {info.username}")
    await secure_client.aclose()


async def main():
    """主函数"""
    print("🔑 LuckMail Python SDK - 异步调用示例")
    print("请修改 base_url 和 api_key 后运行本脚本\n")
    
    # 注意：实际使用时请取消注释并填写真实参数
    # await demo_user_info()
    # await demo_create_order_simple()    # ← 最常用
    # await demo_concurrent_orders()      # ← 异步并发接码
    # await demo_context_manager()
    # await demo_supplier()
    # await demo_hmac_auth()
    
    print("请取消注释相应函数后运行")


if __name__ == "__main__":
    asyncio.run(main())
