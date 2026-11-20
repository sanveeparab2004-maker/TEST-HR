import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from backend.app.core.config import settings

logger = logging.getLogger("sheets_service")

_sheets_service_instance = None
_sheets_initialized = False

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = {
    "Attempts": [
        "attempt_id", "candidate_id", "name", "email_or_phone", "department",
        "start_time", "end_time", "status", "restart_count", "tab_switch_total",
        "face_violation_total", "score", "total_marks", "question_order", "option_order"
    ],
    "Answers": [
        "attempt_id", "candidate_id", "question_id", "selected_answer",
        "correct_answer", "is_correct", "marks_awarded", "answered_at"
    ],
    "Violations": [
        "timestamp", "attempt_id", "candidate_id", "type", "warning_number", "action"
    ],
    "Restarts": [
        "timestamp", "attempt_id", "candidate_id", "reason", "restart_number"
    ],
    "All Results": [
        "attempt_id", "candidate_id", "name", "department", "score",
        "total_marks", "percentage", "status", "rank_dept", "rank_overall",
        "time_taken_minutes", "violations_total", "restarts_total", "submitted_at"
    ],
    "Question Bank": [
        "question_id", "department", "question_text", "option_a",
        "option_b", "option_c", "option_d", "correct_option", "marks"
    ],
    "Config": [
        "Key", "Value", "Description", "Last Updated"
    ]
}


