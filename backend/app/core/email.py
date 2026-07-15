"""
邮件服务模块
用于发送密码重置邮件、邮箱验证邮件等通知
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config.settings import settings


def send_password_reset_email(to_email: str, verification_code: str) -> bool:
    """
    发送密码重置邮件（包含验证码）

    Args:
        to_email: 收件人邮箱
        verification_code: 6位验证码

    Returns:
        bool: 是否发送成功
    """
    try:
        # 创建邮件对象
        msg = MIMEMultipart()
        msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = "密码重置验证码 - RSOD Agent Platform"

        # 邮件正文（HTML 格式）
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #409eff;">密码重置</h2>
                <p>您好，</p>
                <p>我们收到了您的密码重置请求。请使用以下验证码完成密码重置：</p>
                <div style="margin: 30px 0; text-align: center;">
                    <div style="display: inline-block; background-color: #f5f5f5; padding: 15px 30px; border-radius: 8px;">
                        <span style="font-size: 32px; font-weight: bold; color: #409eff; letter-spacing: 4px;">{verification_code}</span>
                    </div>
                </div>
                <p style="color: #999; font-size: 14px;">
                    此验证码将在 5 分钟后失效。如果您没有请求重置密码，请忽略此邮件。
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">
                    此邮件由系统自动发送，请勿回复。
                </p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # 连接 SMTP 服务器并发送邮件
        if settings.SMTP_USE_TLS:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)

        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        return True

    except Exception as e:
        print(f"发送邮件失败: {str(e)}")
        return False


def send_verification_email(to_email: str, verification_token: str) -> bool:
    """
    发送邮箱验证邮件

    Args:
        to_email: 收件人邮箱
        verification_token: 验证令牌

    Returns:
        bool: 是否发送成功
    """
    try:
        # 构建验证链接（通过后端重定向，绕过邮件客户端安全检查）
        verify_url = f"{settings.SERVER_HOST}:{settings.SERVER_PORT}/api/auth/verify-email-redirect?token={verification_token}"

        # 创建邮件对象
        msg = MIMEMultipart()
        msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = "邮箱验证 - RSOD Agent Platform"

        # 邮件正文（HTML 格式）
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #409eff;">邮箱验证</h2>
                <p>您好，</p>
                <p>感谢您注册 RSOD Agent Platform。请点击下面的链接验证您的邮箱：</p>
                <div style="margin: 30px 0;">
                    <a href="{verify_url}" style="color: #409eff; text-decoration: underline; font-size: 16px;">
                        {verify_url}
                    </a>
                </div>
                <p style="color: #999; font-size: 14px;">
                    此链接将在 24 小时后失效。
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">
                    此邮件由系统自动发送，请勿回复。
                </p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # 连接 SMTP 服务器并发送邮件
        if settings.SMTP_USE_TLS:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)

        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        return True

    except Exception as e:
        print(f"发送邮件失败: {str(e)}")
        return False
