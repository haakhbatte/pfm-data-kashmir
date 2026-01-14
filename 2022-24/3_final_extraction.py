"""
Final Reporting
"""

import os
import re
import pandas as pd
import openpyxl

# --- Configuration ---
LIMIT_TO_FILE = None
# LIMIT_TO_FILE = '08_combined.xlsx' (This should be the name in the CLEANED_DIR)

def verify_categories_with_pdfplumber(pdf_path):
    import pdfplumber
    
    pdf_map = {}
    current_category = None
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                if "Grand Total" in text or "Sector" in text:
                    break
                
                cleaned_text = text.replace(" ", "").upper()
                if "REVENUEACCOUNT" in cleaned_text:
                    current_category = 'Revenue'
                elif "CAPITALACCOUNT" in cleaned_text:
                    current_category = 'Capital'
                
                for line in text.split('\n'):
                    if current_category and re.match(r'^\d{4}', line.strip()):
                        major_head_num = line.strip()[:4]
                        pdf_map[major_head_num] = current_category
    except Exception as e:
        print(f"  - Warning: Could not process PDF for verification: {e}")

    return pdf_map

# --- Helper Functions ---

def extract_numbers_from_line(line):
    return [float(m.replace(',', '')) for m in re.findall(r'[\d,]+\.\d{1,2}', line)]

def find_demand_number(lines):
    for line in lines[:30]: 
        match = re.search(r'Demand\s*:?\s*(\d+)', line, re.IGNORECASE)
        if match: return match.group(1)
    return None

def generate_new_filename(original_txt_filename, txt_lines, input_folder_path):
    try:
        year_part = os.path.basename(os.path.normpath(input_folder_path))
        if re.match(r'\d{4}-\d{4}', year_part):
            parts = year_part.split('-')
            year_part = f"{parts[0]}-{parts[1][-2:]}"

    except Exception:
        year_part = "UnknownYear"

    demand_num_part = find_demand_number(txt_lines)
    if not demand_num_part:
        demand_num_part = original_txt_filename[:2] # Fallback to the file prefix

    name_part = "UnknownName"
    name_match = re.search(r'\d+_\d+-(.*)\.txt', original_txt_filename, re.IGNORECASE)
    if name_match:
        name_part = name_match.group(1).replace('_', ' ').title()
    
    return f"{year_part}_{demand_num_part}-{name_part}.xlsx"

def extract_summary_data(txt_lines):
    major_head_map = {}
    grand_total_values = [0.0, 0.0, 0.0, 0.0]
    current_category = None
    grand_total_search_done = False

    for i, line in enumerate(txt_lines):
        cleaned_line = line.replace(" ", "").upper()
        
        if "REVENUEACCOUNT" in cleaned_line: current_category = 'Revenue'
        elif "CAPITALACCOUNT" in cleaned_line: current_category = 'Capital'
        elif line.strip().startswith("Sector"): break
        
        if current_category and re.match(r'^\d{4}', line.strip()):
            major_head_num = line.strip()[:4]
            major_head_map[major_head_num] = current_category
        
        if ("GrandTotal" in cleaned_line or "Grand Total" in line) and not grand_total_search_done:
            collected_numbers = []
            for j in range(i, len(txt_lines)):
                search_line = txt_lines[j]
                
                if "Demand" in search_line:
                    break
                
                numbers_on_this_line = extract_numbers_from_line(search_line)
                collected_numbers.extend(numbers_on_this_line)

            final_four_numbers = collected_numbers[-4:]

            if len(final_four_numbers) < 4:
                padding = [0.0] * (4 - len(final_four_numbers))
                final_four_numbers.extend(padding)
            
            grand_total_values = final_four_numbers
            grand_total_search_done = True 

    return major_head_map, grand_total_values

def calculate_dynamic_totals(df, major_head_map, year_labels):
    if df.empty or 'MajorHead_num' not in df.columns: return None
    df['Category'] = df['MajorHead_num'].astype(str).map(major_head_map)
    for col in year_labels:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    summary = df.groupby('Category')[year_labels].sum()
    return summary.to_dict()

# --- Main Orchestrator ---

