# 📚 AINS Book Entry Helper

A simple tool that automatically fills in book details on the [AINS library website](https://ains.moe.gov.my/) so you don't have to do it by hand.

---

## What Is This?

You give it a list of books (titles, authors, summaries, etc.) in a file, and it types everything into the AINS website for you — clicking buttons, filling forms, and moving to the next book — all on its own. You just watch.

---

## What You Need

| Requirement | Where to Get It |
|---|---|
| **Python 3.10+** | [python.org/downloads](https://www.python.org/downloads/) *(tick "Add to PATH" during install)* |
| **Groq API Key** (free) | [console.groq.com](https://console.groq.com/) → API Keys → Create |
| **Google Chrome** | [google.com/chrome](https://www.google.com/chrome/) |

---

## Setup (One-Time)

Open your terminal (PowerShell on Windows) and run these commands:

pip install groq playwright
playwright install chromium
Then set your AI key:

Windows (PowerShell):

PowerShell

$env:GROQ_API_KEY = "your-key-here"
Mac/Linux:

Bash

export GROQ_API_KEY="your-key-here"
⚠️ You need to set the key each time you open a new terminal window.

## Prepare Your Book List
Create a file called book_malay.json in the same folder as the script:

JSON

[
  {
    "title": "Hikayat Merong Mahawangsa",
    "author": "Anonymous",
    "publisher": "DBP",
    "pages": 120,
    "summary": "A classic tale of the founding of Kedah...",
    "moral": "Loyalty and courage are important virtues."
  }
]
Field	Required?
title	✅ Yes
author, publisher, pages	Recommended
summary, moral	Recommended
category, language	Optional
The tool auto-detects the language from your text.

## How to Run
Bash

cd path/to/your/folder
python ains_automation.py
Then follow the on-screen steps:

Log in to AINS manually in the browser that opens
Navigate to Koleksi → Tambah Bahan
Press Enter in the terminal to start
The tool handles everything from there. You'll see live progress like:

text

📖 [1/30] Hikayat Merong Mahawangsa
   ✅ completed!
📖 [2/30] Konserto Terakhir
   ✅ completed!
Useful Controls
Action	How
Pause	Press Ctrl+C
Resume later	Run the script again — it remembers progress
Start fresh	Run with --reset flag
See all options	Run with --help flag
## Troubleshooting
Problem	Fix
GROQ_API_KEY NOT SET	Set your key (see Setup above)
Book data file not found	Put book_malay.json in the same folder as the script
Browser opens but nothing happens	Log in first, navigate to the form, then press Enter
Session expired	Log in again when prompted
Same book keeps failing	Skip it and enter manually
## Contributing
Contributions are welcome! If you'd like to improve this tool:

Fork this repository
Create a branch for your change (git checkout -b my-fix)
Commit your changes (git commit -m "describe your change")
Push to your branch (git push origin my-fix)
Open a Pull Request with a clear description of what you changed and why
Bug reports, feature suggestions, and documentation improvements are all appreciated.

