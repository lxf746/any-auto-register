"""
examples/user_sync.py - 用户端同步调用示例

演示 LuckMailSdk 在同步（普通 Python 脚本）场景下的完整使用方法。
所有方法与异步版本完全相同，无需任何改动。
"""

from luckmail import LuckMailClient

# 初始化客户端
client = LuckMailClient(
    base_url="https://your-domain.com",
    api_key="your_api_key_here",
    # api_secret="your_api_secret_here",  # 可选：HMAC 高安全模式
    # use_hmac=True,                       # 开启 HMAC 签名验证
)


def demo_user_info():
    """查询用户信息"""
    print("=" * 50)
    print("📋 用户信息")
    print("=" * 50)
    
    info = client.user.get_user_info()
    print(f"用户名: {info.username}")
    print(f"邮箱: {info.email}")
    print(f"余额: {info.balance}")
    print(f"状态: {info.status}")
    
    balance = client.user.get_balance()
    print(f"\n当前余额: {balance}")


def demo_projects():
    """获取项目列表"""
    print("\n" + "=" * 50)
    print("📦 项目列表")
    print("=" * 50)
    
    result = client.user.get_projects(page_size=10)
    print(f"共 {result.total} 个项目，显示前 {len(result.list)} 个：")
    
    for project in result.list[:5]:
        print(f"  - [{project.code}] {project.name}")
        print(f"    支持类型: {', '.join(project.email_types)}")
        print(f"    超时: {project.timeout_seconds}s，保质期: {project.warranty_hours}h")
        for price in project.prices:
            print(f"    {price.email_type}: 接码 {price.code_price}，购买 {price.buy_price}")


def demo_create_order_simple():
    """一行代码创建订单并等待验证码（推荐方式）"""
    print("\n" + "=" * 50)
    print("🚀 一键接码（推荐）")
    print("=" * 50)
    
    print("正在为 Twitter 项目接码...")
    
    def on_poll(result):
        """每次轮询的回调（可选）"""
        print(f"  轮询中... 状态: {result.status}")
    
    # 一行代码搞定：创建订单 + 等待验证码
    result = client.create_and_wait(
        project_code="twitter",
        email_type="ms_graph",      # 可选：指定邮箱类型
        # domain="outlook.com",     # 可选：指定域名
        timeout=300,                # 最大等待 300 秒
        interval=3.0,               # 每 3 秒轮询一次
        on_poll=on_poll,            # 轮询回调（可选）
    )
    
    if result.status == "success":
        print(f"\n✅ 接码成功！")
        print(f"  验证码: {result.verification_code}")
        print(f"  发件人: {result.mail_from}")
        print(f"  邮件标题: {result.mail_subject}")
    else:
        print(f"\n❌ 接码失败: {result.status}")


def demo_create_order_manual():
    """手动创建订单并轮询验证码（适合需要精细控制的场景）"""
    print("\n" + "=" * 50)
    print("🔧 手动接码（精细控制）")
    print("=" * 50)
    
    # 第一步：创建订单
    order = client.user.create_order(
        project_code="twitter",
        email_type="ms_graph",
    )
    print(f"订单号: {order.order_no}")
    print(f"分配邮箱: {order.email_address}")
    print(f"超时时间: {order.expired_at}")
    
    # 第二步：等待验证码（带轮询）
    print("等待验证码...")
    result = client.user.wait_for_code(order.order_no, timeout=300, interval=3.0)
    
    if result.status == "success":
        print(f"✅ 验证码: {result.verification_code}")
    elif result.status == "timeout":
        print("❌ 超时未收到验证码")
        # 可以选择取消订单（虽然超时已自动结束）
    elif result.status == "cancelled":
        print("❌ 订单已取消")


