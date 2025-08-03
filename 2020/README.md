# 📊 Budget Data Extraction and Cleaning Pipeline (2020-21)

This folder contains a tailored pipeline for extracting and validating **budget data for the fiscal year 2020-21**, which introduced significant structural differences compared to earlier years.

---

## ⚠️ Why a Separate Folder for 2020-21?

- Starting 2020:
  - **Urdu** was replaced with **Hindi** in budget PDFs.
  - Item-level tables include **5 columns** instead of the 4 used before and after.
- These changes required script-level modifications, especially in text parsing and structure handling.

---

## 🛠️ Pipeline Overview

### ✅ Step 1: Extract Full Table from PDFs
- **Script:** `budget_parser_fulltable.py`  
- **Input:** Budget PDFs  
- **Output:** Structured `.txt` files (one per demand)  

**Description:**
- Extracts raw tabular data.
- Captures:
  - Head hierarchies
  - Item codes and names
  - Voted/Charged and Plan/Non-Plan tags

---

### ✅ Step 2: Extract Heads and Departments with Outlier Detection
- **Script:** `extract_heads_department_with_outliers_2020.py`  
- **Input:** `.txt` files from Step 1  
- **Output:** Cleaned Excel files  

**Description:**
- Parses head hierarchy and item-level financials from 5-column tables.
- Applies:
  - 3σ rule for numeric outlier detection
  - OCR error checks
  - Text cleaning (removes garbage and non-Hindi characters)

---

### ✅ Step 3: Match Item Codes to Standard Names
- **Script:** `match_items_with_dictionary.py`  
- **Input:** Excel files from Step 2  
- **Output:** Excel files with standardized item names  

**Description:**
- Maps extracted item names to official names using `ITEM_DICT`.

---

### ✅ Step 4: Copy Cleaned Data to Final Extracted Files and Summarize
- **Script:** `copy_to_extracted_and_summarize.py`  
- **Input:** Files from Step 3 + original extracted Excel files  
- **Output:** Final Excel files with a summary sheet  

**Description:**
- Copies validated data to final Excel workbooks.
- **Adds an `accounts_total` summary sheet** (⚠️ *currently not working as expected*).

---

### ✅ Step 5: Rename Final Output Files
- **Script:** `rename_cleaned_files.py`  
- **Output:** Cleaned, renamed files (e.g., `2020-21_01_Health_Cleaned.xlsx`)

---

## ⚠️ Known Issues (2020 Version)

- ❌ **Multi-line head names** are **not parsed correctly** in this version and may lead to truncated or incorrect entries.
- ❌ The final output **does not contain the `accounts_total` summary sheet** — this needs to be fixed in `copy_to_extracted_and_summarize.py`.

---

## 🗂️ Folder Usage

This folder is **exclusively for 2020-21** data, which has a different format.  
Refer to:
- `/pre-2020/` for older budgets (with Urdu)
- `/post-2020/` for later budgets (4-column tables with stable Hindi text)

