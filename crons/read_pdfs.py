from PyPDF2 import PdfReader

for name, path in [("RAPPORT COMPARATIF SAC", "C:/Users/user/rapport_sac.pdf"),
                   ("INDICATEURS APP SAC", "C:/Users/user/indicateurs_sac.pdf")]:
    print(f"{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    r = PdfReader(path)
    print(f"Pages: {len(r.pages)}")
    for i, p in enumerate(r.pages):
        text = p.extract_text()
        if text:
            print(f"\n--- Page {i+1} ---")
            print(text[:2000].encode('ascii', 'replace').decode())
