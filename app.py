import re
import time
import json
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template_string, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------
# Data: kommuner pr. region
# ---------------------------
KOMMUNER = {
    "Region Hovedstaden": [
        "Albertslund", "Allerød", "Ballerup", "Bornholm", "Brøndby", "Dragør", "Egedal",
        "Fredensborg", "Frederiksberg", "Frederikssund", "Furesø", "Gentofte", "Gladsaxe",
        "Glostrup", "Gribskov", "Halsnæs", "Helsingør", "Herlev", "Hillerød", "Hvidovre",
        "Høje-Taastrup", "Hørsholm", "Ishøj", "København", "Lyngby-Taarbæk", "Rudersdal",
        "Rødovre", "Tårnby", "Vallensbæk"
    ],
    "Region Sjælland": [
        "Faxe", "Greve", "Guldborgsund", "Holbæk", "Kalundborg", "Køge", "Lejre", "Lolland",
        "Næstved", "Odsherred", "Ringsted", "Roskilde", "Slagelse", "Solrød", "Sorø", "Stevns", "Vordingborg"
    ],
    "Region Syddanmark": [
        "Assens", "Billund", "Esbjerg", "Fanø", "Fredericia", "Faaborg-Midtfyn", "Haderslev",
        "Kerteminde", "Kolding", "Langeland", "Middelfart", "Nordfyn", "Nyborg", "Odense",
        "Svendborg", "Sønderborg", "Tønder", "Varde", "Vejen", "Vejle", "Ærø", "Aabenraa"
    ],
    "Region Midtjylland": [
        "Favrskov", "Hedensted", "Herning", "Holstebro", "Horsens", "Ikast-Brande", "Lemvig",
        "Norddjurs", "Odder", "Randers", "Ringkøbing-Skjern", "Silkeborg", "Skanderborg",
        "Skive", "Struer", "Syddjurs", "Viborg", "Aarhus"
    ],
    "Region Nordjylland": [
        "Brønderslev", "Frederikshavn", "Hjørring", "Jammerbugt", "Læsø", "Mariagerfjord",
        "Morsø", "Rebild", "Thisted", "Vesthimmerland", "Aalborg"
    ]
}

DOMAENE_UNDTAGELSER = {
    "København": "kk.dk",
    "Frederiksberg": "frederiksberg.dk",
    "Bornholm": "bornholm.dk",
    "Lyngby-Taarbæk": "ltk.dk",
    "Høje-Taastrup": "htk.dk",
    "Vallensbæk": "vallensbaek.dk",
    "Faaborg-Midtfyn": "faaborgmidtfyn.dk",
    "Ringkøbing-Skjern": "rksk.dk",
    "Ikast-Brande": "ikast-brande.dk",
    "Mariagerfjord": "mariagerfjord.dk",
    "Vesthimmerland": "vesthimmerland.dk",
    "Jammerbugt": "jammerbugt.dk",
    "Brønderslev": "broenderslev.dk",
    "Halsnæs": "halsnaes.dk"
}

# ---------------------------
# Hjælpefunktioner
# ---------------------------
def byg_kommune_url(kommune_navn):
    navn_lower = kommune_navn.lower().replace(" ", "-").replace("ø", "oe").replace("å", "aa").replace("æ", "ae")
    if kommune_navn in DOMAENE_UNDTAGELSER:
        domæne = DOMAENE_UNDTAGELSER[kommune_navn]
        return f"https://www.{domæne}"
    return f"https://www.{navn_lower}.dk"

SSP_STIER = [
    "/ssp", "/kontakt/ssp", "/om-kommunen/ssp", "/social-og-sundhed/ssp",
    "/borger/forebyggelse/ssp", "/ssp-samarbejde", "/samarbejde/ssp",
    "/tryghed/ssp", "/kontakt/ssp-medarbejdere", "/ssp-kontakt"
]

