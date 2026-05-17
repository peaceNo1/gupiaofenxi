from fastapi.testclient import TestClient

from gupiaofenxi.web.app import create_app


def test_dashboard_page_renders_ranking_first_view():
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "A 股短线低吸候选仪表盘" in response.text
    assert "数据状态" in response.text
    assert "当前价" in response.text
    assert "低吸区间" in response.text
