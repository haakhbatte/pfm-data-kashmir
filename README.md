# 🧾 Budget Data Extraction and Cleaning Pipeline

This repository contains a modular pipeline for extracting, cleaning, and standardizing **Indian government budget data** from scanned PDF documents.  
It supports different formats used across the years and applies OCR handling, outlier detection, and structured Excel output.

---

## 📁 Folder Structure

### ▶️ [`pre-2020/`](./pre-2020)
- Handles budget PDFs **up to FY 2019-20**.
- Text in PDFs includes **Urdu**, requiring additional cleaning.
- Item tables follow a **4-column** structure.
- Uses:
  - `budget_parser_fulltable.py`
  - `extract_heads_departments_with_outliers.py`
- Fully supports:
  - Head hierarchy parsing
  - Voted/Charged and Plan/Non-Plan flags
  - Item-level outlier detection
  - Summary sheet generation

---

### ▶️ [`2020/`](./2020)
- Handles PDFs from **FY 2020-21**, which have unique formatting:
  - **Urdu replaced by Hindi**
  - Item tables contain **5 columns** (only in this year)
- Uses a modified script:
  - `heads_and_dept_23-06_with_outliers_2020-21.py`
- Known issues:
  - ❌ Multi-line head names not parsed correctly
  - ❌ `accounts_total` summary sheet is not being generated

---

### ▶️ [`2020-onwards/`](./2020-onwards)
- For **FY 2021-22 and beyond**
- PDFs use consistent Hindi formatting
- Item tables revert to **4-column** layout (same as pre-2020)
- Uses:
  - `extract_heads_departments_with_outliers_post-2020.py`
- Benefits:
  - Cleaner OCR
  - More consistent parsing
  - Fewer text cleanup issues

---

## ⚙️ Core Pipeline Logic

All three folders follow a **common 5-step pipeline**:
1. **Extract tables** from PDFs → `.txt` files  
2. **Parse and clean** heads/items → Excel  
3. **Standardize** item names using dictionary  
4. **Copy and summarize** cleaned data  
5. **Rename** final output files for archival/automation

---

## 🚧 Known Gaps
- Some OCR errors and garbage text still require manual review.
- Multi-line head names (esp. in 2020) need more robust parsing.
- Summary generation issues exist in the 2020 version.

---

## 📌 Usage Notes
- Ensure consistent folder structure and naming before running the pipeline.
- Replace or modify scripts only within their corresponding folders based on year-specific format.
