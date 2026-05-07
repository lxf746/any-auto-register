"""
LuckMailSdk 异常类定义
"""


class LuckMailError(Exception):
    """LuckMail SDK 基础异常"""
    pass


class AuthError(LuckMailError):
    """鉴权失败异常"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)


class APIError(LuckMailError):
    """API 调用异常"""
    def __init__(self, code: int, message: str, data=None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"API Error [{code}]: {message}")


class NetworkError(LuckMailError):
    """网络请求异常"""
    def __init__(self, message: str = "Network error occurred"):
        super().__init__(message)


class TimeoutError(LuckMailError):
    """超时异常"""
    def __init__(self, message: str = "Request timed out"):
        super().__init__(message)
