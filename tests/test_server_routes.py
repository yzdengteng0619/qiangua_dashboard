import qiangua_upload_server as server
from http.server import ThreadingHTTPServer
from uuid import UUID


def test_normalize_date_route():
    assert server.parse_date_from_path("/insights/2026-07-02") == "2026-07-02"
    assert server.parse_date_from_path("/dashboard?date=2026-07-02") == "2026-07-02"


def test_upload_page_paths():
    assert server.is_upload_page_path("/")
    assert server.is_upload_page_path("/index.html")
    assert server.is_upload_page_path("/upload")
    assert not server.is_upload_page_path("/upload/history")


def test_validate_upload_file_rejects_unknown_qiangua_file(tmp_path):
    path = tmp_path / "bad.xlsx"
    path.write_bytes(b"not a real workbook")

    result = server.validate_upload_file(path)

    assert result["ok"] is False
    assert result["filename"] == "bad.xlsx"
    assert result["sheet_type"] == "unknown"
    assert "未识别的千瓜文件类型" in result["errors"][0]


def test_parse_run_id_from_path():
    assert server.parse_run_id("/runs/42") == 42
    assert server.parse_run_id("/runs/42?x=1") == 42
    assert server.parse_run_id("/runs/not-a-number") is None


def test_generate_task_id_uses_uuid():
    task_id = server.generate_task_id()

    assert task_id.startswith("task_")
    UUID(task_id.removeprefix("task_"))


def test_upload_size_limit_detects_large_request():
    assert server.is_content_too_large(str(server.MAX_UPLOAD_BYTES + 1))
    assert not server.is_content_too_large(str(server.MAX_UPLOAD_BYTES))
    assert not server.is_content_too_large(None)


def test_build_server_uses_threading_http_server():
    httpd = server.build_server("127.0.0.1", 0)
    try:
        assert isinstance(httpd, ThreadingHTTPServer)
    finally:
        httpd.server_close()
