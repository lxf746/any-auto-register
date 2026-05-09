import requests

def fetch_emails_from_format(account_data):
    """
    解析指定格式的字符串并使用 Microsoft Graph API 获取邮件。
    格式要求: Email----Password----ClientID----RefreshToken
    """
    # 1. 解析字符串
    parts = account_data.split("----")
    if len(parts) != 4:
        print("[-] 格式错误！请确保格式为: 邮箱----密码----ClientID----RefreshToken")
        return

    email = parts[0]
    password = parts[1]  # 注意：OAuth2.0 Token 刷新流程不需要明文密码
    client_id = parts[2]
    refresh_token = parts[3]

    print(f"[*] 正在尝试获取邮箱的 Access Token: {email}")

    # 2. 使用 Refresh Token 获取新的 Access Token
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    token_payload = {
        "client_id": client_id,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
        # 注意: 如果您的 Azure 应用注册为 Web 应用且包含密钥，
        # 则还需要在此处添加 "client_secret": "您的应用密钥"
    }

    try:
        token_response = requests.post(token_url, data=token_payload)
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        print("[+] 成功获取 Access Token！")
    except requests.exceptions.RequestException as e:
        print(f"[-] 获取 Access Token 失败: {e}")
        if token_response.text:
            print(f"    服务器返回信息: {token_response.text}")
        return

    # 3. 使用 Access Token 请求 Graph API 获取收件箱邮件
    # 这里使用 $top=5 参数，仅获取最新 5 封邮件作为示例
    graph_endpoint = (
        "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
        "?$top=5"
        "&$select=id,subject,from,receivedDateTime,bodyPreview"
        "&$orderby=receivedDateTime desc"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        # 让后续按 message id 拉取的 body 尽量返回 text（否则经常是 html）
        "Prefer": 'outlook.body-content-type="text"',
    }

    print(f"[*] 正在请求 Graph API 获取邮件...")
    try:
        graph_response = requests.get(graph_endpoint, headers=headers)
        graph_response.raise_for_status()
        messages = graph_response.json().get("value", [])
        
        print(f"\n[+] 成功获取到 {len(messages)} 封邮件:\n")
        print("-" * 50)
        for idx, msg in enumerate(messages, 1):
            msg_id = msg.get("id", "")
            subject = msg.get("subject", "<无主题>")
            sender_email = msg.get("from", {}).get("emailAddress", {}).get("address", "<未知发件人>")
            received_at = msg.get("receivedDateTime", "")
            preview = msg.get("bodyPreview", "") or ""
            print(f"第 {idx} 封")
            print(f"发件人: {sender_email}")
            print(f"主  题: {subject}")
            if received_at:
                print(f"时间: {received_at}")
            if preview:
                print(f"预览: {preview}")

            # 拉取完整正文内容（text）
            if msg_id:
                try:
                    detail_url = f"https://graph.microsoft.com/v1.0/me/messages/{msg_id}?$select=body"
                    detail = requests.get(detail_url, headers=headers, timeout=30)
                    detail.raise_for_status()
                    body = (detail.json().get("body") or {})
                    content = str(body.get("content") or "").strip()
                    if content:
                        print("正文:")
                        print(content)
                except requests.exceptions.RequestException as e:
                    print(f"[!] 获取正文失败: {e}")
            print("-" * 50)

    except requests.exceptions.RequestException as e:
        print(f"[-] 获取邮件失败: {e}")
        if graph_response.text:
            print(f"    服务器返回信息: {graph_response.text}")

# ==========================================
# 运行示例（交互式输入）
# ==========================================
if __name__ == "__main__":
    print("请输入账号数据 (格式: 邮箱----密码----ClientID----RefreshToken)")
    raw_data = input(">>> ").strip()
    
    if raw_data:
        fetch_emails_from_format(raw_data)
    else:
        print("[-] 未输入任何数据，程序退出。")