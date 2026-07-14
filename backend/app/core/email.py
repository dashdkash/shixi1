"""
邮件服务模块
用于发送密码重置邮件等通知
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config.settings import settings


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    发送密码重置邮件

    Args:
        to_email: 收件人邮箱
        reset_token: 重置令牌

    Returns:
        bool: 是否发送成功
    """
    try:
        # 构建重置链接
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

        # 创建邮件对象
        msg = MIMEMultipart()
        msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = "密码重置 - RSOD Agent Platform"

        # 邮件正文（HTML 格式）
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #409eff;">密码重置</h2>
                <p>您好，</p>
                <p>我们收到了您的密码重置请求。请点击下方按钮重置密码：</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #409eff; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        重置密码
                    </a>
                </div>
                <p>或者，您可以复制以下链接到浏览器中打开：</p>
                <p style="background-color: #f5f5f5; padding: 10px; border-radius: 3px; word-break: break-all;">
                    {reset_url}
                </p>
                <p style="color: #999; font-size: 14px;">
                    此链接将在 1 小时后失效。如果您没有请求重置密码，请忽略此邮件。
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