def demo_purchase_and_use():
    """购买邮箱并使用 Token 接码"""
    print("\n" + "=" * 50)
    print("💰 购买邮箱 + Token 接码")
    print("=" * 50)
    
    # 购买邮箱
    purchase_result = client.user.purchase_emails(
        project_code="twitter",
        quantity=2,
        email_type="ms_graph",
    )
    print(f"购买成功！消费: {purchase_result['total_cost']}")
    print(f"剩余余额: {purchase_result['balance_after']}")
    
    for item in purchase_result["purchases"]:
        print(f"  邮箱: {item['email_address']}, Token: {item['token']}")
    
    # 使用 Token 等待验证码
    if purchase_result["purchases"]:
        token = purchase_result["purchases"][0]["token"]
        print(f"\n使用 Token 等待验证码: {token}")
        
        alive = client.user.check_token_alive(token)
        print(f"测活结果: alive={alive.alive}, message={alive.message}, mail_count={alive.mail_count}")

        result = client.user.wait_for_token_code(token, timeout=120, interval=3.0)
        
        if result.has_new_mail:
            print(f"✅ 验证码: {result.verification_code}")
            if result.mail:
                print(f"  来自: {result.mail.get('from')}")
                print(f"  标题: {result.mail.get('subject')}")
        else:
            print("暂无新邮件")


def demo_email_management():
    """邮箱管理示例"""
    print("\n" + "=" * 50)
    print("📧 邮箱管理")
    print("=" * 50)
    
    # 获取邮箱类型
    types = client.user.get_email_types()
    print("支持的邮箱类型:")
    for t in types:
        print(f"  {t['type']}: {t['name']}")
    
    # 查看我的邮箱列表
    emails = client.user.get_emails(page=1, page_size=5)
    print(f"\n我的邮箱（共 {emails.total} 个）:")
    for email in emails.list:
        print(f"  {email.address} [{email.type}] 状态:{email.status}")
    
    # 导入邮箱
    # result = client.user.import_emails(
    #     email_type="ms_graph",
    #     emails=[
    #         {
    #             "address": "user@outlook.com",
    #             "password": "password123",
    #             "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    #             "refresh_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    #         }
    #     ]
    # )
    # print(f"导入结果 - 成功: {result.success}, 重复: {result.duplicate}, 失败: {result.failed}")


def demo_orders():
    """查看订单历史"""
    print("\n" + "=" * 50)
    print("📋 订单历史")
    print("=" * 50)
    
    result = client.user.get_orders(page=1, page_size=5, status=2)
    print(f"已完成订单（共 {result.total} 个）:")
    for order in result.list:
        print(f"  {order['order_no']} - {order['project_name']} - {order['verification_code']}")


def demo_appeal():
    """申述示例"""
    print("\n" + "=" * 50)
    print("📝 提交申述")
    print("=" * 50)
    
    # result = client.user.create_appeal(
    #     appeal_type=1,        # 1=接码订单 2=购买邮箱
    #     order_id=123,         # 接码订单 ID
    #     reason="no_code",     # 申述原因
    #     description="等待 5 分钟后仍未收到验证码，订单已超时",
    #     evidence_urls=[],
    # )
    # print(f"申述单号: {result['appeal_no']}")
    print("（申述接口已注释，避免误操作）")


def demo_tag_management():
    """标签管理示例"""
    print("\n" + "=" * 50)
    print("🏷️  标签管理")
    print("=" * 50)

    # 创建标签
    tag = client.user.create_tag("主力号", limit_type=1, remark="主力邮箱池，可下发")
    print(f"创建标签: ID={tag.id}, 名称={tag.name}, 限制类型={tag.limit_type}")

    # 获取所有标签
    tags = client.user.get_tags()
    print(f"\n当前共 {len(tags)} 个标签:")
    for t in tags:
        print(f"  [{t.id}] {t.name} (limit_type={t.limit_type}, 邮箱数={t.purchase_count})")

    # 更新标签
    # client.user.update_tag(tag.id, limit_type=0, name="备用号", remark="暂不下发")
    # print("标签已更新")

    # 删除标签
    # client.user.delete_tag(tag.id)
    # print("标签已删除")


