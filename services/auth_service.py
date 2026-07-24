# Auth service: validation + connection logic for any IMAP provider.

from email_handler.imap_client import IMAPClient
from email_handler.provider_detect import detect_provider


def login(email_address: str, password: str, server: str = None, port: int = None) -> dict:
    # Validate the account and connect to its IMAP server.
    if not email_address or not password:
        return {"success": False, "error": "Please enter both your email address and password."}

    if server is None or port is None:
        detected = detect_provider(email_address)
        if not detected["supported"]:
            domain = email_address.split("@")[-1] if "@" in email_address else email_address
            return {
                "success": False,
                "error": (
                    f"Couldn't detect IMAP settings for '{domain}'. "
                    "Enter the server and port manually to continue."
                ),
            }
        server, port = detected["server"], detected["port"]

    try:
        client = IMAPClient(server, port, email_address, password)
        client.connect()
        return {"success": True, "client": client}
    except Exception as e:
        return {"success": False, "error": f"Login failed: {e}"}

def logout(client) -> None:
    # Disconnect the IMAP client when one exists.
    if client:
        client.disconnect()
