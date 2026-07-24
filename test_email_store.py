
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.email_store import EmailStore

TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_emails.db")
RESULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result.txt")
TEST_ACCOUNT = "store.test@example.com"

results = []
passed = 0
failed = 0


# Record one test result.
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
    # Write one loaded email to the result file.
    if fields is None:
        fields = ["uid", "subject", "sender", "from", "recipient", "to",
                   "date_display", "snippet", "body_text", "is_full"]
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
    # Write the loaded email list to the result file.
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


# Write loaded attachments to the result file.
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
    # Start each test run with a clean database.
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    store = EmailStore(TEST_ACCOUNT, db_path=TEST_DB_PATH)
    results.append("== EmailStore save/load test ==")
    results.append(f"DB file: {TEST_DB_PATH}\n")

    # Test saving and loading inbox pages.
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

    # Test full email and attachment storage.
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

    # Test saved email search behavior.
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

        flexible_email = [{
            "uid": "103",
            "subject": "I Care reimbursement update",
            "from": "support@icare.example",
            "to": "member@example.com",
            "date": "2026-07-22T08:00:00",
            "date_display": "2026-07-22 08:00",
            "snippet": "Your claim is ready for review.",
        }]
        store.save_page("INBOX", flexible_email, source="search-test")
        compact = store.search_emails("INBOX", "icare")
        check("search flexible spacing: 'icare' nakita ang 'I Care'",
              any(e["uid"] == "103" for e in compact["emails"]))

        spaced = store.search_emails("INBOX", "i care")
        check("search flexible spacing: 'i care' nakita ang 'icare'",
              any(e["uid"] == "103" for e in spaced["emails"]))

        from_filter = store.search_emails("INBOX", "from:support@icare.example")
        check("search from: filter gumagana",
              any(e["uid"] == "103" for e in from_filter["emails"]))

        to_filter = store.search_emails("INBOX", "to:member@example.com claim")
        check("search to: filter + keyword gumagana",
              any(e["uid"] == "103" for e in to_filter["emails"]))

        subject_filter = store.search_emails("INBOX", 'subject:"I Care"')
        check("search subject: filter gumagana",
              any(e["uid"] == "103" for e in subject_filter["emails"]))

        body_search = store.search_emails("INBOX", "salamat")
        check("search body_text ng full/cached email gumagana",
              any(e["uid"] == "101" for e in body_search["emails"]))

        # Do not match a query across unrelated word boundaries.
        store.save_page("SEARCH_REGRESSION", [
            {
                "uid": "201",
                "subject": "Your move, Robert Jay",
                "from": "messages-noreply@linkedin.com",
                "to": "member@example.com",
                "date": "2026-07-23T08:00:00",
                "date_display": "2026-07-23 08:00",
                "snippet": "LinkedIn puzzle update",
            },
            {
                "uid": "202",
                "subject": "Discover one useful feature",
                "from": "newsletter@example.com",
                "to": "member@example.com",
                "date": "2026-07-23T07:00:00",
                "date_display": "2026-07-23 07:00",
                "snippet": "Product newsletter",
            },
            {
                "uid": "203",
                "subject": "Message from Veronica",
                "from": "Vero <vero@example.com>",
                "to": "member@example.com",
                "date": "2026-07-23T06:00:00",
                "date_display": "2026-07-23 06:00",
                "snippet": "Actual Vero match",
            },
        ], source="search-boundary-test")
        vero_search = store.search_emails("SEARCH_REGRESSION", "vero")
        vero_uids = {e["uid"] for e in vero_search["emails"]}
        check("search word-boundary: 'vero' hindi tumama sa 'move Robert'",
              "201" not in vero_uids, f"found_uids={sorted(vero_uids)}")
        check("search word-boundary: 'vero' hindi tumama sa 'discover one'",
              "202" not in vero_uids, f"found_uids={sorted(vero_uids)}")
        check("search word-boundary: tunay na Vero/Veronica nakita pa rin",
              "203" in vero_uids, f"found_uids={sorted(vero_uids)}")
    except Exception as e:
        check("search_emails() block", False, f"exception: {e}")
        traceback.print_exc()

    # Confirm that the same UID updates instead of creating a duplicate.
    try:
        updated_page = [dict(sample_page[0])]
        updated_page[0]["subject"] = "Meeting bukas (UPDATED)"
        store.save_page("INBOX", updated_page, source="test-update")
        page_after = store.get_page("INBOX", limit=10, offset=0)
        check("save_page() upsert: total email count hindi tumaas (walang duplicate)",
              page_after["total"] == 3, f"actual={page_after['total']}")
        updated = store.get_email("INBOX", "101")
        check("save_page() upsert: subject na-update", updated["subject"] == "Meeting bukas (UPDATED)")

        store.mark_sync_started("INBOX")
        state_started = store.get_sync_state("INBOX")
        check("sync_state: started ay incomplete",
              state_started is not None and state_started["full_sync_complete"] == 0)
        store.mark_sync_complete("INBOX", remote_total=3, synced_count=3)
        state_complete = store.get_sync_state("INBOX")
        check("sync_state: completion naka-persist",
              state_complete is not None
              and state_complete["full_sync_complete"] == 1
              and state_complete["remote_total"] == 3)
    except Exception as e:
        check("upsert block", False, f"exception: {e}")
        traceback.print_exc()

    store.close()

    # Confirm that data remains after reopening the database.
    try:
        store2 = EmailStore(TEST_ACCOUNT, db_path=TEST_DB_PATH)
        reloaded_page = store2.get_page("INBOX", limit=10, offset=0)
        check("PERSISTENCE: bagong koneksyon nakikita ang 3 naka-save na email",
              reloaded_page["total"] == 3, f"actual={reloaded_page['total']}")

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

    # Write the final test summary.
    results.append("")
    results.append(f"SUMMARY: {passed} PASSED, {failed} FAILED (total {passed + failed})")
    overall = "ALL TESTS PASSED" if failed == 0 else f"{failed} TEST(S) FAILED"
    results.append(overall)

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(results) + "\n")

    print(f"\n{overall}")
    print(f"Resulta na-save sa: {RESULT_PATH}")

    # Remove the temporary test database.
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


if __name__ == "__main__":
    main()
