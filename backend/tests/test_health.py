"""
健康检查接口测试

测试目标：
  - GET /api/health 返回正确的状态和格式
  - GET / 返回欢迎信息
"""


def test_health_check(client):
    """测试基础健康检查接口"""
    response = client.get("/api/health")

    # 验证状态码
    assert response.status_code == 200

    # 验证响应格式
    data = response.json()
    assert data["code"] == 200
    assert data["message"] == "ok"
    assert data["data"]["status"] == "healthy"
    assert data["data"]["app_name"] == "RSOD Agent Platform"
    assert "version" in data["data"]


def test_root(client):
    """测试根路径欢迎接口"""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data
