
import json
import re
import threading
import time
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template_string, send_file

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_JSON = BASE_DIR / "ssp_kontakter.json"
OUTPUT_CSV = BASE_DIR / "ssp_kontakter.csv"
OUTPUT_XLSX = BASE_DIR / "ssp_kontakter.xlsx"

BASE_SEARCH_URL = "https://ssp-samraadet.dk/organisationen/repraesentanter/?search={query}"

KOMMUNER = {
    "Region Hovedstaden": ["Albertslund", "Allerød", "Ballerup", "Bornholm", "Brøndby", "Dragør", "Egedal", "Fredensborg", "Frederiksberg", "Frederikssund", "Furesø", "Gentofte", "Gladsaxe", "Glostrup", "Gribskov", "Halsnæs", "Helsingør", "Herlev", "Hillerød", "Hvidovre", "Høje-Taastrup", "Hørsholm", "Ishøj", "København", "Lyngby-Taarbæk", "Rudersdal", "Rødovre", "Tårnby", "Vallensbæk"],
    "Region Sjælland": ["Faxe", "Greve", "Guldborgsund", "Holbæk", "Kalundborg", "Køge", "Lejre", "Lolland", "Næstved", "Odsherred", "Ringsted", "Roskilde", "Slagelse", "Solrød", "Sorø", "Stevns", "Vordingborg"],
    "Region Syddanmark": ["Assens", "Billund", "Esbjerg", "Fanø", "Fredericia", "Faaborg-Midtfyn", "Haderslev", "Kerteminde", "Kolding", "Langeland", "Middelfart", "Nordfyn", "Nyborg", "Odense", "Svendborg", "Sønderborg", "Tønder", "Varde", "Vejen", "Vejle", "Ærø", "Aabenraa"],
    "Region Midtjylland": ["Favrskov", "Hedensted", "Herning", "Holstebro", "Horsens", "Ikast-Brande", "Lemvig", "Norddjurs", "Odder", "Randers", "Ringkøbing-Skjern", "Silkeborg", "Skanderborg", "Skive", "Struer", "Syddjurs", "Viborg", "Aarhus", "Samsø"],
    "Region Nordjylland": ["Brønderslev", "Frederikshavn", "Hjørring", "Jammerbugt", "Læsø", "Mariagerfjord", "Morsø", "Rebild", "Thisted", "Vesthimmerland", "Aalborg"]
}

