import qiangua_upload_server as server


def test_normalize_date_route():
    assert server.parse_date_from_path("/insights/2026-07-02") == "2026-07-02"
    assert server.parse_date_from_path("/dashboard?date=2026-07-02") == "2026-07-02"


def test_upload_page_paths():
    assert server.is_upload_page_path("/")
    assert server.is_upload_page_path("/index.html")
    assert server.is_upload_page_path("/upload")
    assert not server.is_upload_page_path("/upload/history")
