import qiangua_upload_server as server


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
