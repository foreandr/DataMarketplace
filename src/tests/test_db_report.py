from __future__ import annotations


def test_db_report_runs() -> None:
    from report import db_report

    db_report.main()
