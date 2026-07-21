"""
邮件服务模块
用于发送密码重置邮件、邮箱验证邮件等通知
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config.settings import settings


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    发送密码重置邮件（仅包含验证码）

    Args:
        to_email: 收件人邮箱
        reset_token: 重置验证码

    Returns:
        bool: 是否发送成功
    """
    try:
        # 创建邮件对象
        msg = MIMEMultipart()
        msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = "密码重置 - RSOD Agent Platform"

        # 邮件正文（仅显示验证码）
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #409eff;">密码重置验证码</h2>
                <div style="text-align: center; margin: 30px 0;">
                    <p style="font-size: 36px; font-weight: bold; color: #409eff; letter-spacing: 8px;">
                        {reset_token}
                    </p>
                </div>
                <p style="color: #999; font-size: 14px; text-align: center;">
                    此验证码将在 1 小时后失效。
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
    发送邮箱验证邮件（带验证链接）

    Args:
        to_email: 收件人邮箱
        verification_token: 验证令牌

    Returns:
        bool: 是否发送成功
    """
    try:
        # 构建验证链接
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"

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
                <p>感谢您注册 RSOD Agent Platform。请点击下方按钮验证您的邮箱：</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verify_url}" 
                       style="background-color: #409eff; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        验证邮箱
                    </a>
                </div>
                <p>或者，您可以复制以下链接到浏览器中打开：</p>
                <p style="background-color: #f5f5f5; padding: 10px; border-radius: 3px; word-break: break-all;">
                    {verify_url}
                </p>
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