MUNICIPALITY_WEBSITES = {
    "Albertslund": "https://www.albertslund.dk",
    "Allerød": "https://www.alleroed.dk",
    "Ballerup": "https://www.ballerup.dk",
    "Bornholm": "https://www.brk.dk",
    "Brøndby": "https://www.brondby.dk",
    "Dragør": "https://www.dragoer.dk",
    "Egedal": "https://www.egedalkommune.dk",
    "Fredensborg": "https://www.fredensborg.dk",
    "Frederiksberg": "https://www.frederiksberg.dk",
    "Frederikssund": "https://www.frederikssund.dk",
    "Furesø": "https://www.furesoe.dk",
    "Gentofte": "https://www.gentofte.dk",
    "Gladsaxe": "https://www.gladsaxe.dk",
    "Glostrup": "https://www.glostrup.dk",
    "Gribskov": "https://www.gribskov.dk",
    "Halsnæs": "https://www.halsnaes.dk",
    "Helsingør": "https://www.helsingor.dk",
    "Herlev": "https://www.herlev.dk",
    "Hillerød": "https://www.hillerod.dk",
    "Hvidovre": "https://www.hvidovre.dk",
    "Høje-Taastrup": "https://www.htk.dk",
    "Hørsholm": "https://www.horsholm.dk",
    "Ishøj": "https://www.ishoj.dk",
    "København": "https://www.kk.dk",
    "Lyngby-Taarbæk": "https://www.ltk.dk",
    "Rudersdal": "https://www.rudersdal.dk",
    "Rødovre": "https://www.rk.dk",
    "Tårnby": "https://www.taarnby.dk",
    "Vallensbæk": "https://www.vallensbaek.dk",
    "Faxe": "https://www.faxekommune.dk",
    "Greve": "https://www.greve.dk",
    "Guldborgsund": "https://www.guldborgsund.dk",
    "Holbæk": "https://www.holbaek.dk",
    "Kalundborg": "https://www.kalundborg.dk",
    "Køge": "https://www.koege.dk",
    "Lejre": "https://www.lejre.dk",
    "Lolland": "https://www.lolland.dk",
    "Næstved": "https://www.naestved.dk",
    "Odsherred": "https://www.odsherred.dk",
    "Ringsted": "https://www.ringsted.dk",
    "Roskilde": "https://www.roskilde.dk",
    "Slagelse": "https://www.slagelse.dk",
    "Solrød": "https://www.solrod.dk",
    "Sorø": "https://www.soroe.dk",
    "Stevns": "https://www.stevns.dk",
    "Vordingborg": "https://www.vordingborg.dk",
    "Assens": "https://www.assens.dk",
    "Billund": "https://www.billund.dk",
    "Esbjerg": "https://www.esbjerg.dk",
    "Fanø": "https://www.fanoe.dk",
    "Fredericia": "https://www.fredericia.dk",
    "Faaborg-Midtfyn": "https://www.fmk.dk",
    "Haderslev": "https://www.haderslev.dk",
    "Kerteminde": "https://www.kerteminde.dk",
    "Kolding": "https://www.kolding.dk",
    "Langeland": "https://www.langelandkommune.dk",
    "Middelfart": "https://www.middelfart.dk",
    "Nordfyn": "https://www.nordfynskommune.dk",
    "Nyborg": "https://www.nyborg.dk",
    "Odense": "https://www.odense.dk",
    "Svendborg": "https://www.svendborg.dk",
    "Sønderborg": "https://www.sonderborgkommune.dk",
    "Tønder": "https://www.toender.dk",
    "Varde": "https://www.vardekommune.dk",
    "Vejen": "https://www.vejen.dk",
    "Vejle": "https://www.vejle.dk",
    "Ærø": "https://www.aeroekommune.dk",
    "Aabenraa": "https://www.aabenraa.dk",
    "Favrskov": "https://www.favrskov.dk",
    "Hedensted": "https://www.hedensted.dk",
    "Herning": "https://www.herning.dk",
    "Holstebro": "https://www.holstebro.dk",
    "Horsens": "https://www.horsens.dk",
    "Ikast-Brande": "https://www.ikast-brande.dk",
    "Lemvig": "https://www.lemvig.dk",
    "Norddjurs": "https://www.norddjurs.dk",
    "Odder": "https://www.odder.dk",
    "Randers": "https://www.randers.dk",
    "Ringkøbing-Skjern": "https://www.rksk.dk",
    "Silkeborg": "https://www.silkeborg.dk",
    "Skanderborg": "https://www.skanderborg.dk",
    "Skive": "https://www.skive.dk",
    "Struer": "https://www.struer.dk",
    "Syddjurs": "https://www.syddjurs.dk",
    "Viborg": "https://www.viborg.dk",
    "Aarhus": "https://www.aarhus.dk",
    "Samsø": "https://www.samsoe.dk",
    "Brønderslev": "https://www.bronderslev.dk",
    "Frederikshavn": "https://www.frederikshavn.dk",
    "Hjørring": "https://www.hjoerring.dk",
    "Jammerbugt": "https://www.jammerbugt.dk",
    "Læsø": "https://www.laesoe.dk",
    "Mariagerfjord": "https://www.mariagerfjord.dk",
    "Morsø": "https://www.morsoe.dk",
    "Rebild": "https://www.rebild.dk",
    "Thisted": "https://www.thisted.dk",
    "Vesthimmerland": "https://www.vesthimmerland.dk",
    "Aalborg": "https://www.aalborg.dk",
}


def slugify(text: str) -> str:
    replacements = {
        "æ": "ae", "ø": "oe", "å": "aa",
        "Æ": "ae", "Ø": "oe", "Å": "aa",
    }
    value = text
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def build_ssp_search_url(kommune_navn: str) -> str:
    return BASE_SEARCH_URL.format(query=quote(kommune_navn, safe="-"))


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"
    })
    return session


