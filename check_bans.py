import os
import sys

# Ensure the project root is in the python path
sys.path.append(os.getcwd())

from src.vanya.core.config_loader import CONFIG
from src.vanya.model.account import Account
from src.vanya.core.constants import LOGIN_URL, BASE_URL


def check_account_status(account: Account) -> tuple[str, str]:
    session = account.session

    # Mimic the headers used in LoginService
    session.headers.update({
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        "content-type": "application/x-www-form-urlencoded",
        "origin": BASE_URL,
        "referer": f"{BASE_URL}/index",
    })

    try:
        # Initial GET to set up cookies
        session.get(LOGIN_URL, timeout=10)

        # Attempt to POST credentials
        response = session.post(
            LOGIN_URL,
            data={
                "username": account.username,
                "password": account.password
            },
            allow_redirects=True,
            timeout=10
        )

        current_url = response.url.lower()
        response_text = response.text.lower()

        # CASE 1: Still on the login page (Failure)
        if "/login" in current_url:
            if "banned" in response_text or "suspended" in response_text:
                return "BANNED", "Account message says banned/suspended"
            elif "incorrect" in response_text or "invalid" in response_text:
                return "FAILED", "Incorrect username or password"
            else:
                return "FAILED", "Login failed (Unknown reason - Check manually)"

        # CASE 2: Redirected to a specific ban page
        if "banned" in current_url:
            return "BANNED", f"Redirected to {current_url}"

        # CASE 3: Successful Login (usually redirects to dashboard or index)
        return "OK", "Login successful"

    except Exception as e:
        return "ERROR", str(e)


if __name__ == "__main__":
    accounts = [Account(cfg) for cfg in CONFIG.accounts]

    print(f"\n🔍 Checking {len(accounts)} accounts for ban status...\n")

    # Header
    print(f"{'Username':<20} | {'Status':<10} | {'Message'}")
    print("-" * 70)

    for account in accounts:
        status, msg = check_account_status(account)

        # ANSI Colors for terminal output
        # Green for OK, Red for everything else
        color = "\033[92m" if status == "OK" else "\033[91m"
        reset = "\033[0m"

        print(f"{color}{account.username:<20} | {status:<10} | {msg}{reset}")

    print("\nDone.")
