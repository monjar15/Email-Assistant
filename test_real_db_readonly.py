
import os
import shutil
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.email_store import EmailStore

# Set this to the real storage/emails.db path before running the test.
REAL_DB_PATH = "D:\\Python\\email_prj\\email_assistant\\Email-Assistant\\storage\\emails.db"

COPY_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "_real_db_test_copy.db"
)
RESULT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "result_real_db.txt"
)

# Use a fake UID that should not match a real email.
FAKE_TEST_UID = "TEST_UID_999999999"

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


# Write loaded emails to the result file.
def show_email_list(title, emails, limit=10):
    results.append(f"    >>> {title} ({len(emails)} email, showing max {limit})")
    if not emails:
        results.append("        (walang laman)")
        return
    for e in emails[:limit]:
        sender = e.get("sender", e.get("from", ""))
        results.append(
            f"        uid={e.get('uid')} | {e.get('date_display', '')} | "
            f"from: {sender} | subject: {e.get('subject', '')}"
        )


# Test a safe copy of the real email database.
def main():
    results.append("== EmailStore test gamit ang TOTOONG emails.db (safe copy) ==")

    # Confirm that the real database file exists.
    if not os.path.exists(REAL_DB_PATH):
        msg = (
            f"HINDI NAKITA ang REAL_DB_PATH: {REAL_DB_PATH}\n"
            f"Palitan ang variable na REAL_DB_PATH sa taas ng script na ito, "
            f"itapat sa totoong lokasyon ng emails.db mo."
        )
        print(msg)
        results.append(msg)
        with open(RESULT_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(results) + "\n")
        return

    # Copy the database so the original file stays unchanged.
    if os.path.exists(COPY_DB_PATH):
        os.remove(COPY_DB_PATH)
    shutil.copy2(REAL_DB_PATH, COPY_DB_PATH)
    results.append(f"Orihinal (HINDI GINALAW): {REAL_DB_PATH}")
    results.append(f"Ligtas na kopya (ito ang tinetestingan): {COPY_DB_PATH}\n")

    store = EmailStore(TEST_ACCOUNT, db_path=COPY_DB_PATH)

    # Load real inbox data from the copied database.
    try:
        page = store.get_page("INBOX", limit=10, offset=0)
        check("get_page() nabuksan ang copy nang walang error", True)
        check("get_page() may nakuhang total count", page["total"] >= 0,
              f"total={page['total']}")
        show_email_list(
            "TOTOONG DATA - unang 10 email mula sa copy ng emails.db mo",
            page["emails"], limit=10,
        )
    except Exception as e:
        check("LOAD test sa totoong data", False, f"exception: {e}")
        traceback.print_exc()

    # Test save and load using a fake UID in the copied database.
    try:
        fake_email = [{
            "uid": FAKE_TEST_UID,
            "subject": "[TEST ONLY] Safe round-trip check",
            "from": "test@example.com",
            "to": "test@example.com",
            "date": "2026-07-22T00:00:00",
            "date_display": "2026-07-22 00:00",
            "snippet": "Ito ay fake test entry lang, awtomatikong tatanggalin.",
        }]
        store.save_page("INBOX", fake_email, source="round-trip-test")
        loaded = store.get_email("INBOX", FAKE_TEST_UID)
        check("SAVE+LOAD round-trip gamit ang fake uid gumana",
              loaded is not None and loaded["subject"] == fake_email[0]["subject"])

        # Remove the fake row from the copied database.
        store.conn.execute(
            "DELETE FROM emails WHERE account_id=? AND folder=? AND uid=?",
            (store.account_id, "INBOX", FAKE_TEST_UID)
        )
        store.conn.commit()
        cleanup_check = store.get_email("INBOX", FAKE_TEST_UID)
        check("Fake test row na-clean up sa copy", cleanup_check is None)
    except Exception as e:
        check("Safe round-trip test", False, f"exception: {e}")
        traceback.print_exc()

    store.close()

    # Write the final test summary.
    results.append("")
    results.append(f"SUMMARY: {passed} PASSED, {failed} FAILED (total {passed + failed})")
    overall = "ALL TESTS PASSED" if failed == 0 else f"{failed} TEST(S) FAILED"
    results.append(overall)

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(results) + "\n")

    print(f"\n{overall}")
    print(f"Resulta na-save sa: {RESULT_PATH}")

    # Delete the temporary database copy.
    if os.path.exists(COPY_DB_PATH):
        os.remove(COPY_DB_PATH)
    print(f"Tinanggal na ang temporary copy: {COPY_DB_PATH}")
    print(f"Ang orihinal ay HINDI GINALAW: {REAL_DB_PATH}")


if __name__ == "__main__":
    main()