def extract_contacts_from_html(html: str, kommune: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()

    for block in soup.find_all(["article", "div", "li", "section"]):
        text = normalize_ws(block.get_text(" ", strip=True))
        if not text:
            continue

        mailto_links = block.select('a[href^="mailto:"]')
        tel_links = block.select('a[href^="tel:"]')
        if not mailto_links and not tel_links:
            continue

        emails = []
        for tag in mailto_links:
            email = tag.get("href", "").replace("mailto:", "").strip()
            if email and email not in emails:
                emails.append(email)

        phones = []
        for tag in tel_links:
            phone = tag.get("href", "").replace("tel:", "").strip()
            if phone and phone not in phones:
                phones.append(phone)

        name = ""
        title = ""

        for heading in block.find_all(["h1", "h2", "h3", "h4", "strong", "b"]):
            candidate = normalize_ws(heading.get_text(" ", strip=True))
            if candidate and "@" not in candidate and len(candidate) <= 120:
                if not name:
                    name = candidate
                elif not title:
                    title = candidate
                    break

        if not name:
            for line in [normalize_ws(x) for x in block.stripped_strings][:6]:
                if (
                    line and "@" not in line and len(line) <= 120
                    and not re.search(r"\d{4,}", line)
                    and "telefon" not in line.lower()
                    and "mail" not in line.lower()
                ):
                    name = line
                    break

        if not title:
            for p in [normalize_ws(p.get_text(" ", strip=True)) for p in block.find_all(["p", "span"])][:6]:
                lower = p.lower()
                if p and len(p) <= 140 and (
                    "ssp" in lower
                    or "konsulent" in lower
                    or "koordinator" in lower
                    or "repræsentant" in lower
                    or "forebygg" in lower
                ):
                    title = p
                    break

        key = (name, tuple(emails), tuple(phones))
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "name": name or "SSP kontakt",
            "email": emails[0] if emails else "",
            "phone": phones[0] if phones else "",
            "title": title,
            "emails": emails,
            "phones": phones,
            "rawText": text[:500],
        })

    return results


def build_verification(entry: dict) -> dict:
    contacts = entry["contacts"]
    has_contact = len(contacts) > 0
    has_email = any(contact.get("email") for contact in contacts)
    has_phone = any(contact.get("phone") for contact in contacts)
    website = entry.get("website", "")
    domain = website.replace("https://", "").replace("http://", "").split("/")[0]
    domain_matches = domain.endswith(".dk") if domain else False

    confidence = 0.3
    if has_contact:
        confidence += 0.2
    if has_email:
        confidence += 0.2
    if has_phone:
        confidence += 0.1
    if entry.get("sourceType") == "official":
        confidence += 0.1
    if domain_matches:
        confidence += 0.1
    confidence = min(confidence, 0.9)

    return {
        "sourceLooksOfficial": entry.get("sourceType") == "official",
        "hasContact": has_contact,
        "hasEmail": has_email,
        "hasPhone": has_phone,
        "domainMatchesMunicipality": domain_matches,
        "scrapeStatus": entry["status"],
        "manualReviewed": False,
        "confidence": round(confidence, 2),
    }


def transform_result(region: str, municipality: str, contacts: list[dict]) -> dict:
    website = MUNICIPALITY_WEBSITES.get(municipality, "")
    ssp_page = f"{website}/ssp" if website else ""

    transformed_contacts = []
    for contact in contacts:
        transformed_contacts.append({
            "name": contact.get("name", ""),
            "email": contact.get("email", ""),
            "phone": contact.get("phone", ""),
            "title": contact.get("title", ""),
        })

    status = "found" if transformed_contacts else "no_contact"
    source_type = "official" if website else "directory"

    entry = {
        "id": f"{slugify(municipality)}-ssp",
        "municipality": municipality,
        "region": region,
        "website": website,
        "sspPage": ssp_page,
        "contacts": transformed_contacts,
        "status": status,
        "sourceType": source_type,
        "verificationStatus": "auto-validated",
        "verification": {},
        "verifiedAt": "",
        "notes": "",
        "sourceSummary": {
            "hasWebsite": bool(website),
            "hasSspPage": bool(ssp_page),
            "contactCount": len(transformed_contacts),
        },
    }
    entry["verification"] = build_verification(entry)
    return entry


