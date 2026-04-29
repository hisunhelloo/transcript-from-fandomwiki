# 📜 Fandom Transcript Crawler

A web app that crawls any **Fandom wiki `/Transcript` page** and lets you download it as **Markdown**, **PDF**, or **Word (.docx)** — instantly, in your browser.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)
![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?logo=render)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 🌐 Live Demo

**[https://transcript-from-fandomwiki.onrender.com](https://transcript-from-fandomwiki.onrender.com)**

> ⚠️ Hosted on Render's free plan — the server sleeps after 15 min of inactivity.
> The **first visit after a period of inactivity may take ~30–60 seconds** to wake up. Subsequent requests are instant.

---

## ✨ Features

- 🔗 Paste any `*.fandom.com/wiki/*/Transcript` URL
- 📝 Export as **Markdown** (`.md`)
- 📄 Export as **PDF** (styled, character names highlighted in blue)
- 📃 Export as **Word** (`.docx`)
- 📦 All selected formats packed into a single `.zip` download
- ⚡ Runs entirely in-browser — no login, no database, no setup
- 🌐 Works across all Fandom wikis (Phineas and Ferb, Harry Potter, SpongeBob, etc.)

---

## 🖼️ How to Use

1. Open the [live app](https://transcript-from-fandomwiki.onrender.com)
2. Paste a Fandom transcript URL (e.g. `https://phineasandferb.fandom.com/wiki/Rollercoaster/Transcript`)
3. Check the formats you want — **Markdown**, **PDF**, **Word**
4. Click **Generate & Download**
5. A `.zip` file downloads automatically with your chosen files inside

---

## ⚙️ How It Works

```
User pastes URL
      ↓
Flask backend calls MediaWiki Action API (?action=parse)
      ↓
HTML parsed with BeautifulSoup
  • <b>Character:</b> → dialogue line
  • <i>(text)</i>    → stage direction
  • Lines with ♪     → song
      ↓
Rendered to selected format(s) — all in memory, no disk writes
      ↓
Packed into a .zip → downloaded to browser
```

**Why use the MediaWiki API instead of scraping directly?**
Fandom blocks plain `requests` with a 403. The public MediaWiki API (`/api.php`) is accessible without authentication and returns clean, structured HTML.

---

## 🛠️ Run Locally

### Requirements

- Python 3.11+

### Setup

```bash
git clone https://github.com/hisunhelloo/transcript-from-fandomwiki.git
cd transcript-from-fandomwiki

pip install -r requirements.txt
python app.py
```

Open [http://localhost:5000](http://localhost:5000)

### CLI (no web server needed)

```bash
# Default: Rollercoaster transcript → ./output/ as .md + .pdf
python crawl_transcript.py

# Custom URL
python crawl_transcript.py https://phineasandferb.fandom.com/wiki/Lawn_Gnome_Beach_Party_of_Terror/Transcript

# Markdown only, custom output dir
python crawl_transcript.py <URL> --format md --out ./transcripts

# All options
python crawl_transcript.py --help
```

---

## 📁 Project Structure

```
transcript-from-fandomwiki/
├── app.py                  # Flask server + all crawler/export logic
├── crawl_transcript.py     # Standalone CLI version
├── templates/
│   └── index.html          # Web UI (dark mode, vanilla HTML/CSS/JS)
├── _fonts/                 # Bundled DejaVu Sans TTF fonts (for PDF Unicode support)
│   ├── DejaVuSans.ttf
│   ├── DejaVuSans-Bold.ttf
│   └── DejaVuSans-Oblique.ttf
├── requirements.txt
├── render.yaml             # Render one-click deploy config
└── .gitignore
```

---

## 🧰 Tech Stack

| Layer | Tool |
|---|---|
| Web framework | Flask + Gunicorn |
| HTML fetching | `requests` + MediaWiki Action API |
| HTML parsing | BeautifulSoup4 + lxml |
| PDF export | fpdf2 + DejaVu Sans (Unicode-safe font) |
| Word export | python-docx |
| Hosting | Render (free tier) |

---

## 🚀 Deploy Your Own (Render — Free)

1. Fork this repo
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your forked repo
4. `render.yaml` is auto-detected — just click **Deploy**

No environment variables required.

---

## 📝 License

MIT — free to use, modify, and distribute.

> Transcript content on Fandom is user-contributed and licensed under [CC-BY-SA](https://www.fandom.com/licensing).
> This tool is intended for personal and educational use.