def find_ssp_side_med_selenium(base_url, timeout=10):
    """
    Brug Selenium til at besøge forsiden og klikke rundt efter SSP.
    Returnerer den første URL, der indeholder 'ssp' i stien eller tekst.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    try:
        driver.get(base_url)
        time.sleep(3)  # vent på evt. cookie-popups
        
        # Find alle links
        links = driver.find_elements("xpath", "//a[@href]")
        ssp_links = []
        for link in links:
            href = link.get_attribute("href")
            if href and "ssp" in href.lower():
                ssp_links.append(href)
        if ssp_links:
            return ssp_links[0]  # første hit
        
        # Alternativ: søg i sidens tekst efter "SSP" og klik på nærmeste link
        page_text = driver.page_source.lower()
        if "ssp" in page_text:
            # Prøv at finde et afsnit om SSP og tag første link derfra
            elements = driver.find_elements("xpath", "//*[contains(translate(text(),'SSP','ssp'), 'ssp')]/ancestor::a")
            if elements:
                return elements[0].get_attribute("href")
        return None
    except Exception as e:
        print(f"Selenium fejl: {e}")
        return None
    finally:
        driver.quit()

def google_fallback_ssp_side(kommune_navn, kommune_url):
    """
    Brug DuckDuckGo til at søge efter 'SSP kontakt site:kommune.dk'
    Returnerer den første URL, der ligner en SSP-side.
    """
    søgeterm = f"SSP kontakt site:{kommune_url.replace('https://', '').replace('http://', '')}"
    # DuckDuckGo scraping
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(søgeterm)}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, timeout=10, headers=headers)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Find resultatlinks
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('/l/?uddg='):
                    # DDG redirect link, extract real URL
                    real_url = re.search(r'uddg=(.*?)(&|$)', href)
                    if real_url:
                        url = requests.utils.unquote(real_url.group(1))
                        if kommune_url.replace('https://', '').replace('http://', '') in url and "ssp" in url.lower():
                            return url
            # Hvis ingen direkte, tag første resultat med kommune-domæne
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/l/?uddg=' in href:
                    real_url = re.search(r'uddg=(.*?)(&|$)', href)
                    if real_url:
                        url = requests.utils.unquote(real_url.group(1))
                        if kommune_url.replace('https://', '').replace('http://', '') in url:
                            return url
        return None
    except Exception as e:
        print(f"DDG søgefejl: {e}")
        return None

def find_ssp_side_robust(kommune_navn, base_url):
    # 1) Prøv kendte stier (statisk)
    for sti in SSP_STIER:
        url = urljoin(base_url, sti)
        try:
            resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                if "ssp" in resp.text.lower():
                    return url
        except:
            pass
    # 2) Brug Selenium til at interagere med siden
    print(f"  Prøver Selenium for {kommune_navn}...")
    ssp_url = find_ssp_side_med_selenium(base_url)
    if ssp_url:
        return ssp_url
    # 3) Fallback til DuckDuckGo søgning
    print(f"  Prøver DuckDuckGo-søgning for {kommune_navn}...")
    ssp_url = google_fallback_ssp_side(kommune_navn, base_url)
    return ssp_url

def find_ssp_kontakt_fra_side(side_url):
    """Brug Selenium til at hente dynamisk indhold, derefter BeautifulSoup."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    try:
        driver.get(side_url)
        time.sleep(2)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')
        
        kontakter = []
        # Mailto links
        email_links = soup.find_all('a', href=re.compile(r'mailto:'))
        telefon_links = soup.find_all('a', href=re.compile(r'tel:'))
        
        for link in email_links:
            email = link.get('href', '').replace('mailto:', '')
            navn = link.get_text(strip=True) or ""
            if not navn and link.parent:
                navn = link.parent.get_text(strip=True).split(email)[0].strip()
            kontakter.append({"navn": navn, "email": email, "telefon": "", "titel": ""})
        
        for link in telefon_links:
            telefon = link.get('href', '').replace('tel:', '')
            # match med eksisterende
            fundet = False
            for k in kontakter:
                if not k["telefon"]:
                    k["telefon"] = telefon
                    fundet = True
                    break
            if not fundet:
                kontakter.append({"navn": "", "email": "", "telefon": telefon, "titel": ""})
        
        # Hvis ingen af ovenstående, søg efter mønstre i tekst
        if not kontakter:
            body = soup.get_text()
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', body)
            telefoner = re.findall(r'(?:\d{2} \d{2} \d{2} \d{2}|\d{8}|\d{4} \d{4})', body)
            for email in emails[:3]:
                kontakter.append({"navn": "", "email": email, "telefon": "", "titel": ""})
            for tlf in telefoner[:3]:
                if not any(k["telefon"] == tlf for k in kontakter):
                    kontakter.append({"navn": "", "email": "", "telefon": tlf, "titel": ""})
        
        # Fjern dubletter
        unikke = []
        for k in kontakter:
            if k not in unikke:
                unikke.append(k)
        return unikke
    except Exception as e:
        print(f"Fejl ved scraping af {side_url} med Selenium: {e}")
        return []
    finally:
        driver.quit()

