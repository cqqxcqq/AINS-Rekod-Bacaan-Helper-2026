# 📚 AINS Book Automation Tool - Beginner's Guide

**Automatically submit books to AINS library system - No technical knowledge needed!**

---

## 🎯 What Does This Do?

This tool automatically adds books to AINS (library system) without you having to type each one manually.

**Before:** Type each book's details and click buttons 100+ times ❌  
**After:** Let the tool do it automatically ✅

---

## 📋 What You Need

### Files Required (Only 2!)
1. **`ains_auto.py`** - The automation script (comes with this)
2. **`book_malay.json`** - Your list of books (you create this)

### What to Install
- **Python** (free programming tool)
- **Google Chrome** browser
- **Groq API key** (free account)

### What You Need to Have
- Windows 10 or 11
- Internet connection
- AINS account with username/password
- List of books to add

---

## 🛠️ Step-by-Step Setup

### Step 1: Install Python

1. Go to [python.org](https://www.python.org/downloads/)
2. Download Python 3.x
3. Run the installer
4. **IMPORTANT:** Check the box that says "Add Python to PATH"
5. Click "Install Now"

**Test if it worked:**
- Open PowerShell (right-click desktop → "Open PowerShell here")
- Type: `python --version`
- You should see a version number

### Step 2: Get Your Groq API Key (Free!)

1. Go to [console.groq.com](https://console.groq.com/)
2. Click "Sign Up" and create free account
3. Log in
4. Click "API Keys" on the left
5. Click "Create New API Key"
6. Copy the long key (starts with `gsk_`)
7. **Save it somewhere safe!**

### Step 3: Create Your Book List

Create a file called `book_malay.json` in the same folder as `ains_auto.py`

Option A — Create JSON yourself (recommended):

1. Copy the example below into a new file named `book_malay.json`.
2. Fill in the required fields (see "Required Fields" section).

```json
[
  {
    "title": "Book Title Here",
    "author": "Author Name",
    "publisher": "Publisher Name",
    "pages": 156,
    "category": "Fiksyen",
    "language": "Bahasa Melayu",
    "summary": "What the book is about...",
    "moral": "What the reader learns..."
  }
]
```

Option B — Let the AI generate the JSON for you:

If you prefer, you can ask an AI assistant (ChatGPT or Groq chat) to generate `book_malay.json` for you. Use the prompt below and ask the assistant to reply ONLY with a valid JSON array (no extra text).

AI Prompt (copy/paste into the chat):

```
Create a JSON array of book objects for AINS automation. Each object must include the following fields: title, author, publisher, pages, category, summary, moral. Use realistic sample data for 5 books in Bahasa Melayu. Return only the JSON array and nothing else.
```

After you receive the JSON array from the AI, save it as `book_malay.json` in the same folder as `ains_auto.py`.

**Required fields:** `tajuk` (`title`), `penulis` (`author`), `penerbit` (`publisher`), `bilangan_mukasurat` (`pages`), `kategori` (`category`), `summary`, and `moral`. All these fields are required for reliable automation.

---

## ▶️ Run from Any IDE (VS Code, PyCharm, Thonny, etc.)

You can run the script directly from any IDE — no need to use PowerShell specifically.

1. Open your IDE and load the project folder (the folder that contains `ains_auto.py`).
2. In your IDE, open a terminal or run configuration.
3. Set the Groq API key in the terminal before running (example for PowerShell / Terminal):

```powershell
$env:GROQ_API_KEY = "your_api_key_here"
```

Or on macOS / Linux terminal:

```bash
export GROQ_API_KEY="your_api_key_here"
```

4. Run the script using your IDE's run button or from the terminal:

```bash
python ains_auto.py
```

5. When the browser opens, log in to AINS and navigate to: **Koleksi > Tambah Bahan** (Add Material), then return to your IDE/terminal and press Enter to start the automation.

Notes for IDE users:
- In VS Code: open the folder, use the integrated terminal (View → Terminal), set the env var, then run `python ains_auto.py`.
- In PyCharm: create a run configuration for `ains_auto.py` and set the environment variable `GROQ_API_KEY` in the configuration settings.

---

## ⚠️ Common Problems & Fixes

### 1. "Python is not recognized"
**Solution:** Python didn't install correctly
- Restart your computer
- Uninstall Python and reinstall
- Make sure you checked "Add Python to PATH"

### 2. "GROQ_API_KEY NOT SET"
**Solution:** You forgot to set the API key
- Copy the command from Step 3 above again
- Make sure you have YOUR actual key in it
- Press Enter after pasting

### 3. "book_malay.json not found"
**Solution:** File is named wrong or in wrong place
- Make sure filename is exactly: `book_malay.json`
- Make sure it's in the same folder as `ains_auto.py`
- Check spelling

### 4. Browser won't open
**Solution:**
- Make sure Chrome is installed (not Edge or Firefox)
- Restart your computer
- Check your internet connection

### 5. Script crashes or stops
**Solution:**
- Don't close the PowerShell window
- Wait 10 seconds
- If still broken, delete `progress.json` and start over

### 6. Login doesn't work
**Solution:**
- Check your AINS username/password
- Make sure your account is active
- Try logging in manually first

---

## 📊 What the Script Does

For each book, it automatically:

1. ✅ Enters the book title
2. ✅ Enters author name
3. ✅ Enters publisher name
4. ✅ Enters number of pages
5. ✅ Enters book summary
6. ✅ Enters moral/lesson
7. ✅ Selects category (automatically)
8. ✅ Selects language (automatically)
9. ✅ Clicks submit button
10. ✅ Confirms submission
11. ✅ Moves to next book

**No manual clicking needed after you press Enter!**

---

## 💾 Saving Your Progress

Progress is saved automatically in `progress.json`

- If script crashes → run again and it continues from where it stopped
- If you close browser → run again and it skips already-added books
- **To restart completely:** Delete `progress.json` file

---

## 🔄 Running Again Later

Next time you want to use the tool:

1. Open PowerShell in the folder
2. Set API key again: `$env:GROQ_API_KEY = "your_key"`
3. Run: `python ains_auto.py`
4. Log in when browser opens
5. Press Enter to continue

Already-added books will be automatically skipped.

---

## 🔁 Starting From Scratch

If you want to delete everything and start over:

1. Delete file: `progress.json` (if it exists)
2. Run: `python ains_auto.py`
3. Choose option **[1] 🔄 FRESH START**

---

## 📝 Book Data Format Tips

### Required Fields
- `"tajuk"` / `"title"` - Book title (MUST)
- `"penulis"` / `"author"` - Author name (MUST)
- `"penerbit"` / `"publisher"` - Publisher name (MUST)
- `"bilangan_mukasurat"` / `"pages"` - Number of pages (MUST)
- `"kategori"` / `"category"` - Book category/genre (MUST; use `Fiksyen` or `Bukan Fiksyen`)
- `"summary"` - Book summary / synopsis (MUST)
- `"moral"` - Moral / lesson (MUST)
- `"language"` - Language (optional but recommended)

### Notes
- Field names are accepted in English or Malay. Example: use `"title"` or `"tajuk"`, `"author"` or `"penulis"`.
  Provide all required fields to avoid validation errors during automation.

### Code reference (mapping)
The automation accepts either Malay or English keys and maps them internally. Provide any of the pairs below in your JSON:

```
title <-> tajuk
author <-> penulis
publisher <-> penerbit
pages <-> bilangan_mukasurat
category <-> kategori
summary <-> summary
moral <-> moral
```

Use the exact keys above (case-insensitive) to ensure the script matches fields correctly.

### Category Options
- `Fiksyen` / `Fiction`
- `Bukan Fiksyen` / `Non-Fiction`

---

## ✅ Before You Start Checklist

- [ ] Python 3.x installed
- [ ] Chrome browser installed
- [ ] Groq API key obtained
- [ ] `book_malay.json` file created
- [ ] `ains_auto.py` file in same folder
- [ ] AINS account username and password ready
- [ ] Internet connection working

---

## 🆘 When Something Goes Wrong

1. **Look at the error message** - it usually tells you what's wrong
2. **Check this guide** - look for your error in "Common Problems & Fixes"
3. **Close everything** - close Chrome, PowerShell, try again
4. **Restart computer** - fixes most problems
5. **Delete progress.json** - start completely fresh

---

## 📞 Need Technical Help?

If you need to contact someone, tell them:

1. **What error message you saw** (copy all the text)
2. **What step you were on**
3. **Take a screenshot** of the error
4. **Check the file:** `automation.log` (has technical details)

---

## 🔐 Keep Safe!

- ✅ Never share your Groq API key with anyone
- ✅ Never post your API key online
- ✅ Keep your AINS password safe
- ✅ Don't run multiple copies at the same time

---

## 📋 Files Created by Script

After running, you'll see these files (don't delete them!):

- `progress.json` - Keeps track of progress
- `automation.log` - Record of what happened
- `ains_stealth_profile/` - Browser data (for remembering login)
- `duplicates_detected.json` - Books already added

---

## 🎉 You're Ready!

Follow the steps above and your books will be added automatically!

**Questions?** Go back and read the relevant section above.

---

**Made with ❤️ for easy book automation**  
*Version 5.1 - February 2026*
```