def get_sheets_service():
    """Build and return an authorized Google Sheets API v4 service instance.
    Falls back gracefully to None if credentials are not configured."""
    global _sheets_service_instance
    if _sheets_service_instance is not None:
        return _sheets_service_instance

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        logger.warning("google-api-python-client or google-auth not installed; running in mock mode.")
        return None

    creds = None
    if settings.GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
    elif settings.GOOGLE_SERVICE_ACCOUNT_FILE and os.path.exists(settings.GOOGLE_SERVICE_ACCOUNT_FILE):
        try:
            creds = service_account.Credentials.from_service_account_file(settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Failed to load GOOGLE_SERVICE_ACCOUNT_FILE: {e}")

    if not creds:
        app_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if app_cred and os.path.exists(app_cred):
            try:
                creds = service_account.Credentials.from_service_account_file(app_cred, scopes=SCOPES)
            except Exception as e:
                logger.error(f"Failed to load GOOGLE_APPLICATION_CREDENTIALS: {e}")

    if creds:
        try:
            _sheets_service_instance = build("sheets", "v4", credentials=creds, cache_discovery=False)
            logger.info("Google Sheets API service connected successfully.")
            return _sheets_service_instance
        except Exception as e:
            logger.error(f"Failed to build Google Sheets service: {e}")
            return None

    logger.info("No Google Service Account configured. Running in mock/dry-run logging mode.")
    return None


def execute_with_retry(request_callable, max_retries: int = 5, initial_backoff: float = 1.0):
    """Execute a Google Sheets API call with exponential backoff."""
    retries = 0
    backoff = initial_backoff
    last_exc = None
    while retries < max_retries:
        try:
            return request_callable()
        except Exception as e:
            last_exc = e
            retries += 1
            if retries >= max_retries:
                logger.error(f"Google Sheets API call failed after {max_retries} attempts: {e}")
                raise e
            time.sleep(backoff)
            backoff *= 2
    raise last_exc


def ensure_sheet_tabs_and_headers(sheet_id: Optional[str] = None) -> bool:
    """Ensure all required tabs exist with standardized headers, formatting and dashboard formulas."""
    global _sheets_initialized
    sheet_id = sheet_id or settings.GOOGLE_SHEET_ID
    if not sheet_id:
        return False

    service = get_sheets_service()
    if not service:
        _sheets_initialized = True
        return True

    try:
        spreadsheet = execute_with_retry(
            lambda: service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        )
        existing_sheets = {s["properties"]["title"]: s["properties"]["sheetId"] for s in spreadsheet.get("sheets", [])}

        requests = []
        required_tabs = ["Dashboard", "All Results", "Attempts", "Answers", "Violations", "Restarts", "Question Bank", "Config"]
        for dept in settings.DEPARTMENTS:
            required_tabs.append(f"Dept - {dept}")

        for tab_name in required_tabs:
            if tab_name not in existing_sheets:
                requests.append({
                    "addSheet": {
                        "properties": {
                            "title": tab_name,
                            "gridProperties": {
                                "rowCount": 1000,
                                "columnCount": 26,
                                "frozenRowCount": 1 if tab_name != "Dashboard" else 0
                            }
                        }
                    }
                })

        if requests:
            execute_with_retry(
                lambda: service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={"requests": requests}
                ).execute()
            )
            spreadsheet = execute_with_retry(
                lambda: service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            )
            existing_sheets = {s["properties"]["title"]: s["properties"]["sheetId"] for s in spreadsheet.get("sheets", [])}

        # Populate headers where missing
        value_updates = []
        for tab_name, header_cols in HEADERS.items():
            if tab_name in existing_sheets:
                value_updates.append({
                    "range": f"'{tab_name}'!A1:{chr(64 + len(header_cols))}1",
                    "values": [header_cols]
                })

        for dept in settings.DEPARTMENTS:
            dept_tab = f"Dept - {dept}"
            if dept_tab in existing_sheets:
                header_cols = HEADERS["All Results"]
                value_updates.append({
                    "range": f"'{dept_tab}'!A1:{chr(64 + len(header_cols))}1",
                    "values": [header_cols]
                })

        # Config tab default values
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        config_rows = [
            ["TOTAL_MARKS", str(settings.TOTAL_MARKS), "Total exam marks", now_str],
            ["PASS_MARKS", str(settings.PASS_MARKS), "Minimum passing mark", now_str],
            ["TEST_DURATION_MINUTES", str(settings.EXAM_DURATION_MINUTES), "Strict exam duration", now_str],
            ["MAX_TAB_WARNINGS", str(settings.MAX_TAB_WARNINGS), "Maximum allowed tab switch warnings", now_str],
            ["MAX_FACE_WARNINGS", str(settings.MAX_FACE_WARNINGS), "Maximum allowed face warnings", now_str],
            ["FACE_MISSING_SECONDS", str(settings.FACE_MISSING_SECONDS), "Seconds before missing face triggers warning", now_str],
            ["FACE_MATCH_THRESHOLD", str(settings.FACE_MATCH_THRESHOLD), "Face descriptor distance threshold", now_str],
            ["NEGATIVE_MARKING", str(settings.NEGATIVE_MARKING), "Deductions per incorrect answer", now_str],
            ["DEPARTMENTS", ",".join(settings.DEPARTMENTS), "Active participating departments", now_str]
        ]
        value_updates.append({
            "range": "'Config'!A2:D10",
            "values": config_rows
        })

        # Dashboard Tab Setup with Live Formulas
        dashboard_content = [
            ["ONLINE ASSESSMENT DASHBOARD – EXECUTIVE SUMMARY", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", ""],
            ["KEY PERFORMANCE INDICATORS", "", "", "", "", "", "", ""],
            ["Total Attempts", "Passed", "Failed", "Pass Rate %", "Average Score", "Highest Score", "Total Violations", "Total Restarts"],
            [
                "=COUNTA('All Results'!A2:A)",
                '=COUNTIF(\'All Results\'!H2:H, "PASS")',
                '=COUNTIF(\'All Results\'!H2:H, "FAIL")',
                '=IF(A4>0, ROUND((B4/A4)*100, 1), 0)',
                "=IFERROR(ROUND(AVERAGE('All Results'!E2:E), 1), 0)",
                "=IFERROR(MAX('All Results'!E2:E), 0)",
                "=IFERROR(SUM('All Results'!L2:L), 0)",
                "=IFERROR(SUM('All Results'!M2:M), 0)"
            ],
            ["", "", "", "", "", "", "", ""],
            ["DEPARTMENT PERFORMANCE BREAKDOWN", "", "", "", "", "", "", ""],
            ["Department", "Attempted", "Passed", "Failed", "Pass %", "Average Score", "Top Score", "Violations"]
        ]

        row_offset = 9
        for dept in settings.DEPARTMENTS:
            r = row_offset
            dashboard_content.append([
                dept,
                f'=COUNTIF(\'All Results\'!D2:D, "{dept}")',
                f'=COUNTIFS(\'All Results\'!D2:D, "{dept}", \'All Results\'!H2:H, "PASS")',
                f'=COUNTIFS(\'All Results\'!D2:D, "{dept}", \'All Results\'!H2:H, "FAIL")',
                f'=IF(B{r}>0, ROUND((C{r}/B{r})*100, 1), 0)',
                f'=IFERROR(ROUND(AVERAGEIFS(\'All Results\'!E2:E, \'All Results\'!D2:D, "{dept}"), 1), 0)',
                f'=IFERROR(MAXIFS(\'All Results\'!E2:E, \'All Results\'!D2:D, "{dept}"), 0)',
                f'=IFERROR(SUMIFS(\'All Results\'!L2:L, \'All Results\'!D2:D, "{dept}"), 0)'
            ])
            row_offset += 1

        value_updates.append({
            "range": "'Dashboard'!A1:H25",
            "values": dashboard_content
        })

        if value_updates:
            execute_with_retry(
                lambda: service.spreadsheets().values().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={"valueInputOption": "USER_ENTERED", "data": value_updates}
                ).execute()
            )

        # Apply header styling (#1F3864 dark blue background, bold white text)
        style_requests = []
        for tab_name, sheet_id_num in existing_sheets.items():
            if tab_name == "Dashboard":
                style_requests.append({
                    "repeatCell": {
                        "range": {"sheetId": sheet_id_num, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 8},
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 31/255, "green": 56/255, "blue": 100/255},
                                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 14},
                                "horizontalAlignment": "CENTER"
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                })
                style_requests.append({
                    "repeatCell": {
                        "range": {"sheetId": sheet_id_num, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 0, "endColumnIndex": 8},
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 44/255, "green": 62/255, "blue": 80/255},
                                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10},
                                "horizontalAlignment": "CENTER"
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                })
                continue

            cols_count = len(HEADERS.get(tab_name, HEADERS["All Results"]))
            style_requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id_num,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": cols_count
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 31/255, "green": 56/255, "blue": 100/255},
                            "textFormat": {
                                "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                                "bold": True,
                                "fontSize": 10
                            },
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
                }
            })

            if "Results" in tab_name or "Dept" in tab_name:
                style_requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": sheet_id_num, "startRowIndex": 1, "endRowIndex": 1000, "startColumnIndex": 7, "endColumnIndex": 8}],
                            "booleanRule": {
                                "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": "PASS"}]},
                                "format": {
                                    "backgroundColor": {"red": 226/255, "green": 239/255, "blue": 218/255},
                                    "textFormat": {"foregroundColor": {"red": 55/255, "green": 86/255, "blue": 35/255}, "bold": True}
                                }
                            }
                        },
                        "index": 0
                    }
                })
                style_requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": sheet_id_num, "startRowIndex": 1, "endRowIndex": 1000, "startColumnIndex": 7, "endColumnIndex": 8}],
                            "booleanRule": {
                                "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": "FAIL"}]},
                                "format": {
                                    "backgroundColor": {"red": 252/255, "green": 228/255, "blue": 214/255},
                                    "textFormat": {"foregroundColor": {"red": 198/255, "green": 89/255, "blue": 17/255}, "bold": True}
                                }
                            }
                        },
                        "index": 1
                    }
                })

        if style_requests:
            try:
                execute_with_retry(
                    lambda: service.spreadsheets().batchUpdate(
                        spreadsheetId=sheet_id,
                        body={"requests": style_requests}
                    ).execute()
                )
            except Exception as e:
                logger.warning(f"Styling requests partially applied: {e}")

        _sheets_initialized = True
        return True
    except Exception as e:
        logger.error(f"Error ensuring sheet tabs: {e}")
        return False