def scrape_kommune(region, kommune_navn):
    base_url = byg_kommune_url(kommune_navn)
    print(f"Behandler: {kommune_navn} ({region}) - {base_url}")
    
    ssp_url = find_ssp_side_robust(kommune_navn, base_url)
    if not ssp_url:
        return {
            "kommune": kommune_navn,
            "region": region,
            "hjemmeside": base_url,
            "ssp_side": None,
            "ssp_kontakt": [],
            "status": "not_found"
        }
    
    print(f"  SSP-side fundet: {ssp_url}")
    kontakter = find_ssp_kontakt_fra_side(ssp_url)
    status = "found" if kontakter else "no_contact"
    return {
        "kommune": kommune_navn,
        "region": region,
        "hjemmeside": base_url,
        "ssp_side": ssp_url,
        "ssp_kontakt": kontakter,
        "status": status
    }

# ---------------------------
# Flask Web App
# ---------------------------
app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>SSP Kontakt Scraper</title>
    <style>
        body { font-family: Arial; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .status-found { background-color: #d4edda; }
        .status-no_contact { background-color: #fff3cd; }
        .status-not_found { background-color: #f8d7da; }
        button { padding: 10px 20px; font-size: 16px; margin: 10px 0; }
        pre { background: #f4f4f4; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>SSP Kontakt Scraper</h1>
    <p>Klik på knappen for at starte scraping af alle kommuner (kan tage 5-10 minutter).</p>
    <form method="POST" action="/scrape">
        <button type="submit">Start scraping</button>
    </form>
    {% if data %}
        <h2>Resultater</h2>
        <table>
            <tr><th>Kommune</th><th>Region</th><th>SSP-side</th><th>Kontakter</th><th>Status</th></tr>
            {% for item in data %}
            <tr class="status-{{ item.status }}">
                <td>{{ item.kommune }}</td>
                <td>{{ item.region }}</td>
                <td><a href="{{ item.ssp_side }}" target="_blank">{{ item.ssp_side or 'Ikke fundet' }}</a></td>
                <td>
                    {% if item.ssp_kontakt %}
                        <ul>
                        {% for k in item.ssp_kontakt %}
                            <li>{{ k.navn }} - {{ k.email }} - {{ k.telefon }}</li>
                        {% endfor %}
                        </ul>
                    {% else %}
                        Ingen kontakt
                    {% endif %}
                </td>
                <td>{{ item.status }}</td>
            </tr>
            {% endfor %}
        </table>
        <h3>Download JSON</h3>
        <pre>{{ json_data }}</pre>
        <a href="/download">Download ssp_kontakter.json</a>
    {% endif %}
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, data=None, json_data=None)

@app.route('/scrape', methods=['POST'])
def scrape_all():
    alle_data = []
    for region, kommuner in KOMMUNER.items():
        for kommune in kommuner:
            result = scrape_kommune(region, kommune)
            alle_data.append(result)
            time.sleep(1)  # pænt mellemrum
    # Gem JSON
    with open("ssp_kontakter.json", "w", encoding="utf-8") as f:
        json.dump(alle_data, f, indent=2, ensure_ascii=False)
    json_str = json.dumps(alle_data, indent=2, ensure_ascii=False)
    return render_template_string(HTML_TEMPLATE, data=alle_data, json_data=json_str)

@app.route('/download')
def download():
    with open("ssp_kontakter.json", "r", encoding="utf-8") as f:
        data = f.read()
    return data, 200, {'Content-Type': 'application/json', 'Content-Disposition': 'attachment; filename=ssp_kontakter.json'}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)