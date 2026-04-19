import imaplib, email
from email.header import decode_header

mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login("academie@academiexguard.ca", "qlhoktyrfnrcbomd")
mail.select("INBOX")
s, m = mail.search(None, "ALL")
ids = m[0].split()

print(f"Total emails: {len(ids)}")
print()

for mid in ids[-15:]:
    s, data = mail.fetch(mid, "(RFC822)")
    msg = email.message_from_bytes(data[0][1])

    subj = decode_header(msg["Subject"] or "")[0][0]
    if isinstance(subj, bytes):
        subj = subj.decode(errors="ignore")

    frm = msg["From"] or ""
    date = msg["Date"] or ""

    # Get body preview
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    body_preview = body.replace("\n", " ").replace("\r", "")[:80]

    print(f"{date[:22]:22s} | {str(subj)[:45]:45s} | {frm[:35]}")
    if body_preview.strip():
        print(f"{'':22s}   {body_preview}")
    print()

mail.logout()
