from pathlib import Path

root = Path(__file__).resolve().parent

for name in [
    "settings-polish-variants.html",
    "settings-about-variants.html",
    "history-variants.html",
]:
    p = root / name
    text = p.read_text(encoding="utf-8")
    marker = "<!DOCTYPE html>"
    idx = text.find(marker)
    if idx <= 0:
        print(name, "already clean or missing uppercase DOCTYPE; idx=", idx)
        continue
    # Drop thin JS stub before the full static document
    kept = text[idx:]
    p.write_text(kept, encoding="utf-8")
    print(name, "stripped stub; kept", len(kept), "from offset", idx)

models = root / "settings-models-variants.html"
if models.exists():
    t = models.read_text(encoding="utf-8")
    print("models", models.stat().st_size, "DOCTYPE", t.count("<!DOCTYPE"), "badge", t.count('class="badge"'))

for name in [
    "settings-polish-variants.html",
    "settings-about-variants.html",
    "history-variants.html",
]:
    p = root / name
    t = p.read_text(encoding="utf-8")
    print(
        name,
        p.stat().st_size,
        "starts=",
        t[:40].replace("\n", " "),
        "badge=",
        t.count('class="badge"'),
        "doctype_lower=",
        t.lower().count("<!doctype"),
    )

# remove helper
Path(__file__).unlink(missing_ok=True)
print("cleanup script removed")