def append_rows_idempotent(tab_name: str, rows: List[List[Any]], sheet_id: Optional[str] = None) -> bool:
    """Appends rows to the specified tab with retry and error handling."""
    if not rows:
        return True

    sheet_id = sheet_id or settings.GOOGLE_SHEET_ID
    service = get_sheets_service()
    if not service or not sheet_id:
        logger.info(f"[MOCK SHEETS] Appended {len(rows)} rows to tab '{tab_name}'.")
        return True

    try:
        range_target = f"'{tab_name}'!A1"
        execute_with_retry(
            lambda: service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range=range_target,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": rows}
            ).execute()
        )
        return True
    except Exception as e:
        logger.error(f"Failed to append to '{tab_name}': {e}")
        raise e


def queue_or_write_sheet(db, operation: str, idempotency_key: str, payload: Dict[str, Any], attempt_id: Optional[int] = None) -> bool:
    """Attempt direct write to Google Sheets. If fails or service is unavailable,
    durable record is stored in pending_sheet_writes table for background drain."""
    from backend.app.models.models import PendingSheetWrite

    existing = db.query(PendingSheetWrite).filter_by(idempotency_key=idempotency_key).first()
    if existing and existing.status == "COMPLETED":
        return True

    success = False
    last_error = None
    try:
        if operation == "append_attempt":
            success = append_rows_idempotent("Attempts", [payload["row"]])
        elif operation == "append_answers":
            success = append_rows_idempotent("Answers", payload["rows"])
        elif operation == "append_violation":
            success = append_rows_idempotent("Violations", [payload["row"]])
        elif operation == "append_restart":
            success = append_rows_idempotent("Restarts", [payload["row"]])
        elif operation == "sync_all_results":
            success = append_rows_idempotent("All Results", [payload["row"]])
            dept = payload.get("department")
            if dept:
                append_rows_idempotent(f"Dept - {dept.upper()}", [payload["row"]])
        elif operation == "sync_question_bank":
            success = append_rows_idempotent("Question Bank", payload["rows"])
    except Exception as e:
        success = False
        last_error = str(e)
        logger.warning(f"Live sheet write '{operation}' failed ({e}). Queuing to pending_sheet_writes.")

    status = "COMPLETED" if success else "PENDING"

    if existing:
        existing.status = status
        existing.retries = existing.retries + 1 if not success else existing.retries
        existing.last_error = last_error
        existing.updated_at = datetime.now(timezone.utc)
    else:
        pending_record = PendingSheetWrite(
            attempt_id=attempt_id,
            operation=operation,
            idempotency_key=idempotency_key,
            payload=payload,
            retries=0 if success else 1,
            max_retries=10,
            status=status,
            last_error=last_error,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(pending_record)

    db.commit()
    return success


def process_pending_sheet_writes(db, limit: int = 50) -> int:
    """Drain pending writes in background."""
    from backend.app.models.models import PendingSheetWrite

    pending_items = db.query(PendingSheetWrite).filter(
        PendingSheetWrite.status.in_(["PENDING", "FAILED"]),
        PendingSheetWrite.retries < PendingSheetWrite.max_retries
    ).order_by(PendingSheetWrite.id.asc()).limit(limit).all()

    processed = 0
    for item in pending_items:
        try:
            payload = item.payload
            op = item.operation
            success = False
            if op == "append_attempt":
                success = append_rows_idempotent("Attempts", [payload["row"]])
            elif op == "append_answers":
                success = append_rows_idempotent("Answers", payload["rows"])
            elif op == "append_violation":
                success = append_rows_idempotent("Violations", [payload["row"]])
            elif op == "append_restart":
                success = append_rows_idempotent("Restarts", [payload["row"]])
            elif op == "sync_all_results":
                success = append_rows_idempotent("All Results", [payload["row"]])
                dept = payload.get("department")
                if dept:
                    append_rows_idempotent(f"Dept - {dept.upper()}", [payload["row"]])
            elif op == "sync_question_bank":
                success = append_rows_idempotent("Question Bank", payload["rows"])

            if success:
                item.status = "COMPLETED"
                item.last_error = None
                processed += 1
            else:
                item.retries += 1
                item.last_error = "Write failed without exception"
        except Exception as e:
            item.retries += 1
            item.last_error = str(e)
            if item.retries >= item.max_retries:
                item.status = "FAILED"

        item.updated_at = datetime.now(timezone.utc)
        db.commit()

    return processed
