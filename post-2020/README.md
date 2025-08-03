# 📊 Budget Data Extraction and Cleaning Pipeline (Post-2020)

This folder contains the pipeline for extracting, cleaning, and validating **budget data from 2021-22 onwards**. The processing structure remains largely identical to earlier years, with minor adjustments for newer PDF formats.

---

## ⚠️ What Changed Post-2020?

- Budget PDFs are now **more consistent and cleaner**, using **Hindi** text instead of Urdu.
- Item-level tables have **4 columns** (same as pre-2020), unlike the 5-column format used in 2020-21.
- A dedicated script is used to handle these minor adjustments.

---

## 🛠️ Pipeline Overview

### ✅ Step 1: Extract Full Table from PDFs
- **Script:** `budget_parser_fulltable.py`  
- **Input:** Budget PDFs  
- **Output:** `.txt` files (one per demand)  

**Description:**
- Extracts complete tabular data, including:
  - Head hierarchies
  - Item codes and names
  - Voted/Charged and Plan/Non-Plan labels

---

### ✅ Step 2: Extract Heads and Departments with Outlier Detection
- **Script:** `extract_heads_departments_with_outliers_post-2020.py`  
- **Input:** `.txt` files from Step 1  
- **Output:** Cleaned Excel files  

**Description:**
- Parses 4-column item-level tables (standardized post-2020 format).
- Detects numeric outliers (3σ rule).
- Cleans up garbage characters.
- Supports Hindi-based text extraction.

---

### ✅ Step 3: Match Item Codes to Standard Names
- **Script:** `match_items_with_dictionary.py`  
- **Input:** Excel files from Step 2  
- **Output:** Excel files with standardized item names  

**Description:**
- Matches extracted names to official names using `ITEM_DICT`.

---

### ✅ Step 4: Copy Cleaned Data to Final Extracted Files and Summarize
- **Script:** `copy_to_extracted_and_summarize.py`  
- **Input:** Matched Excel + original extracted files  
- **Output:** Final Excel files with summary  

**Description:**
- Copies final data to an Excel workbook.
- Adds an `accounts_total` summary sheet.

---

### ✅ Step 5: Rename Final Output Files
- **Script:** `rename_cleaned_files.py`  
- **Output:** Renamed files (e.g., `2021-22_05_Education_Cleaned.xlsx`)

---

## ✅ Benefits of Post-2020 Data

- Cleaner OCR due to Hindi instead of Urdu.
- Standard 4-column structure eases parsing.
- Fewer text-cleaning edge cases than in older versions.

---

📁 Use this folder for **budgets from 2021-22 onward**.  
Refer to:
- `/pre-2020/` for older Urdu-based PDFs  
- `/2020/` for the transitional 5-column structure specific to 2020-21 only