def scrape_kommune(session: requests.Session, region: str, municipality: str) -> dict:
    url = build_ssp_search_url(municipality)
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        contacts = extract_contacts_from_html(response.text, municipality)
        result = transform_result(region, municipality, contacts)
        result["notes"] = f"Data hentet fra {url}"
        return result
    except Exception as exc:
        result = transform_result(region, municipality, [])
        result["status"] = "error"
        result["verification"]["scrapeStatus"] = "error"
        result["notes"] = str(exc)
        return result


def flatten_results(results: list[dict]) -> list[dict]:
    rows = []
    for item in results:
        if item["contacts"]:
            for contact in item["contacts"]:
                rows.append({
                    "id": item["id"],
                    "municipality": item["municipality"],
                    "region": item["region"],
                    "website": item["website"],
                    "sspPage": item["sspPage"],
                    "status": item["status"],
                    "sourceType": item["sourceType"],
                    "verificationStatus": item["verificationStatus"],
                    "name": contact.get("name", ""),
                    "email": contact.get("email", ""),
                    "phone": contact.get("phone", ""),
                    "title": contact.get("title", ""),
                    "confidence": item["verification"].get("confidence", ""),
                    "notes": item["notes"],
                })
        else:
            rows.append({
                "id": item["id"],
                "municipality": item["municipality"],
                "region": item["region"],
                "website": item["website"],
                "sspPage": item["sspPage"],
                "status": item["status"],
                "sourceType": item["sourceType"],
                "verificationStatus": item["verificationStatus"],
                "name": "",
                "email": "",
                "phone": "",
                "title": "",
                "confidence": item["verification"].get("confidence", ""),
                "notes": item["notes"],
            })
    return rows


def save_outputs(results: list[dict]) -> None:
    OUTPUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    df = pd.DataFrame(flatten_results(results))
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    df.to_excel(OUTPUT_XLSX, index=False)


progress_state = {
    "running": False,
    "start_time": None,
    "completed": 0,
    "total": sum(len(v) for v in KOMMUNER.values()),
    "current_kommune": None,
    "results": [],
    "success_list": [],
    "no_contact_list": [],
    "error_list": [],
}

stop_flag = False
state_lock = threading.Lock()
stop_lock = threading.Lock()


def reset_progress() -> None:
    with state_lock:
        progress_state["running"] = True
        progress_state["start_time"] = time.time()
        progress_state["completed"] = 0
        progress_state["current_kommune"] = None
        progress_state["results"] = []
        progress_state["success_list"] = []
        progress_state["no_contact_list"] = []
        progress_state["error_list"] = []


def run_full_scrape() -> None:
    global stop_flag
    with stop_lock:
        stop_flag = False

    reset_progress()
    results = []
    session = make_session()

    try:
        for region, municipalities in KOMMUNER.items():
            for municipality in municipalities:
                with stop_lock:
                    if stop_flag:
                        break

                with state_lock:
                    progress_state["current_kommune"] = municipality

                item = scrape_kommune(session, region, municipality)
                results.append(item)

                with state_lock:
                    progress_state["completed"] += 1
                    progress_state["results"] = results
                    bucket = {"kommune": municipality, "status": item["status"]}
                    if item["status"] == "found":
                        progress_state["success_list"].append(bucket)
                    elif item["status"] == "no_contact":
                        progress_state["no_contact_list"].append(bucket)
                    else:
                        progress_state["error_list"].append(bucket)

                time.sleep(0.6)

            with stop_lock:
                if stop_flag:
                    break
    finally:
        save_outputs(results)
        with state_lock:
            progress_state["running"] = False
            progress_state["results"] = results
            progress_state["current_kommune"] = None


