import qiangua_upload_server as server


def test_normalize_date_route():
    assert server.parse_date_from_path("/insights/2026-07-02") == "2026-07-02"
    assert server.parse_date_from_path("/dashboard?date=2026-07-02") == "2026-07-02"
