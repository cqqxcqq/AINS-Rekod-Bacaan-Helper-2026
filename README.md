
# 📚 AINS Book Entry Helper

An automation tool that automatically fills in book details on the [AINS library website](https://ains.moe.gov.my/) (Nilam) using Python and AI.

---

## 🛠 Prerequisites

### 1. Install Python
Download and install Python 3.10 or higher from [python.org](https://www.python.org/downloads/). 
**Important:** During installation, check the box that says **"Add Python to PATH"**.

### 2. Install Required Packages
Open your Terminal or PowerShell and run these commands to install the automation engine and the AI library:
```bash
pip install groq playwright
playwright install chromium
```

### 3. Get a Groq API Key
This tool uses AI to process book data.
1. Go to [console.groq.com](https://console.groq.com/).
2. Create a free account.
3. Generate an **API Key** and save it.

---

## 📥 How to Get the Script

You have two options to get the tool:

### Option A: Clone the Repository (Recommended)
If you have Git installed, run:
```bash
git clone https://github.com/YOUR_USERNAME/ains-automation.git
cd ains-automation
```

### Option B: Manual Download (No Git needed)
1. Create a new folder on your computer.
2. Create a file named `ains_automation.py` and paste the script code inside.
3. Create a file named `book_malay.json` in the same folder.

---

## 📋 Prepare Your Book List

Your `book_malay.json` file should look like this. You can add as many books as you like:

```json
[
  {
    "title": "Hikayat Merong Mahawangsa",
    "author": "Anonymous",
    "publisher": "DBP",
    "pages": 120,
    "summary": "Kisah klasik mengenai pengasasan negeri Kedah...",
    "moral": "Kesetiaan dan keberanian adalah sifat yang terpuji."
  }
]
```

---

## 🚀 Setup & Running

### 1. Set the API Key
Every time you open a new terminal to run the script, you must set your key:

**Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY = "your-actual-key-here"
```

**Mac/Linux:**
```bash
export GROQ_API_KEY="your-actual-key-here"
```

### 2. Run the Script
```bash
python ains_automation.py
```

### 3. Follow these steps once the browser opens:
1. **Log in** to your AINS account manually.
2. Click on **Koleksi** -> **Tambah Bahan**.
3. Once you see the form, go back to your **Terminal** and press **Enter**.
4. The script will now start filling in all the books from your JSON file automatically.

---

## 🕹 Controls & Features

*   **Progress Tracking:** The script creates a `ains_progress.json` file. If the script crashes or you stop it, it will resume from the last successful book.
*   **Reset:** To start from the very first book again, run:
    ```bash
    python ains_automation.py --reset
    ```
*   **Pause:** Press `Ctrl + C` in the terminal to stop the process safely.

---

## 🔍 Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError` | Run `pip install groq playwright` again. |
| `Playwright Error` | Run `playwright install chromium` to download the browser engine. |
| `API Key Error` | Ensure you typed `$env:GROQ_API_KEY` correctly in PowerShell. |
| `File Not Found` | Ensure `book_malay.json` is in the exact same folder as the script. |

---

## 🤝 Contributing
Feel free to fork this project, report bugs, or submit pull requests to improve the automation logic.

**Disclaimer:** This tool is intended for personal educational use. Please ensure all book entries are honest and accurate.
```
