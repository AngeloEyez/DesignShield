"""
SSE 即時事件推播端點測試 (SSE Events Endpoint Tests)

驗證 /api/v1/tasks/{task_id}/events 的 Server-Sent Events 串流廣播與歷史回放能力。
"""

import uuid
from backend.app.models.task import DrcTask
from backend.app.models.step_status import StepStatus


def test_sse_events_streaming(client, db_session):
    """測試 SSE 串流推播現有步驟與終端結束事件"""
    task_id = str(uuid.uuid4())
    # 設定任務為 COMPLETED，這會讓 SSE 在推播完步驟與 task_end 事件後安全退出
    task = DrcTask(id=task_id, project_name="SSETestProject", status="COMPLETED")
    step = StepStatus(
        task_id=task_id,
        step_name="PARSE_AND_GRAPH",
        status="COMPLETED",
        log_message="圖譜構建完成 (節點: 1240)"
    )
    db_session.add(task)
    db_session.add(step)
    db_session.commit()

    response = client.get(f"/api/v1/tasks/{task_id}/events")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    content = response.text
    # 驗證包含 step_update 事件
    assert "event: step_update" in content
    assert "PARSE_AND_GRAPH" in content
    assert "圖譜構建完成" in content

    # 驗證包含 task_end 終端事件
    assert "event: task_end" in content
    assert "COMPLETED" in content


def test_sse_events_not_found(client):
    """測試不存在的任務回傳 404"""
    non_existent = str(uuid.uuid4())
    response = client.get(f"/api/v1/tasks/{non_existent}/events")
    assert response.status_code == 404
