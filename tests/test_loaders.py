from life4.data.loaders import GoogleSheetLoader


def test_builds_the_documented_export_url():
    loader = GoogleSheetLoader(doc_id="ABC123")
    assert loader.csv_url(638900183) == (
        "https://docs.google.com/spreadsheets/d/ABC123/export?format=csv&gid=638900183"
    )


def test_url_does_not_use_the_gviz_endpoint():
    # gviz honours the sheet's filter view; it returned 3,415 of the WORLD
    # tab's 10,821 rows because that tab is filtered to singles, level 8+.
    assert "gviz" not in GoogleSheetLoader(doc_id="ABC123").csv_url(0)
