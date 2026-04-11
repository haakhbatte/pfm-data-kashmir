# J&K Budget Data Extraction Pipeline

This is a three-stage Python pipeline for extracting structured budget data from scanned government budget PDFs (Jammu & Kashmir). The pipeline handles multilingual documents (English, Hindi, Urdu), OCR noise correction, hierarchical budget classification, and produces clean Excel reports. Please note that the excel files so extracted were carefully reviewed, given the sensitivity of the financial data.

---

## Table of Contents

- [Overview](#overview)
- [Pipeline Architecture](#pipeline-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output Format](#output-format)
- [Data Quality Flags](#data-quality-flags)
- [Known Limitations](#known-limitations)
- [Notes for Developers](#notes-for-developers)

---

## Overview

Government budget PDFs are often scanned images rather than machine-readable text. This pipeline automates the full extraction workflow (three stages):

1. **OCR & Raw Parsing** — Convert scanned PDFs to text and extract a full budget table with hierarchical context.
2. **Refinement & Cleaning** — Re-parse the raw text with improved logic, correct OCR errors, and standardize item names using a lookup dictionary.
3. **Final Reporting** — Verify categories (Revenue vs Capital), cross-check extracted totals against reported Grand Totals, and produce a formatted Excel report with live SUMIF formulas.

---

## Pipeline Architecture

```
Scanned Budget PDFs
        │
        ▼
┌─────────────────────────────────────┐
│  Stage 1: 1_budget_parser_fulltable │  OCR via Tesseract + pdf2image
│  Input:  Data/2025-2026/*.pdf        │  Produces .txt + .xlsx per PDF
│  Output: 2025-26/Extracted/          │
└─────────────────────────────────────┘
        │  .txt files (OCR output)
        ▼
┌─────────────────────────────────────┐
│  Stage 2: 2_extraction_refinement   │  Refined parsing + item_dict lookup
│  Input:  Data/2025-2026/*.txt        │  Produces cleaned .xlsx per file
│  Output: 2025-26/Cleaned_Items/      │
└─────────────────────────────────────┘
        │  cleaned .xlsx + .txt + .pdf
        ▼
┌─────────────────────────────────────┐
│  Stage 3: 3_final_extraction        │  Category verification + reporting
│  Input:  2025-26/Cleaned_Items/      │  Produces final Excel report
│  Output: 2025-26/Final_Extracted/    │
└─────────────────────────────────────┘
        │
        ▼
  Final Excel Reports
  (Extracted Data + Account Totals + Category Lookup)
```

> **Important:** PDF filenames must follow the naming convention `{number}_{department-name}.pdf`
> (e.g., `01_General_Administration.pdf`). The pipeline uses the numeric prefix to match
> source `.txt`, `.pdf`, and cleaned `.xlsx` files across stages.

---

## Prerequisites

### System Dependencies

| Tool | Purpose | Download |
|---|---|---|
| **Python 3.9+** | Runtime | https://www.python.org |
| **Tesseract OCR** | PDF text extraction | https://github.com/tesseract-ocr/tesseract |
| **Poppler** | PDF-to-image conversion | https://github.com/oschwartz10612/poppler-windows/releases (Windows) |
| **Hindi + Urdu Tesseract language packs** | Multilingual OCR | Install via Tesseract installer or manually |

### Python Libraries

See `requirements.txt`. Key dependencies:

```
pytesseract
pdf2image
Pillow
numpy
pandas
openpyxl
pdfplumber
```

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd <repo-name>
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Tesseract OCR** and add it to your system PATH.

4. **Install Poppler** and note the installation path (needed in Stage 1 configuration).

5. **Install Hindi/Urdu language packs** for Tesseract if the source PDFs contain Devanagari or Urdu script.

---

## Configuration

Before running any script, update the path and year variables as needed.

### Stage 1 — `1_budget_parser_fulltable.py`

```python
# Line ~10: Restrict to a single file for testing (set to None to process all)
LIMIT_TO_FILE = "01_General_Administration.pdf"

# Line ~16: Update to your actual Poppler installation path
poppler_path=r"C:\Program Files\poppler-24.08.0\Library\bin"

# Bottom of file: Set input/output folder paths
input_folder  = r"Data\2025-2026"
output_folder = r"2025-26\Extracted"
```

### Stage 2 — `2_extraction_refinement.py`

```python
# Restrict to a single file for testing (set to None to process all)
LIMIT_TO_FILE = None

# Bottom of file: Set input/output folder paths and base year
input_folder  = r"Data\2025-2026"
output_folder = r"2025-26\Cleaned_Items"
base_year     = 2025          # The first year in the budget year (e.g., 2025 for 2025-26)
```

### Stage 3 — `3_final_extraction.py`

```python
# Restrict to a single file for testing
LIMIT_TO_FILE = None

# Bottom of file: Set folder paths
CLEANED_DIR  = r"2025-26\Cleaned_Items"
TXT_DIR      = r"Data\2025-2026"
REPORTS_DIR  = r"2025-26\Final_Extracted"
```

> **Tip:** Use `LIMIT_TO_FILE` in each script when testing on a single department PDF before
> running the full batch. Set it to `None` to process all files.

---

## Usage

Run the scripts **in order**, one stage at a time:

```bash
# Stage 1: OCR extraction
python 1_budget_parser_fulltable.py

# Stage 2: Refinement and cleaning
python 2_extraction_refinement.py

# Stage 3: Final report generation
python 3_final_extraction.py
```

Each script will print progress to the console, including detected year labels,
discrepancies, and any data quality warnings.

---

## Output Format

Each final Excel report (Stage 3 output) contains three sheets:

| Sheet | Contents |
|---|---|
| **Extracted Data** | One row per budget line item with full hierarchical context, monetary values, and a `Category` column (Revenue/Capital) populated via VLOOKUP |
| **Account Totals** | Per-year summary with Revenue, Capital, Total, Reported Grand Total, and a `CHECK` column comparing extracted vs. reported totals |
| **CategoryLookup** | Hidden reference sheet mapping Major Head numbers to Revenue/Capital (used internally by formulas) |

### Column Reference (Extracted Data sheet)

| Column | Description |
|---|---|
| `Demand` | Demand grant number |
| `Sector_num / _nam` | Sector code and name |
| `MajorHead_num / _nam` | 4-digit Major Head |
| `SubMajorHead_num / _nam` | 2-digit Sub Major Head |
| `MinorHead_num / _nam` | 3-digit Minor Head |
| `GroupHead_num / _nam` | Group Head |
| `SubHead_num / _nam` | Sub Head |
| `Dept_num / _nam` | Department code and name |
| `Item_num` | 3-digit item/object code |
| `Item_nam` | Cleaned item name (standardized via `item_dict.py`) |
| `YYYY-YY_accounts` | Actuals for previous year |
| `YYYY-YY_estimates` | Budget estimates |
| `YYYY-YY_revisedestimate` | Revised estimates |
| `*_Original` | Raw pre-cleaning value (Stage 2) |
| `*_Error` | OCR error or outlier flag per year column |
| `Data_Check` | Row-level data quality status |
| `Spill_Check` | Detects OCR spill (item code bleeding into value column) |
| `Category` | Revenue or Capital (from VLOOKUP) |

---

## Data Quality Flags

| Flag | Meaning |
|---|---|
| `OK` | No issues detected |
| `OCR Error` | Value could not be parsed as a number |
| `Outlier` | Value exceeds 3× standard deviation from the column mean |
| `OCR Error, Outlier` | Both conditions apply |
| `Suspicious Zero` | Value is zero (may be a missed extraction) |
| `CORRECTED` | Item code had OCR character substitution corrected (e.g., `O`→`0`) |
| `MISSING_CODE` | Row had valid values but no item code was found |
| `MISSING_HEAD_NUMBER` | A budget head was found without a corresponding code |
| `SPILL` | Item code value matches the first financial column (data column misalignment) |
| `CHECK` | General flag — requires manual review |

---

## Known Limitations

- **Poppler path is hardcoded** in Stage 1. Update this before running on a new machine.
- **`base_year`** in Stage 2 must be updated manually when processing a new budget year.
- The pipeline is optimized for J&K government budget PDFs from **2013-14 to 2025-26**.
  Year detection logic includes special cases for several fiscal years; PDFs from other
  governments or years may need additional handling.
- OCR quality depends on the scan resolution. Low-quality scans may produce higher rates
  of `OCR Error` flags.
- `item_dict.py` must be present in the same directory as `2_extraction_refinement.py`.
  This file is **not auto-generated** — it must be maintained separately.

---

## Notes for Developers

- **Testing a single file:** Set `LIMIT_TO_FILE = "filename"` at the top of any script
  to restrict processing to one file. This is useful for debugging.
- **Adding a new budget year:** Update `base_year` in Stage 2 and add a year-specific
  branch in the `detect_years()` function in Stage 1 if the column structure differs.
- **Extending item names:** Add entries to `item_dict.py` using the format
  `{"001": "Salaries", "002": "Wages", ...}` to improve name standardization.
- **Verification logic:** Stage 3 compares the sum of extracted values against the
  reported Grand Total from the source text. A `CHECK` in the `Account Totals` sheet
  indicates a discrepancy worth investigating.
- **OCR caching:** Stage 1 saves `.txt` files alongside source PDFs. On re-runs,
  it reads from these cached files instead of re-running OCR, saving significant time.

---

*Pipeline developed for research and analysis of J&K government demand grants.*
