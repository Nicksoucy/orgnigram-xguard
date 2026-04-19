import imaplib
from datetime import datetime, timedelta

mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login("academie@academiexguard.ca", "qlhoktyrfnrcbomd")

# INBOX
mail.select("INBOX")
s, m = mail.search(None, "ALL")
total = len(m[0].split())

six_months = (datetime.now() - timedelta(days=180)).strftime("%d-%b-%Y")
three_months = (datetime.now() - timedelta(days=90)).strftime("%d-%b-%Y")
one_month = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")

s, m6 = mail.search(None, f"SINCE {six_months}")
last_6m = len(m6[0].split())
s, m3 = mail.search(None, f"SINCE {three_months}")
last_3m = len(m3[0].split())
s, m1 = mail.search(None, f"SINCE {one_month}")
last_1m = len(m1[0].split())

# SENT
mail.select('"[Gmail]/Sent Mail"')
s, ms = mail.search(None, "ALL")
total_sent = len(ms[0].split())
s, ms6 = mail.search(None, f"SINCE {six_months}")
sent_6m = len(ms6[0].split())

mail.logout()

print(f"INBOX total: {total}")
print(f"INBOX last 6 months: {last_6m}")
print(f"INBOX last 3 months: {last_3m}")
print(f"INBOX last 1 month: {last_1m}")
print(f"SENT total: {total_sent}")
print(f"SENT last 6 months: {sent_6m}")
print(f"Total to analyze (6m): {last_6m + sent_6m}")
