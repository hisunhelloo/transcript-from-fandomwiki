# 📜 Fandom Transcript Crawler

A web app that crawls any **Fandom wiki `/Transcript` page** and lets you download it as **Markdown**, **PDF**, or **Word (.docx)** — instantly.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

- 🔗 Paste any `*.fandom.com/wiki/*/Transcript` URL
- 📝 Export as **Markdown** (`.md`)
- 📄 Export as **PDF** (styled, with character names in blue)
- 📃 Export as **Word** (`.docx`)
- ⚡ Multiple formats packed into a single `.zip` download
- 🌐 Works across all Fandom wikis (Phineas and Ferb, Harry Potter, etc.)

---

## 🖥️ Demo

> Paste a URL → select formats → click Generate → ZIP downloads automatically.

---

## 🚀 Deploy to Render (Free)

### 1. Push to GitHub

```bash
git remote add origin https://github.com/<your-username>/transcript-from-fandom.git
git push -u origin master
```

### 2. Deploy on Render

1. Go to [render.com](https://render.com) and sign up (free)
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — just click **Deploy**

That's it. No environment variables needed.

> ⚠️ **Free tier note:** The service sleeps after 15 minutes of inactivity. The first request after sleep takes ~30 seconds to wake up.

---

## 🛠️ Run Locally

### Prerequisites

- Python 3.11+

### Setup

```bash
git clone https://github.com/<your-username>/transcript-from-fandom.git
cd transcript-from-fandom

pip install -r requirements.txt
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

### CLI usage (no web server needed)

```bash
# Default: crawl Rollercoaster transcript → output/ as both md + pdf
python crawl_transcript.py

# Custom URL
python crawl_transcript.py https://phineasandferb.fandom.com/wiki/Lawn_Gnome_Beach_Party_of_Terror/Transcript

# Markdown only, custom output directory
python crawl_transcript.py <URL> --format md --out ./transcripts

# Options
python crawl_transcript.py --help
```

---

## 📁 Project Structure

```
transcript-from-fandom/
├── app.py                  # Flask web server + crawler logic
├── crawl_transcript.py     # Standalone CLI version
├── templates/
│   └── index.html          # Web UI (dark mode, vanilla CSS)
├── _fonts/                 # Bundled DejaVu Sans fonts (for PDF)
├── requirements.txt
├── render.yaml             # Render deployment config
└── .gitignore
```

---

## ⚙️ How It Works

1. **Fetch** — Uses the [MediaWiki Action API](https://www.mediawiki.org/wiki/API:Main_page) (`?action=parse`) to fetch the page HTML without hitting bot-blockers
2. **Parse** — Splits each `<p>` block on `<br>` boundaries and classifies lines as:
   - `<b>Character:</b>` → dialogue
   - `<i>(text)</i>` → stage direction
   - Lines starting with ♪ → song
3. **Export** — Renders to the selected format(s) and zips them for download

---

## 🧰 Tech Stack

| Layer | Library |
|---|---|
| Web server | Flask + Gunicorn |
| Scraping | requests + BeautifulSoup4 (lxml) |
| PDF generation | fpdf2 + DejaVu Sans (Unicode font) |
| Word generation | python-docx |

---

## 📝 License

MIT — do whatever you want with it.

> Content scraped from Fandom wikis is user-contributed and licensed under [CC-BY-SA](https://www.fandom.com/licensing). This tool is for personal/educational use.
