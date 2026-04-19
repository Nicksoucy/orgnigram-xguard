import imaplib

mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login("academie@academiexguard.ca", "qlhoktyrfnrcbomd")

status, folder_list = mail.list()
total = 0
folders_count = {}

for f in folder_list:
    try:
        parts = f.decode().split('"')
        if len(parts) >= 3:
            folder = parts[-2]
            if "\\Noselect" in parts[0]:
                continue
            status, _ = mail.select(f'"{folder}"', readonly=True)
            if status != "OK":
                continue
            s, m = mail.search(None, "ALL")
            count = len(m[0].split()) if m[0] else 0
            if count > 0:
                folders_count[folder] = count
                total += count
    except:
        pass

mail.logout()

print(f"TOTAL EMAILS: {total}")
print()
for folder, count in sorted(folders_count.items(), key=lambda x: -x[1]):
    print(f"  {count:5d} | {folder}")
