# test

### ⚠️ 注意事项
###    完成了认证模块需要的后续操作
1. 数据库迁移 ：需要运行 alembic upgrade head 来应用数据库变更
2. 邮件服务 ：忘记密码接口目前直接返回 token，生产环境需要集成邮件服务
根据当前代码实现，**忘记密码和修改密码功能可以正常工作**，但需要前端配合。让我详细说明：

## 当前实现流程

### 1. 忘记密码流程

**后端接口已实现：**

```
POST /api/auth/forgot-password
请求体: {"email": "user@example.com"}
响应: {
  "message": "重置令牌已生成",
  "reset_url": "/reset-password?token=xxxxx",
  "token": "xxxxx"  // 开发环境直接返回
}
```

**流程：**
1. 用户输入邮箱，调用接口
2. 后端生成 32 位随机 token，有效期 1 小时
3. 后端将 token 保存到数据库（`reset_token` 和 `reset_token_expires_at` 字段）
4. 返回 token 给前端

### 2. 重置密码流程

**后端接口已实现：**

```
POST /api/auth/reset-password
请求体: {"token": "xxxxx", "new_password": "newpass123"}
响应: {"message": "密码重置成功"}
```

**流程：**
1. 前端拿到 token，展示重置密码页面
2. 用户输入新密码
3. 前端调用接口，传入 token 和新密码
4. 后端验证 token 是否有效且未过期
5. 更新密码，清除 token
6. 返回成功

## 当前状态

✅ **后端功能完整**：
- 生成重置令牌
- 验证令牌有效性
- 检查令牌过期时间
- 更新密码
- 清除令牌

⚠️ **生产环境注意事项**：
- 当前开发环境直接返回 token
- 生产环境需要通过邮件发送 token（不实现邮件服务的话，可以通过其他方式如短信、站内信等）

## 前端需要实现

前端需要实现两个页面：

1. **忘记密码页面**：
   - 输入邮箱
   - 调用 `/api/auth/forgot-password`
   - 显示成功提示（生产环境提示"重置链接已发送到邮箱"）

2. **重置密码页面**：
   - 从 URL 获取 token
   - 输入新密码
   - 调用 `/api/auth/reset-password`
   - 跳转到登录页

## 结论

**可以正常忘记和修改密码**，后端逻辑完整。只需要前端实现对应的页面，并且生产环境需要确定 token 的传递方式（邮件、短信或其他）。


### 邮箱修改

## 修改内容
### 1. 配置文件 settings.py
添加了邮件相关配置项：

- SMTP_HOST : SMTP 服务器地址
- SMTP_PORT : SMTP 端口（默认 587）
- SMTP_USER : 发件人邮箱
- SMTP_PASSWORD : 邮箱授权码/密码
- SMTP_FROM_NAME : 发件人显示名称
- SMTP_USE_TLS : 是否使用 TLS 加密
- FRONTEND_URL : 前端地址（用于生成重置链接）
### 2. 邮件服务 core/email.py
创建了 send_password_reset_email() 函数：

- 使用 Python 标准库 smtplib 发送邮件
- 支持 HTML 格式的邮件内容
- 包含重置按钮和链接
- 自动处理 TLS 加密连接
- 返回发送成功/失败状态
### 3. 认证接口 auth.py
修改了 /forgot-password 接口：

- 生成 token 后调用邮件发送功能
- 生产环境：发送邮件给用户
- 开发环境（DEBUG=true）：如果邮件发送失败，返回 token 便于测试
- 防止邮箱枚举攻击：无论邮箱是否存在都返回相同提示
### 4. 环境变量示例 .env.example
添加了邮件配置示例，方便部署时参考。

## 使用方式
在 .env 文件中配置实际的邮件服务信息：

```
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your-email@qq.com
SMTP_PASSWORD=your-auth-code
SMTP_FROM_NAME=RSOD Agent Platform
SMTP_USE_TLS=true
FRONTEND_URL=http://localhost:5173
```
常用邮箱 SMTP 配置：

- QQ 邮箱： smtp.qq.com ，使用授权码
- 163 邮箱： smtp.163.com ，使用授权码
- Gmail： smtp.gmail.com ，使用应用专用密码