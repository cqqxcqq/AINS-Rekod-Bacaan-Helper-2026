What Is This?
This tool automatically fills in book information on the AINS library website (used by Malaysia's Ministry of Education) so you don't have to type each book's details by hand. You give it a list of books (titles, authors, summaries, etc.), and it enters them into the website one by one — clicking buttons, filling forms, and moving to the next book — all on its own.

Think of it as a tireless assistant that does the repetitive data-entry clicking and typing for you, while you supervise.

How It Helps You
If you've ever had to enter dozens of books into the AINS system manually, you know how exhausting it is: type the title, pick the language, paste the summary, click "Next," click "Submit," click "Confirm," then start all over again.

This tool does all of that automatically. It:

Saves hours of repetitive work — it processes up to 30 books in a single session without you lifting a finger.
Remembers where it stopped — if something goes wrong or you need a break, it picks up right where you left off.
Skips duplicates — it won't re-enter a book you've already submitted.
Tries to fix its own mistakes — if something unexpected happens on the website (a pop-up, a missing button), it uses AI to figure out what went wrong and recover.
Preparation (What You Need Before Starting)
Before using this tool, you need to set up a few things on your computer. Follow these steps carefully.

Step 1: Install Python
Python is the programming language this tool is written in. Your computer needs it to run the tool.

Go to python.org/downloads
Download Python 3.10 or newer for your operating system (Windows, Mac, etc.)
Important (Windows users): During installation, check the box that says "Add Python to PATH"
Finish the installation
To verify it worked: Open your terminal (on Windows, search for "PowerShell" in the Start menu) and type:

text

python --version
You should see something like Python 3.12.4. If you see an error, Python wasn't installed correctly.

Step 2: Install Required Tools
This tool relies on a few helper programs. Open your terminal and run these commands one at a time:

text

pip install groq
text

pip install playwright
text

playwright install chromium
What these do (in plain English):

Command	What It Installs
pip install groq	Connects the tool to an AI service (Groq) that helps it understand what's on the screen
pip install playwright	Lets the tool control a web browser automatically
playwright install chromium	Downloads the actual browser the tool will use behind the scenes
Step 3: Get a Groq AI Key (Free)
The tool uses a free AI service called Groq to "read" the website and make smart decisions. You need a key to use it.

Go to console.groq.com
Sign up for a free account
Go to API Keys and click Create API Key
Copy the key (it looks like a long string of letters and numbers)
Now tell your computer about the key. In your terminal:

Windows (PowerShell):

PowerShell

$env:GROQ_API_KEY = "paste-your-key-here"
Mac/Linux:

Bash

export GROQ_API_KEY="paste-your-key-here"
⚠️ Note: You need to do this step every time you open a new terminal window, unless you add it to your system's permanent settings.

Step 4: Prepare Your Book List
The tool reads book information from a file called book_malay.json. This file must be in the same folder as the tool itself.

The file should look like this (you can have as many books as you want):

JSON

[
  {
    "title": "Hikayat Merong Mahawangsa",
    "author": "Anonymous",
    "publisher": "DBP",
    "pages": 120,
    "category": "Fiksyen",
    "summary": "A classic tale of the founding of Kedah...",
    "moral": "Loyalty and courage are important virtues."
  },
  {
    "title": "Konserto Terakhir",
    "author": "Abdullah Hussain",
    "publisher": "DBP",
    "pages": 200,
    "category": "Fiksyen",
    "summary": "The story of a musician facing life's challenges...",
    "moral": "Perseverance leads to success."
  }
]
What each piece means:

Field	What to Put Here	Required?
title	The book's title	✅ Yes
author	Who wrote it	Recommended
publisher	The publishing company	Recommended
pages	Number of pages	Recommended
category	Genre (e.g., "Fiksyen", "Bukan Fiksyen")	Optional
summary	A short summary of the book	Recommended
moral	The lesson or moral value	Recommended
💡 Tip: The tool automatically detects whether the book is in Malay, English, Chinese, Tamil, or Arabic based on the text you provide. You don't need to specify the language manually (though you can, with a "language" field).

How to Use It (Step by Step)
1. Open Your Terminal and Navigate to the Tool's Folder
If the tool is saved in a folder called BookHelper on your Desktop:

Windows:

PowerShell

cd C:\Users\YourName\Desktop\BookHelper
Mac/Linux:

Bash

cd ~/Desktop/BookHelper
2. Set Your AI Key (If You Haven't Already)
Windows:

PowerShell

$env:GROQ_API_KEY = "paste-your-key-here"
Mac/Linux:

Bash

export GROQ_API_KEY="paste-your-key-here"
3. Run the Tool
text

python ains_automation.py
(Replace ains_automation.py with whatever the script file is actually named.)

4. Follow the On-Screen Instructions
When the tool starts, it will:

Open a browser window pointing to the AINS website
Ask you to log in manually — type your AINS username and password as you normally would
Ask you to navigate to the book entry page (Koleksi → Tambah Bahan)
Wait for you to press Enter — once you're on the right page, press Enter in the terminal
Start working! — it will begin entering books automatically
While it runs, you'll see a live log in your terminal showing what it's doing:

text

📖 [1/30] Hikayat Merong Mahawangsa
   🌐 Bahasa Melayu | ⏱️ ETA: Calculating...
📝 Phase 1: Basic Information
   ✏️ Filled 4 fields
📝 Phase 2: Summary & Moral
   ✏️ Filled 2 fields
📤 Phase 4: Submit
✔️ Phase 5: Confirm
✅ 'Hikayat Merong Mahawangsa' completed!
5. When It's Done
The tool will show you a final summary:

text

📊 AUTOMATION COMPLETE - FINAL SUMMARY
   ✅ Successful:  28
   ❌ Failed:      1
   🔁 Duplicates:  1
   ⏩ Skipped:     0
   🎯 Success rate: 96.6%
Helpful Extras
Pausing and Resuming
To pause: Press Ctrl+C on your keyboard. The tool will ask if you want to continue, retry, or exit.
To resume later: Just run the tool again. It will ask whether you want to pick up where you left off or start fresh.
If Something Goes Wrong
The tool is designed to handle most problems on its own. If it can't fix an issue:

It skips that book and moves on to the next one
It saves your progress so nothing is lost
Failed books are listed at the end so you can enter them manually
Optional Settings (For Advanced Use)
You can add these flags when running the tool to change its behavior:

Flag	What It Does
--reset	Erases all progress and starts completely fresh
--debug	Shows extra-detailed information (useful if reporting a problem)
--screenshots	Saves pictures of the screen when errors happen
--no-duplicate-check	Turns off duplicate detection
--help	Shows all available options
Example:

text

python ains_automation.py --debug --screenshots
Troubleshooting Common Issues
Problem	Solution
"GROQ_API_KEY NOT SET"	You forgot to set your AI key. See Step 3 in Preparation.
"Book data file not found"	Make sure book_malay.json is in the same folder as the script.
The browser opens but nothing happens	Make sure you logged in and navigated to the book entry page, then pressed Enter.
The tool keeps failing on the same book	That book might have unusual data. Skip it and enter it manually.
"Session expired"	Your AINS login timed out. Log in again when prompted.
Purpose & Usage
Acknowledgment: This tool was developed specifically to reduce physical fatigue and repetitive clicking. It is designed as an assistive utility to prevent strain, not as a tool for mass automation.