app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html lang="da">
<head>
    <meta charset="UTF-8">
    <title>SSP Kontakt Scraper</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="max-w-6xl mx-auto p-8">
        <h1 class="text-4xl font-semibold text-gray-900">SSP Kontakt Scraper</h1>
        <p class="text-gray-600 mt-2 mb-2">Forenklet version med struktureret JSON-output.</p>
        <p class="text-gray-600 mb-8">Typisk samlet køretid for alle 98 kommuner: ca. 1 minut og 15 sekunder.</p>

        <div id="start-panel" class="bg-white shadow rounded-3xl p-8 mb-8">
            <button onclick="startScraping()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xl py-5 rounded-3xl">
                START SCRAPING
            </button>
        </div>

        <div id="progress-panel" class="hidden bg-white shadow rounded-3xl p-8 mb-8">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-2xl font-semibold">Status</h2>
                <div id="current-kommune" class="text-blue-700 font-medium"></div>
            </div>
            <div class="mb-4">
                <div class="flex justify-between text-sm text-gray-600 mb-2">
                    <div><span id="completed-count">0</span>/<span id="total-count">0</span> kommuner</div>
                    <div id="elapsed-time">0:00</div>
                </div>
                <div class="h-3 bg-gray-200 rounded-full overflow-hidden">
                    <div id="progress-bar" class="h-3 bg-blue-600" style="width: 0%"></div>
                </div>
                <div class="text-xs text-gray-500 mt-2">Tid tilbage: <span id="eta-time">–</span></div>
            </div>

            <div class="grid grid-cols-3 gap-6">
                <div>
                    <div class="font-medium text-emerald-700 mb-2">Fundet: <span id="success-count-badge">0</span></div>
                    <ul id="success-list" class="text-sm space-y-1"></ul>
                </div>
                <div>
                    <div class="font-medium text-amber-700 mb-2">Ingen kontakt: <span id="no-contact-count-badge">0</span></div>
                    <ul id="no-contact-list" class="text-sm space-y-1"></ul>
                </div>
                <div>
                    <div class="font-medium text-red-700 mb-2">Fejl: <span id="error-count-badge">0</span></div>
                    <ul id="error-list" class="text-sm space-y-1"></ul>
                </div>
            </div>

            <button onclick="stopScraping()" class="mt-6 w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-4 rounded-3xl">
                STOP
            </button>
        </div>

        <div id="final-panel" class="hidden bg-white shadow rounded-3xl p-8">
            <h2 class="text-3xl font-semibold mb-6">Færdig</h2>
            <div class="grid grid-cols-3 gap-6 mb-8">
                <div class="text-center"><div id="final-success" class="text-4xl font-semibold text-emerald-600">0</div><div>Fundet</div></div>
                <div class="text-center"><div id="final-no-contact" class="text-4xl font-semibold text-amber-600">0</div><div>Ingen kontakt</div></div>
                <div class="text-center"><div id="final-error" class="text-4xl font-semibold text-red-600">0</div><div>Fejl</div></div>
            </div>
            <div class="grid grid-cols-3 gap-4">
                <a href="/download/json" class="block text-center bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 rounded-2xl">Download JSON</a>
                <a href="/download/csv" class="block text-center bg-slate-700 hover:bg-slate-800 text-white font-semibold py-4 rounded-2xl">Download CSV</a>
                <a href="/download/xlsx" class="block text-center bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-4 rounded-2xl">Download Excel</a>
            </div>
        </div>
    </div>

    <script>
        let pollingInterval = null;

        function renderList(id, items) {
            const ul = document.getElementById(id);
            ul.innerHTML = "";
            if (!items.length) {
                ul.innerHTML = '<li class="text-gray-400 italic">Ingen endnu...</li>';
                return;
            }
            items.forEach(item => {
                const li = document.createElement("li");
                li.className = "bg-gray-50 rounded-xl px-3 py-2";
                li.textContent = `${item.kommune} (${item.status})`;
                ul.appendChild(li);
            });
        }

        function startScraping() {
            document.getElementById("start-panel").classList.add("hidden");
            document.getElementById("progress-panel").classList.remove("hidden");
            fetch("/scrape", { method: "POST" }).then(() => {
                pollingInterval = setInterval(fetchProgress, 1500);
            });
        }

        function stopScraping() {
            fetch("/stop", { method: "POST" });
        }

        function fetchProgress() {
            fetch("/progress").then(r => r.json()).then(data => {
                const total = data.total || 0;
                const completed = data.completed || 0;
                document.getElementById("completed-count").textContent = completed;
                document.getElementById("total-count").textContent = total;
                document.getElementById("elapsed-time").textContent = data.elapsed_formatted;
                document.getElementById("eta-time").textContent = data.eta_formatted;
                document.getElementById("current-kommune").textContent = data.current_kommune ? `Behandler: ${data.current_kommune}` : "";
                document.getElementById("progress-bar").style.width = `${total ? Math.round(completed * 100 / total) : 0}%`;

                document.getElementById("success-count-badge").textContent = data.success_count;
                document.getElementById("no-contact-count-badge").textContent = data.no_contact_count;
                document.getElementById("error-count-badge").textContent = data.error_count;

                renderList("success-list", data.success_list);
                renderList("no-contact-list", data.no_contact_list);
                renderList("error-list", data.error_list);

                if (!data.running && completed > 0) {
                    clearInterval(pollingInterval);
                    document.getElementById("progress-panel").classList.add("hidden");
                    document.getElementById("final-panel").classList.remove("hidden");
                    document.getElementById("final-success").textContent = data.success_count;
                    document.getElementById("final-no-contact").textContent = data.no_contact_count;
                    document.getElementById("final-error").textContent = data.error_count;
                }
            });
        }
    </script>
