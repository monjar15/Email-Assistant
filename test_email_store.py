"""
Test script para sa EmailStore (storage/email_store.py).

Sinusubukan dito:
  1. save_page()      -> pag-save ng listahan ng emails (header-level lang)
  2. get_page()        -> pagbabasa ulit ng listahan (dapat parehas sa na-save)
  3. save_full()       -> pag-save ng buong email (may body na + attachments)
  4. get_email()        -> pagkuha ng isang buong email
  5. get_attachments() -> pagkuha ng mga attachment ng isang email
  6. search_emails()   -> paghahanap gamit ang subject/sender
  7. mark_read()       -> pag-mark ng isang email bilang nabasa na
  8. "reload" test     -> bagong EmailStore instance na tumuturo sa parehong
                          .db file, para masigurong naka-persist talaga sa disk
                          (hindi lang laman ng memory).

Lahat ng resulta (PASS/FAIL bawat check + buod sa dulo) ay isusulat sa
result.txt sa parehong folder ng script na ito.
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.email_store import EmailStore

TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_emails.db")
RESULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result.txt")

results = []
passed = 0
failed = 0


def check(label, condition, extra=""):
    global passed, failed
    status = "PASS" if condition else "FAIL"
    if condition:
        passed += 1
    else:
        failed += 1
    line = f"[{status}] {label}"
    if extra:
        line += f" -- {extra}"
    results.append(line)
    print(line)


def show_email(title, email_dict, fields=None):
    """Isulat sa result.txt ang ACTUAL na laman ng isang na-loadf na email,
    hindi lang pass/fail, para makita mismo ang datos."""
    if fields is None:
        fields = ["uid", "subject", "sender", "from", "recipient", "to",
                   "date_display", "snippet", "body_text", "is_full", "is_read"]
    results.append(f"    >>> {title}")
    if email_dict is None:
        results.append("        (walang nakuhang email)")
        return
    for f in fields:
        if f in email_dict:
            value = email_dict[f]
            if isinstance(value, str) and len(value) > 120:
                value = value[:120] + "...(pinutol)"
            results.append(f"        {f}: {value}")


def show_email_list(title, emails):
    """Isulat sa result.txt ang ACTUAL na listahan ng na-loadng emails
    (parang tinitingnan ang inbox list view)."""
    results.append(f"    >>> {title} ({len(emails)} email)")
    if not emails:
        results.append("        (walang laman)")
        return
    for e in emails:
        sender = e.get("sender", e.get("from", ""))
        results.append(
            f"        uid={e.get('uid')} | {e.get('date_display', '')} | "
            f"from: {sender} | subject: {e.get('subject', '')}"
        )


def show_attachments(title, attachments):
    results.append(f"    >>> {title} ({len(attachments)} attachment)")
    if not attachments:
        results.append("        (walang attachment)")
        return
    for a in attachments:
        data_len = len(a["data"]) if a.get("data") is not None else 0
        results.append(
            f"        filename={a.get('filename')} | type={a.get('content_type')} | "
            f"size={a.get('size')} bytes | actual_data_length={data_len} bytes"
        )


def main():
    # simula sa malinis na database bawat run
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    store = EmailStore(db_path=TEST_DB_PATH)
    results.append("== EmailStore save/load test ==")
    results.append(f"DB file: {TEST_DB_PATH}\n")

    # ------------------------------------------------------------------
    # 1) save_page() + get_page()
    # ------------------------------------------------------------------
    sample_page = [
        {
            "uid": "101",
            "subject": "Meeting bukas",
            "from": "boss@example.com",
            "to": "me@example.com",
            "date": "2026-07-20T09:00:00",
            "date_display": "2026-07-20 09:00",
            "snippet": "Pakidala ang report bukas ng umaga...",
        },
        {
            "uid": "102",
            "subject": "Invoice #4521",
            "from": "billing@vendor.com",
            "to": "me@example.com",
            "date": "2026-07-21T14:30:00",
            "date_display": "2026-07-21 14:30",
            "snippet": "Attached po ang inyong invoice para sa buwan...",
        },
    ]

    try:
        store.save_page("INBOX", sample_page, source="test")
        page = store.get_page("INBOX", limit=10, offset=0)
        check("save_page() walang error", True)
        check("get_page() nagbalik ng 2 email", len(page["emails"]) == 2,
              f"actual={len(page['emails'])}")
        check("get_page() total count tama", page["total"] == 2,
              f"actual={page['total']}")
        uids = {e["uid"] for e in page["emails"]}
        check("get_page() naglalaman ng uid 101 at 102", uids == {"101", "102"},
              f"actual={uids}")
        newest_first = page["emails"][0]["uid"] == "102"
        check("get_page() naka-order pababa (pinakabago muna)", newest_first,
              f"first_uid={page['emails'][0]['uid']}")

        show_email_list("LOAD RESULT - get_page('INBOX') na-load mula sa database",
                         page["emails"])
    except Exception as e:
        check("save_page()/get_page() block", False, f"exception: {e}")
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 2) save_full() + get_email() + attachments
    # ------------------------------------------------------------------
    full_email = {
        "uid": "101",
        "subject": "Meeting bukas",
        "from": "boss@example.com",
        "to": "me@example.com",
        "date": "2026-07-20T09:00:00",
        "date_display": "2026-07-20 09:00",
        "snippet": "Pakidala ang report bukas ng umaga...",
        "body_text": "Hi, pakidala ang report bukas ng umaga. Salamat!",
        "body_html": "<p>Hi, pakidala ang report bukas ng umaga. Salamat!</p>",
        "attachments": [
            {
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "size": 12345,
                "data": b"%PDF-fake-bytes-for-testing",
            }
        ],
    }

    try:
        store.save_full("INBOX", full_email)
        loaded = store.get_email("INBOX", "101")
        check("save_full() walang error", True)
        check("get_email() nakita ang email", loaded is not None)
        if loaded:
            check("get_email() body_text tama", loaded["body_text"] == full_email["body_text"])
            check("get_email() is_full=1", loaded["is_full"] == 1)
            check("get_email() is_read=1 (auto-mark)", loaded["is_read"] == 1)

        show_email("LOAD RESULT - get_email('INBOX', '101') na-load mula sa database",
                   loaded)

        attachments = store.get_attachments("INBOX", "101")
        check("get_attachments() nagbalik ng 1 attachment", len(attachments) == 1,
              f"actual={len(attachments)}")
        if attachments:
            check("attachment filename tama", attachments[0]["filename"] == "report.pdf")
            check("attachment data tama (bytes match)",
                  bytes(attachments[0]["data"]) == full_email["attachments"][0]["data"])

        show_attachments("LOAD RESULT - get_attachments('INBOX', '101') na-load mula sa database",
                          attachments)
    except Exception as e:
        check("save_full()/get_email()/attachments block", False, f"exception: {e}")
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 3) search_emails()
    # ------------------------------------------------------------------
    try:
        result = store.search_emails("INBOX", "Invoice")
        check("search_emails() nakahanap ng tugma sa subject",
              any(e["uid"] == "102" for e in result["emails"]),
              f"found_uids={[e['uid'] for e in result['emails']]}")

        show_email_list("LOAD RESULT - search_emails('Invoice') na-load mula sa database",
                         result["emails"])

        result2 = store.search_emails("INBOX", "walang-tutugma-dito-xyz")
        check("search_emails() walang resulta sa hindi tugmang query",
              len(result2["emails"]) == 0)
    except Exception as e:
        check("search_emails() block", False, f"exception: {e}")
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 4) mark_read()
    # ------------------------------------------------------------------
    try:
        store.mark_read("INBOX", "102")
        row = store.get_email("INBOX", "102")
        check("mark_read() nag-set ng is_read=1", row is not None and row["is_read"] == 1)
    except Exception as e:
        check("mark_read() block", False, f"exception: {e}")
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 5) UPSERT check - pag-save ulit ng parehong uid ay dapat mag-update
    #    lang, hindi gumawa ng duplicate row
    # ------------------------------------------------------------------
    try:
        updated_page = [dict(sample_page[0])]
        updated_page[0]["subject"] = "Meeting bukas (UPDATED)"
        store.save_page("INBOX", updated_page, source="test-update")
        page_after = store.get_page("INBOX", limit=10, offset=0)
        check("save_page() upsert: total email count hindi tumaas (walang duplicate)",
              page_after["total"] == 2, f"actual={page_after['total']}")
        updated = store.get_email("INBOX", "101")
        check("save_page() upsert: subject na-update", updated["subject"] == "Meeting bukas (UPDATED)")
    except Exception as e:
        check("upsert block", False, f"exception: {e}")
        traceback.print_exc()

    store.close()

    # ------------------------------------------------------------------
    # 6) Persistence test — bagong EmailStore instance, parehong db file,
    #    para masigurong naka-save talaga sa disk (hindi lang sa memory)
    # ------------------------------------------------------------------
    try:
        store2 = EmailStore(db_path=TEST_DB_PATH)
        reloaded_page = store2.get_page("INBOX", limit=10, offset=0)
        check("PERSISTENCE: bagong koneksyon nakikita ang 2 naka-save na email",
              reloaded_page["total"] == 2, f"actual={reloaded_page['total']}")

        show_email_list(
            "LOAD RESULT (bagong koneksyon, parang bagong session) - get_page('INBOX')",
            reloaded_page["emails"])

        reloaded_full = store2.get_email("INBOX", "101")
        check("PERSISTENCE: buong email (body + is_full) naka-save pa rin",
              reloaded_full is not None and reloaded_full["is_full"] == 1)

        show_email(
            "LOAD RESULT (bagong koneksyon) - get_email('INBOX', '101')",
            reloaded_full)

        reloaded_attachments = store2.get_attachments("INBOX", "101")
        check("PERSISTENCE: attachment naka-save pa rin",
              len(reloaded_attachments) == 1)

        show_attachments(
            "LOAD RESULT (bagong koneksyon) - get_attachments('INBOX', '101')",
            reloaded_attachments)

        store2.close()
    except Exception as e:
        check("persistence block", False, f"exception: {e}")
        traceback.print_exc()

    # ------------------------------------------------------------------
    # buod
    # ------------------------------------------------------------------
    results.append("")
    results.append(f"SUMMARY: {passed} PASSED, {failed} FAILED (total {passed + failed})")
    overall = "ALL TESTS PASSED" if failed == 0 else f"{failed} TEST(S) FAILED"
    results.append(overall)

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(results) + "\n")

    print(f"\n{overall}")
    print(f"Resulta na-save sa: {RESULT_PATH}")

    # linisin ang test db
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


if __name__ == "__main__":
    main()
