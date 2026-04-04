from curl_cffi import requests
import time
import re

BASE_URL = "https://vanyaonline.com"
LOGIN_URL = f"{BASE_URL}/login"
url_train = f"{BASE_URL}/process/house_train_click.php"
url_dash = f"{BASE_URL}/dashboard"

def get_global_csrf(html: str) -> str:
    match = re.search(r'globalCsrfToken\s*=\s*"([a-f0-9]+)"', html)
    if not match:
        raise RuntimeError("Global CSRF token not found")
    return match.group(1)

def authenticate():
    session = requests.Session(impersonate="chrome120")

    session.cookies.update({
        '__stripe_mid': '2b6d1538-820f-48df-8514-892fd8965b9f39483b'
    })

    session.headers.update({
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,pt-PT;q=0.8,pt;q=0.7,pl;q=0.6',
        'cache-control': 'no-cache',
        'dnt': '1',
        'origin': BASE_URL,
    })

    session.get(LOGIN_URL)

    session.post(
        LOGIN_URL,
        headers={"referer": f"{BASE_URL}/index"},
        data={
            "username": "Skyrus",
            "password": "J@ny1234"
        }
    )

    dash_response = session.get(url_dash)
    csrf_token = get_global_csrf(dash_response.text)

    session.headers.update({'x-csrf-token': csrf_token})
    return session

session = authenticate()

train_headers = {
    'referer': f"{BASE_URL}/house",
    'content-type': 'application/x-www-form-urlencoded'
}

train_data = {
    'skill': 'defense',
    'start': '0',
    'force': '0',
    'batch_hits': '3'
}

interval = 3

while True:
    try:
        start_time = time.time()
        response = session.post(url_train, headers=train_headers, data=train_data, timeout=5)
        elapsed = time.time() - start_time

        print(f"Response: {response.text} | Request took: {elapsed:.3f} seconds")

        response_text_lower = response.text.lower()
        if "unauthorized" in response_text_lower or "unautorized" in response_text_lower:
            print("Re-authenticating...")
            session = authenticate()
            continue

        try:
            data = response.json()
            if data.get("stamina") == 0:
                print("Stamina is 0. Sleeping for 5 minutes...")
                time.sleep(300)
                continue
        except Exception:
            pass

        sleep_time = max(0, interval - elapsed)
        time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nScript stopped by user.")
        break
    except Exception as e:
        print(f"Error encountered: {e}")
        time.sleep(2)