def create_summary_reports(cleaned_folder, txt_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    
    txt_by_key = {fn[:2]: fn for fn in os.listdir(txt_folder) if fn.lower().endswith(".txt")}
    pdf_by_key = {fn[:2]: fn for fn in os.listdir(txt_folder) if fn.lower().endswith(".pdf")}

    for file in os.listdir(cleaned_folder):
        if LIMIT_TO_FILE and file != LIMIT_TO_FILE:
            continue

        if file.lower().endswith(".xlsx"):
            key = file[:2]
            if key not in txt_by_key or key not in pdf_by_key:
                print(f"Missing a source file for prefix {key}; skipped {file}")
                continue

            print(f"\n--- Creating report for: {file} ---")
            cleaned_path = os.path.join(cleaned_folder, file)
            original_txt_filename = txt_by_key[key]
            txt_path = os.path.join(txt_folder, original_txt_filename)
            pdf_path = os.path.join(txt_folder, pdf_by_key[key])
            
            with open(txt_path, 'r', encoding='utf-8') as f:
                txt_lines = f.readlines()

            new_filename = generate_new_filename(original_txt_filename, txt_lines, txt_folder)
            output_path = os.path.join(output_folder, new_filename)

            print("  Step 1: Reading clean data with specific types...")
            try:
                excel_cols = pd.read_excel(cleaned_path, sheet_name=0, nrows=0).columns.tolist()
            except Exception as e:
                print(f"Error reading header from {file}: {e}. Skipping.")
                continue

            dtype_map = {col: str for col in excel_cols}
            value_col_endings = ('_accounts', '_estimates', '_revisedestimate')
            for col in excel_cols:
                if col.endswith(value_col_endings):
                    dtype_map[col] = float

            clean_df = pd.read_excel(cleaned_path, sheet_name=0, dtype=dtype_map)
            
            print("  Step 2: Performing Hybrid Verification...")
            major_head_map, grand_totals = extract_summary_data(txt_lines)
            
            print("  Step 3: Building dynamic Excel report...")
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                clean_df.to_excel(writer, sheet_name='Extracted Data', index=False)
                
                lookup_df = pd.DataFrame(list(major_head_map.items()), columns=['MajorHead_num', 'Category'])
                lookup_df.to_excel(writer, sheet_name='CategoryLookup', index=False)
                
                import openpyxl
                from openpyxl.styles import Font
                writer.book['CategoryLookup'].sheet_state = 'veryHidden'

                summary_df = pd.DataFrame(columns=['Column', 'Revenue', 'Capital', 'Total', 'Reported Total', 'Check'])
                summary_df.to_excel(writer, sheet_name='Account Totals', index=False)

                workbook = writer.book
                data_ws = workbook['Extracted Data']
                summary_ws = workbook['Account Totals']

                header_cells = data_ws[1]
                col_letters = {cell.value: cell.column_letter for cell in header_cells}

                bold_font = Font(bold=True)
                category_col_letter = openpyxl.utils.get_column_letter(data_ws.max_column + 1)
                category_header_cell = data_ws[f'{category_col_letter}1']
                category_header_cell.value = 'Category'
                category_header_cell.font = bold_font

                for i in range(2, data_ws.max_row + 1):
                    major_head_cell = f"{col_letters.get('MajorHead_num', 'D')}{i}"
                    formula = f'=IFERROR(VLOOKUP({major_head_cell},CategoryLookup!$A:$B,2,FALSE),"")'
                    data_ws[f'{category_col_letter}{i}'] = formula

                year_labels = [col for col in clean_df.columns if isinstance(col, str) and re.search(r'\d{4}', col) and '_Original' not in col and '_Error' not in col]

                money_format = '#,##0.00'

                for i, year_label in enumerate(year_labels):
                    row_num = i + 2
                    data_col_letter = col_letters.get(year_label)
                    
                    if data_col_letter:
                        summary_ws[f'A{row_num}'] = year_label
                        
                        # Column B: Revenue
                        rev_cell = summary_ws[f'B{row_num}']
                        rev_cell.value = f"=SUMIF('Extracted Data'!${category_col_letter}:${category_col_letter},\"Revenue\",'Extracted Data'!${data_col_letter}:${data_col_letter})"
                        rev_cell.number_format = money_format
                        
                        # Column C: Capital
                        cap_cell = summary_ws[f'C{row_num}']
                        cap_cell.value = f"=SUMIF('Extracted Data'!${category_col_letter}:${category_col_letter},\"Capital\",'Extracted Data'!${data_col_letter}:${data_col_letter})"
                        cap_cell.number_format = money_format
                        
                        # Column D: Total
                        total_cell = summary_ws[f'D{row_num}']
                        total_cell.value = f"=SUM(B{row_num}:C{row_num})"
                        total_cell.number_format = money_format
                        
                        # Column E: Reported Total
                        reported_total_cell = summary_ws[f'E{row_num}']
                        reported_total_cell.value = grand_totals[i]
                        reported_total_cell.number_format = money_format
                        
                        # Column F: Check
                        summary_ws[f'F{row_num}'] = f'=IF(ABS(D{row_num}-E{row_num})<0.01,"OK","CHECK")'

            print(f"Dynamic report saved to: {output_path}")

# --- Script Execution ---

if __name__ == '__main__':
    # Here's where I define the input and output folders for this script.
    CLEANED_DIR   = r"2025-26\Cleaned_Items"
    TXT_DIR       = r"Data\2025-2026"
    REPORTS_DIR   = r"2025-26\Final_Extracted"
    
    print(f"Starting final report generation...")
    if LIMIT_TO_FILE:
        print(f"--- Limiting to single file: {LIMIT_TO_FILE} ---")

    create_summary_reports(CLEANED_DIR, TXT_DIR, REPORTS_DIR)
    
    print("\nReporting process complete.")