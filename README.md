# 🇩🇰 SSP Kontakt Scraper

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![Selenium](https://img.shields.io/badge/Selenium-4.15-orange.svg)](https://www.selenium.dev/)

**Automatisk indsamling af SSP-medarbejderes kontaktoplysninger fra alle 98 danske kommuner.**  
Scraperen bruger en kombination af statisk HTTP, Selenium (JavaScript-håndtering) og DuckDuckGo-fallback for at finde den rigtige SSP-side – og udtrækker herefter e-mails og telefonnumre.

> ✅ Perfekt til programmører, der skal bruge en struktureret JSON-database med kontaktinfo til SSP-samarbejdet i hele Danmark.

---

## 📦 Hvad kan den gøre for dig?

- **Færdig JSON-database** – spar timer på manuel søgning på 98 kommunale hjemmesider.
- **Robust scraping** – håndterer JavaScript, cookie-popups og dynamisk indhold via Selenium.
- **Fallback til søgemaskine** – finder SSP-sider selv når de ikke ligger på standardstier.
- **Webinterface** – start scraping med ét klik og download resultatet.
- **Let at integrere** – output er ren JSON, klar til brug i andre systemer, analyser eller dashboards.

---

## 🚀 Kom godt i gang

### Forudsætninger

- **Python 3.8 eller nyere**
- **Google Chrome** installeret (Selenium bruger ChromeDriver – webdriver-manager henter automatisk den rigtige version)

### Installation

1. **Klon repositoriet**  
   ```bash
   git clone https://github.com/dit-brugernavn/ssp-kontakt-scraper.git
   cd ssp-kontakt-scraper