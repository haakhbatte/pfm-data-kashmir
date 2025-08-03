# 📊 Budget Data Extraction & Cleaning Pipeline (Upto 2019-20)

This repository contains a multi-step pipeline for **extracting, cleaning, and validating** budget data from government PDF documents. The workflow handles OCRed content, maps item codes to standardized names, and detects data inconsistencies.

---

## 🛠️ Pipeline Overview

### ✅ Step 1: Extract Full Table from PDFs
- **Script:** `budget_parser_fulltable.py`  
- **Input:** Budget PDFs  
- **Output:** Structured `.txt` files (one per demand)  

**Description:**
- Extracts all tabular data from PDFs.
- Captures:
  - Head hierarchies (Sector, Major Head, Sub Major Head, etc.)
  - Item codes and names
  - Voted/Charged and Plan/Non-Plan labels

---

### ✅ Step 2: Extract Heads and Departments with Outlier Detection
- **Script:** `extract_heads_departments_with_outliers.py`  
- **Input:** `.txt` files from Step 1  
- **Output:** Cleaned Excel files  

**Description:**
- Parses head hierarchies and financial data.
- Detects OCR errors in numeric fields.
- Flags outliers using the **3σ rule**.
- Cleans text (removes garbage and Urdu characters).

---

### ✅ Step 3: Match Item Codes to Standard Names
- **Script:** `match_items_with_dictionary.py`  
- **Input:** Cleaned Excel files from Step 2  
- **Output:** Excel files with standardized item names  

**Description:**
- Replaces raw item names with official names from `ITEM_DICT`.
- Ensures consistent naming across years and demands.

---

### ✅ Step 4: Copy Cleaned Data to Final Extracted Files and Summarize
- **Script:** `copy_to_extracted_and_summarize.py`  
- **Input:** Files from Step 3 + original extracted Excel files  
- **Output:** Final Excel files with summary sheet  

**Description:**
- Copies cleaned data into the final output file.
- Adds a summary sheet with account totals.

---

### ✅ Step 5: Rename Final Output Files
- **Script:** `rename_cleaned_files.py`  
- **Input:** Final Excel files  
- **Output:** Renamed files (e.g., `Demand_01_Health_Cleaned.xlsx`)  

**Description:**
- Standardizes output filenames.
- Useful for automation and archival.

---

## ⚠️ Known Limitations

- `extract_heads_departments_with_outliers.py` **does not extract** Voted/Charged or Plan/Non-Plan information. Use `budget_parser_fulltable.py` for that.
- Some head names may be **skipped** due to OCR garbage characters — manual review is advised.
- **Urdu/Arabic characters** may still occasionally break parsing. A filter (`strip_urdu`) is applied but not foolproof.

---

📁 Designed for budget data **up to 2019-20**. Folder-specific scripts maintained in `/pre-2020`.