</body>
</html>
"""


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/scrape", methods=["POST"])
def start_scrape():
    with state_lock:
        if progress_state["running"]:
            return jsonify({"status": "already_running"})

    thread = threading.Thread(target=run_full_scrape, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/stop", methods=["POST"])
def stop_scrape():
    global stop_flag
    with stop_lock:
        stop_flag = True
    return jsonify({"status": "stopping"})


@app.route("/progress")
def progress():
    with state_lock:
        state = dict(progress_state)

    elapsed = 0
    eta = "–"
    if state["start_time"]:
        elapsed = time.time() - state["start_time"]
        if state["completed"]:
            avg = elapsed / state["completed"]
            remaining = avg * (state["total"] - state["completed"])
            eta = format_duration(remaining)

    return jsonify({
        "running": state["running"],
        "current_kommune": state["current_kommune"],
        "completed": state["completed"],
        "total": state["total"],
        "elapsed_formatted": format_duration(elapsed),
        "eta_formatted": eta,
        "success_count": len(state["success_list"]),
        "no_contact_count": len(state["no_contact_list"]),
        "error_count": len(state["error_list"]),
        "success_list": state["success_list"][-8:],
        "no_contact_list": state["no_contact_list"][-8:],
        "error_list": state["error_list"][-8:],
    })


@app.route("/download/json")
def download_json():
    if not OUTPUT_JSON.exists():
        return "Ingen JSON endnu", 404
    return send_file(OUTPUT_JSON, as_attachment=True, download_name=OUTPUT_JSON.name)


@app.route("/download/csv")
def download_csv():
    if not OUTPUT_CSV.exists():
        return "Ingen CSV endnu", 404
    return send_file(OUTPUT_CSV, as_attachment=True, download_name=OUTPUT_CSV.name)


@app.route("/download/xlsx")
def download_xlsx():
    if not OUTPUT_XLSX.exists():
        return "Ingen Excel endnu", 404
    return send_file(OUTPUT_XLSX, as_attachment=True, download_name=OUTPUT_XLSX.name)


if __name__ == "__main__":
    print("Starter SSP Kontakt Scraper på http://localhost:5000")
    print("Forventet køretid for 98 kommuner: ca. 1 minut og 15 sekunder")
    app.run(debug=True, host="0.0.0.0", port=5000)
