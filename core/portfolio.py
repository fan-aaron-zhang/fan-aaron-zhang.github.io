"""Read-only Excel ledger and GBP weighted-average cost accounting."""
import math
import unicodedata
from datetime import date, datetime, timedelta
import pandas as pd
from config import EXCLUDED_SHEETS, TRADE_ACTIONS, QTY_TOLERANCE


def numeric(value):
    if value is None or isinstance(value, bool) or pd.isna(value):
        return None
    try:
        cleaned = "".join(c for c in str(value) if unicodedata.category(c) != "Cf")
        cleaned = cleaned.replace(",", "").replace("£", "").replace("$", "").strip()
        result = float(cleaned)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None

def parse_date(value):
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.date()
    if isinstance(value, date):
        return value
    number = numeric(value)
    if number is not None and 30000 < number < 80000:
        return (datetime(1899, 12, 30) + timedelta(days=number)).date()
    try:
        parsed = pd.to_datetime(str(value), errors="coerce", dayfirst=False)
        return None if pd.isna(parsed) else parsed.date()
    except (TypeError, ValueError):
        return None

def get_cell(frame, row, col):
    if row >= len(frame) or col >= frame.shape[1]:
        return None
    return frame.iat[row, col]

def analyse_sheet(name, frame, as_of):
    reported_shares = numeric(get_cell(frame, 1, 2))
    reported_unit_cost = numeric(get_cell(frame, 1, 3))
    reported_value_gbp = numeric(get_cell(frame, 1, 6))
    account_type = get_cell(frame, 1, 1)
    records, issues = [], []
    for idx in range(2, len(frame)):
        action_raw = get_cell(frame, idx, 1)
        action = str(action_raw).strip().upper() if pd.notna(action_raw) else ""
        if action not in TRADE_ACTIONS:
            continue
        row_num = idx + 1
        qty = numeric(get_cell(frame, idx, 2))
        trans_date = parse_date(get_cell(frame, idx, 0))
        amount = numeric(get_cell(frame, idx, 6))
        price = numeric(get_cell(frame, idx, 5))
        opening_unit_cost = numeric(get_cell(frame, idx, 3))
        if qty is None or qty <= 0:
            issues.append(f"Row {row_num}: {action} invalid share quantity")
            continue
        if trans_date is None:
            issues.append(f"Row {row_num}: {action} missing/invalid date — excluded from cost accounting")
            continue
        if trans_date > as_of:
            issues.append(f"Row {row_num}: future transaction dated {trans_date} — excluded")
            continue
        if amount is None or amount < 0:
            issues.append(f"Row {row_num}: {action} has missing/invalid GBP transaction amount (column G)")
        if action == "OPEN" and (amount is None or amount <= 0):
            # Explicit opening book value fallback only (D is unit cost, not a trade price).
            if opening_unit_cost is not None and opening_unit_cost >= 0:
                amount = opening_unit_cost * qty
                issues.append(f"Row {row_num}: OPEN cost derived from column D × shares; confirm opening book value")
        records.append({
            "Excel row": row_num, "Date": trans_date, "Action": action,
            "Shares": qty, "Price (local)": price, "Amount GBP": amount,
        })

    # Workbook transaction history is generally in reverse chronological order.
    # For equal dates: higher physical row is earlier as a deterministic heuristic.
    records.sort(key=lambda r: (r["Date"], -r["Excel row"]))
    shares, book_cost, realised, realised_complete = 0.0, 0.0, 0.0, True
    audit = []
    blocked = False
    for r in records:
        qty, amt, action = r["Shares"], r["Amount GBP"], r["Action"]
        current_cost = book_cost / shares if shares > QTY_TOLERANCE else None
        allocated_cost, gain = None, None
        note = ""
        if blocked:
            note = "Not calculated after cost ledger failure"
        elif action == "OPEN":
            if amt is None:
                blocked = True
                note = "Missing opening book value"
            elif shares > QTY_TOLERANCE:
                # Do not silently treat a second OPEN as a normal BUY.
                blocked = True
                note = "OPEN after existing position; investigate opening balances"
            else:
                shares += qty
                book_cost += amt
        elif action == "BUY":
            if amt is None:
                blocked = True
                note = "Missing actual GBP purchase amount"
            else:
                shares += qty
                book_cost += amt
        else:  # SELL
            if shares + QTY_TOLERANCE < qty:
                blocked = True
                note = f"Sell exceeds available position ({shares:.8f} shares)"
            else:
                allocated_cost = (book_cost / shares) * qty if shares > 0 else None
                if allocated_cost is None:
                    blocked = True
                    note = "No preceding cost-bearing holding"
                else:
                    shares -= qty
                    book_cost -= allocated_cost
                    if shares < QTY_TOLERANCE:
                        shares, book_cost = 0.0, 0.0
                    if amt is not None:
                        gain = amt - allocated_cost
                        realised += gain
                    else:
                        realised_complete = False
                        note = "Sale proceeds missing; realised P/L incomplete"
        if note:
            issues.append(f"Row {r['Excel row']}: {note}")
        audit.append({
            "Date": r["Date"].isoformat(), "Excel row": r["Excel row"],
            "Action": action, "Shares traded": qty,
            "Trade price (local)": r["Price (local)"],
            "Cash flow GBP": (-amt if amt is not None and action == "BUY" else amt),
            "Cost removed GBP": allocated_cost,
            "Realised P/L GBP": gain,
            "Running shares": shares if not blocked else None,
            "Running cost GBP": book_cost if not blocked else None,
            "Note": note,
        })
    if blocked:
        calculated, total_cost, avg_cost, realised_out = None, None, None, None
        status = "REVIEW"
    else:
        calculated = round(shares, 8)
        total_cost = book_cost
        avg_cost = (book_cost / shares) if shares > QTY_TOLERANCE else 0.0
        realised_out = realised if realised_complete else None
        if reported_shares is None:
            status = "NO SUMMARY"
        elif abs(calculated - reported_shares) <= QTY_TOLERANCE:
            status = "MATCH"
        else:
            status = "MISMATCH"
    summary = {
        "Stock / account": name,
        "Account type": str(account_type) if pd.notna(account_type) else "",
        "Summary shares": reported_shares,
        "Calculated shares": calculated,
        "Difference": calculated - reported_shares if calculated is not None and reported_shares is not None else None,
        "Status": status,
        "Avg cost GBP/share": avg_cost,
        "Remaining cost GBP": total_cost,
        "Realised P/L GBP": realised_out,
        "Excel avg cost GBP/share": reported_unit_cost,
        "Excel value GBP (snapshot)": reported_value_gbp,
        "Trade rows": len(records),
    }
    return summary, audit, issues

def read_cash_from_summary(workbook):
    if "Summary" not in workbook.sheet_names:
        return None, "Summary worksheet is missing"
    frame = pd.read_excel(workbook, sheet_name="Summary", header=None)
    matches = []
    for i in range(len(frame)):
        label = get_cell(frame, i, 0)
        if isinstance(label, str) and label.strip().casefold() == "cash":
            matches.append(i)
    if len(matches) != 1:
        return None, f"Expected exactly one 'Cash' label in Summary column A; found {len(matches)}"
    row = matches[0]
    value = numeric(get_cell(frame, row, 6))  # Summary column G
    if value is None or value < 0:
        return None, f"Summary!G{row+1} is missing or not a valid nonnegative GBP balance"
    return value, f"Summary!G{row+1}"

def classify_account(name, account_type):
    typ = str(account_type).strip().upper()
    if name == "VWRP (HL-Junior ISA)" or "ALAN" in typ or "JUNIOR" in typ:
        return "Junior ISA"
    if name in {"VWRP (T212 ISA)", "HSBC-ETF"} or typ == "ETF":
        return "Core ETF"
    if typ == "SWING":
        return "Swing"
    return "Unclassified"

