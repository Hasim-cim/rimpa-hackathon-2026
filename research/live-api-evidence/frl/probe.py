"""Throwaway probe: can we resolve realistic legislation citations against the Federal Register of Legislation?"""
import re, sys, time, json, urllib.parse, urllib.request
B = "https://api.prod.legislation.gov.au/v1"
def get(path, **params):
    url = f"{B}/{path}?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    t = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=20) as r:
            return json.load(r), time.time() - t, None
    except Exception as e:
        return None, time.time() - t, str(e)[:120]
def normalise(raw):
    s = re.sub(r"\((Cth|Commonwealth)\)", "", raw)
    s = re.split(r"\s+(s|ss|sec|section|sch|pt|part)\.?\s*\d", s, flags=re.I)[0]
    s = re.sub(r"[.,;]+$", "", s).strip()
    m = re.search(r"^(.*?\b(Act|Regulations?|Rules?)\b(\s+\d{4})?)", s)
    return (m.group(1) if m else s).strip()
def esc(s): return s.replace("'", "''")
cites = [
  "Social Security Act 1991 (Cth) s 1237AAD.",
  "Public Service Act 1922 (Cth)",
  "Archives Act 1983 (Cth), s 24",
  "Privacy Act 1988 (Cth) sch 1",
  "Freedom of Information Act 1982",
  "Public Governance, Performance and Accountability Act 2013 (Cth) s 15",
  "Social Security Act 1947",
  "Privacy Act 1989 (Cth)",           # wrong year, does not exist
  "Records Integrity Act 2021 (Cth)",  # invented
  "Data Availability and Transparency Act 2022",
]
for c in cites:
    name = normalise(c)
    d, dt, err = get("titles", **{"$filter": f"name eq '{esc(name)}'", "$select": "id,name,status,year,number"})
    hits = (d or {}).get("value", [])
    how = "exact"
    if not hits and not err:
        stem = re.sub(r"\s+\d{4}$", "", name)
        d, dt2, err = get("titles", **{"$filter": f"contains(name,'{esc(stem)}')", "$select": "id,name,status,year", "$top": "5"})
        dt += dt2; hits = (d or {}).get("value", []); how = "contains(stem)"
    print(f"{c!r:72} -> {name!r:58} {how:15} {dt:4.1f}s {'ERR '+err if err else ''}")
    for h in hits[:4]: print("      ", h.get("id"), h.get("name"), h.get("status"))
