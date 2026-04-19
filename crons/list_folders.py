import imaplib
mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login("academie@academiexguard.ca", "qlhoktyrfnrcbomd")
s, folders = mail.list()
for f in folders:
    print(f.decode())

# Try inbox count
mail.select("INBOX")
s, m = mail.search(None, "ALL")
print(f"\nINBOX total: {len(m[0].split())}")

from datetime import datetime, timedelta
six_months = (datetime.now() - timedelta(days=180)).strftime("%d-%b-%Y")
s, m6 = mail.search(None, f"SINCE {six_months}")
print(f"INBOX last 6 months: {len(m6[0].split())}")

mail.logout()