def demo_purchase_tag_management():
    """已购邮箱标签和禁用管理示例"""
    print("\n" + "=" * 50)
    print("📧 已购邮箱管理（标签 + 禁用）")
    print("=" * 50)

    # 查看已购邮箱（支持更多筛选条件）
    result = client.user.get_purchases(
        page=1,
        page_size=10,
        keyword="outlook",
        user_disabled=0,  # 只看未禁用的
    )
    print(f"已购邮箱（共 {result.total} 个）:")
    for item in result.list:
        print(f"  [{item.id}] {item.email_address} 标签:{item.tag_name or '无'} 禁用:{item.user_disabled}")

    if result.list:
        first_id = result.list[0].id

        # 设置单个邮箱标签
        # client.user.set_purchase_tag(first_id, tag_name="主力号")
        # print(f"已为邮箱 {first_id} 设置标签")

        # 批量设置标签
        # ids = [item.id for item in result.list[:3]]
        # client.user.batch_set_purchase_tag(ids, tag_name="主力号")
        # print(f"已为 {len(ids)} 个邮箱批量设置标签")

        # 禁用单个邮箱
        # client.user.set_purchase_disabled(first_id, 1)
        # print(f"已禁用邮箱 {first_id}")

        # 批量禁用
        # ids = [item.id for item in result.list[:3]]
        # client.user.batch_set_purchase_disabled(ids, 1)
        # print(f"已批量禁用 {len(ids)} 个邮箱")

    print("（修改操作已注释，避免误操作）")


def demo_api_get_purchases():
    """按标签获取已购邮箱（API 下发）示例"""
    print("\n" + "=" * 50)
    print("🚀 按标签获取已购邮箱（API 下发）")
    print("=" * 50)

    # 从"主力号"标签取 5 个邮箱，并将其标记为"已使用"
    items = client.user.api_get_purchases(
        count=5,
        tag_name="主力号",        # 从哪个标签取
        mark_tag_name="已使用",   # 取出后打什么标签
    )
    print(f"获取到 {len(items)} 个邮箱:")
    for item in items:
        print(f"  {item.email_address} | token: {item.token} | 新标签: {item.tag_name}")


def demo_token_mail_list_and_detail():
    """通过 Token 获取邮件列表和邮件详情"""
    print("\n" + "=" * 50)
    print("📬 Token 邮件列表 & 详情")
    print("=" * 50)

    token = "tok_abc123def456"  # 替换为实际的已购邮箱 token

    # 获取邮件列表
    mail_list = client.user.get_token_mails(token)
    print(f"邮箱: {mail_list.email_address}")
    print(f"项目: {mail_list.project}")
    print(f"保修截止: {mail_list.warranty_until}")
    print(f"邮件数量: {len(mail_list.mails)}")

    for mail in mail_list.mails:
        print(f"  [{mail.received_at}] {mail.from_addr}: {mail.subject}")
        print(f"    message_id: {mail.message_id}")

    # 获取邮件详情
    if mail_list.mails:
        first_mail = mail_list.mails[0]
        detail = client.user.get_token_mail_detail(token, first_mail.message_id)
        print(f"\n📧 邮件详情:")
        print(f"  发件人: {detail.from_addr}")
        print(f"  收件人: {detail.to}")
        print(f"  主题: {detail.subject}")
        print(f"  正文: {detail.body_text[:200]}...")
        if detail.verification_code:
            print(f"  ✅ 验证码: {detail.verification_code}")


if __name__ == "__main__":
    print("🔑 LuckMail Python SDK - 同步调用示例")
    print("请修改 base_url 和 api_key 后运行本脚本\n")
    
    # 注意：实际使用时请取消注释并填写真实参数
    # demo_user_info()
    # demo_projects()
    # demo_create_order_simple()        # ← 最常用，一行代码搞定接码
    # demo_create_order_manual()
    # demo_purchase_and_use()
    # demo_email_management()
    # demo_orders()
    # demo_appeal()
    # demo_tag_management()             # ← 标签管理
    # demo_purchase_tag_management()    # ← 已购邮箱标签+禁用管理
    # demo_api_get_purchases()          # ← 按标签获取已购邮箱
    # demo_token_mail_list_and_detail() # ← Token 邮件列表 & 详情
    
    print("请取消注释相应函数后运行")
