"""
Test script para sa EmailStore GAMIT ANG TOTOONG emails.db mo.

LIGTAS ITO -- hindi ginagalaw ang orihinal na file. Ang ginagawa:

  1. Kinokopya muna ang totoong emails.db papunta sa isang temporary
     na copy (ibang filename, ibang lokasyon).
  2. Ang copy lang ang binubuksan at tinetestingan -- hindi na
     nagagalaw pa ang orihinal simula dito.
  3. Ipinapakita sa result.txt ang TOTOONG laman ng inbox mo (galing
     sa copy), para makita mo mismo ang tunay na data.
  4. May safe na SAVE+LOAD round-trip test gamit ang isang FAKE uid
     (malayong-malayo sa totoong email uid range) -- para masubukan
     pa rin kung gumagana ang pag-save, nang hindi nadadamay ang
     kahit anong totoong record mo.
  5. Sa dulo, dine-delete ang temporary copy -- walang naiiwan.

PAANO GAMITIN:
  1. Baguhin ang REAL_DB_PATH sa ibaba, itapat sa totoong lokasyon ng
     iyong emails.db (kadalasan ay katabi ng email_store.py, sa loob
     ng storage/ folder ng app mo).
  2. Patakbuhin: python3 test_real_db_readonly.py
"""

import os
import shutil
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.email_store import EmailStore

# --------------------------------------------------------------------
# PALITAN ITO ng totoong path ng emails.db mo.
# Halimbawa kung nasa storage/emails.db ito sa loob ng project mo:
#   REAL_DB_PATH = "/path/papunta/sa/project/storage/emails.db"
# --------------------------------------------------------------------
REAL_DB_PATH = "D:\\Python\\email_prj\\email_assistant\\Email-Assistant\\storage\\emails.db"

COPY_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "_real_db_test_copy.db"
)
RESULT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "result_real_db.txt"
)

# Fake uid na malayong-malayo sa normal na IMAP sequence numbers
# (karaniwang mga maliliit na numero lang ang totoong uid, 1-5 digits),
# para halos imposibleng mag-collide sa totoong email.
FAKE_TEST_UID = "TEST_UID_999999999"

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


def main():
    results.append("== EmailStore test gamit ang TOTOONG emails.db (safe copy) ==")

    # ------------------------------------------------------------------
    # Hakbang 1: Tiyaking may makikitang totoong db file
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Hakbang 2: Kopyahin ang totoong file -- HINDI na nagagalaw ang
    # orihinal mula dito pababa.
    # ------------------------------------------------------------------
    if os.path.exists(COPY_DB_PATH):
        os.remove(COPY_DB_PATH)
    shutil.copy2(REAL_DB_PATH, COPY_DB_PATH)
    results.append(f"Orihinal (HINDI GINALAW): {REAL_DB_PATH}")
    results.append(f"Ligtas na kopya (ito ang tinetestingan): {COPY_DB_PATH}\n")

    store = EmailStore(db_path=COPY_DB_PATH)

    # ------------------------------------------------------------------
    # Hakbang 3: LOAD test gamit ang totoong data -- makikita rito ang
    # tunay na laman ng inbox mo (galing sa copy).
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Hakbang 4: Safe SAVE+LOAD round-trip gamit ang FAKE uid -- hindi
    # nadadamay ang kahit anong totoong record, pero nasusubukan pa rin
    # ang save/load mechanism sa parehong file structure ng totoong db.
    # ------------------------------------------------------------------
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

        # Linisin: tanggalin ang fake row sa COPY (hindi sa totoong file,
        # kasi copy lang ang ginagalaw dito).
        store.conn.execute(
            "DELETE FROM emails WHERE folder=? AND uid=?", ("INBOX", FAKE_TEST_UID)
        )
        store.conn.commit()
        cleanup_check = store.get_email("INBOX", FAKE_TEST_UID)
        check("Fake test row na-clean up sa copy", cleanup_check is None)
    except Exception as e:
        check("Safe round-trip test", False, f"exception: {e}")
        traceback.print_exc()

    store.close()

    # ------------------------------------------------------------------
    # Buod
    # ------------------------------------------------------------------
    results.append("")
    results.append(f"SUMMARY: {passed} PASSED, {failed} FAILED (total {passed + failed})")
    overall = "ALL TESTS PASSED" if failed == 0 else f"{failed} TEST(S) FAILED"
    results.append(overall)

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(results) + "\n")

    print(f"\n{overall}")
    print(f"Resulta na-save sa: {RESULT_PATH}")

    # ------------------------------------------------------------------
    # Hakbang 5: Tanggalin ang temporary copy -- orihinal, hindi pa rin
    # nagagalaw sa buong proseso.
    # ------------------------------------------------------------------
    if os.path.exists(COPY_DB_PATH):
        os.remove(COPY_DB_PATH)
    print(f"Tinanggal na ang temporary copy: {COPY_DB_PATH}")
    print(f"Ang orihinal ay HINDI GINALAW: {REAL_DB_PATH}")


if __name__ == "__main__":
    main()
