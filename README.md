# Ledger — Financial Statement Analyzer

A web-based tool that lets credit analysts paste, upload, or drop in a company's financial statements and instantly receive structured ratios, trend analysis, and a plain-English credit summary.

**Built for:** BIS Self-Selected Coursework (James & Luke)
**Tech stack:** Python · Flask · Google Gemini API

---

## What it does

1. **Accepts financial data** in three formats: pasted text, PDF upload (10-Ks, annual reports), or Excel/CSV upload.
2. **Extracts the line items** from the source using Gemini (revenue, total assets, current liabilities, etc.).
3. **Calculates 11 financial ratios in deterministic Python code** — liquidity, profitability, leverage, and efficiency. No LLM math, so no hallucination risk.
4. **Generates a credit-analyst narrative** using Gemini — summary, strengths, concerns, red flags, and trend commentary.
5. **Lets you ask follow-up questions** about the analysis through an in-app chat.

---

## Architecture (the important part for the writeup)

The professor's feedback specifically warned that LLMs hallucinate when doing math. We addressed this directly by separating responsibilities:

```
INPUT (text/PDF/Excel)
        ↓
[Gemini API]  ← extracts numbers from text (no math, just reading)
        ↓
[Python]      ← calculates ALL ratios with deterministic code
        ↓
[Gemini API]  ← receives pre-calculated ratios, writes narrative analysis
        ↓
OUTPUT (ratios table + narrative + Q&A chat)
```

This separation means our ratios are always mathematically correct, while still benefiting from the LLM's strength in reading messy financial documents and writing professional analysis.

---

## Setup — first time only (~10 minutes)

### Step 1: Make sure you have Python installed

Open PowerShell and type:

```
python --version
```

You should see something like `Python 3.10.x` or higher. If you get an error, download Python from https://www.python.org/downloads/ and install it. **On Windows, make sure to check the box "Add python.exe to PATH" during installation.**

### Step 2: Get the project files onto your computer

If you downloaded a zip file, unzip it somewhere you'll remember (like Desktop).

In PowerShell, navigate into the project folder. For example:

```
cd $HOME\Desktop\financial-analyzer-gemini
```

(If your Desktop is synced to OneDrive, the path will be `$HOME\OneDrive\Desktop\financial-analyzer-gemini`.)

### Step 3: Create a virtual environment

```
python -m venv venv
```

Activate it:

- **Windows (PowerShell):** `venv\Scripts\Activate.ps1`
- **Mac/Linux:** `source venv/bin/activate`

After activation, your terminal prompt should show `(venv)` at the beginning.

### Step 4: Install the required packages

```
pip install -r requirements.txt
```

Takes 1-3 minutes. You should see a `Successfully installed...` line at the end.

### Step 5: Get your free Gemini API key

This is the easy part. **No credit card. No phone verification. No paywall.**

1. Go to **https://aistudio.google.com/apikey**
2. Sign in with any Google account.
3. Click **Create API key** (top right).
4. Pick "Create API key in new project" if prompted.
5. A long string starting with `AIza...` will appear. Copy it.

That's it. You now have free access to Gemini's API. The free tier gives you ~1,500 requests per day, way more than you'll need for development and demos.

### Step 6: Create your `.env` file

In the project folder, copy the example file:

- **Windows:** `copy .env.example .env`
- **Mac/Linux:** `cp .env.example .env`

Open `.env` in Notepad:

```
notepad .env
```

Replace `your-key-goes-here` with the API key you copied:

```
GEMINI_API_KEY=AIzaSy...your-actual-key
```

Save and close.

**⚠️ Common Windows gotcha:** If Notepad saves it as `.env.txt`, the app won't find it. Verify with `dir .env*` — you should see exactly `.env`, not `.env.txt`. If wrong, run `ren .env.txt .env`.

---

## Running the app

Every time you want to use the app:

1. Open PowerShell and navigate to the folder:
   ```
   cd $HOME\OneDrive\Desktop\financial-analyzer-gemini
   ```
2. Activate the virtual environment:
   ```
   venv\Scripts\Activate.ps1
   ```
3. Run:
   ```
   python app.py
   ```
4. Open your browser to **http://127.0.0.1:5000**

To stop: press **Ctrl+C** in the PowerShell window.

---

## How to use it

1. Pick an input method at the top: Paste Text, Upload PDF, or Upload Excel/CSV.
2. Provide the financial data — multi-period data works best (e.g., FY2023 and FY2024) so trend analysis appears.
3. Click **Run Analysis**. Takes about 10-20 seconds.
4. The results section appears with company info, ratios, trends, and narrative.
5. Use the **Follow-up Questions** chat to dig deeper into anything in the analysis.

The **Load example data** button gives you a sample two-period income statement to play with.

---

## File structure

```
financial-analyzer-gemini/
├── app.py              Flask routes + file parsing
├── analyzer.py         Core logic: extraction, ratio math, narrative
├── requirements.txt    Python packages
├── .env.example        Template — copy to .env and add your API key
├── README.md           This file
├── templates/
│   └── index.html      The web page
└── static/
    ├── style.css       Styling
    └── app.js          Frontend interaction
```

---

## Troubleshooting

**"GEMINI_API_KEY is not set"** — You forgot to create the `.env` file or didn't paste your key into it.

**"ModuleNotFoundError"** — The virtual environment isn't activated, or install didn't finish. Re-activate and re-run `pip install -r requirements.txt`.

**Browser shows "site can't be reached"** — Make sure the terminal is still running `app.py`. If it crashed, restart.

**API errors / 401 Unauthorized** — Your API key is wrong. Check `.env` for typos.

**Rate limit errors (429)** — The free tier allows ~10 requests per minute on the Flash model. If you hit this, just wait 60 seconds and try again. You're unlikely to hit it during normal use.

---

## Notes on AI use (for the writeup)

- The application uses the **Gemini API** as a runtime dependency — it's the analytical engine.
- **Note on the technology change:** This project was originally proposed using Anthropic's Claude API. After Phase 3 approval, we discovered that Anthropic's free credit program had changed and required a paid plan to access the API. Rather than spend money on the project, we evaluated alternatives and ported the application to Google's Gemini API. The architectural separation (Python for math, LLM for reading/writing) made the port straightforward — only the API client code changed; the Flask app, prompts, ratio calculations, and frontend were unaffected. This is a real-world example of why decoupling business logic from third-party APIs matters.
- All financial math is **deliberately handled in Python** so that calculated values are mathematically guaranteed regardless of the LLM. The LLM is used for what it's actually good at: reading messy text and writing professional prose.
