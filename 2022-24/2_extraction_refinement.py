"""
Extraction Refinement
The script takes raw text files and produces clean, structured Excel files.
"""

import os
import re
import pandas as pd
import string
from item_dict import ITEM_DICT

# --- Configuration ---
LIMIT_TO_FILE = None
# LIMIT_TO_FILE = '08_08-Finance.txt'

# --- Helper Functions ---

def clean_head_name(raw_text: str) -> str:
    if raw_text is None: return raw_text
    words = raw_text.strip().split()
    keep_words = []
    for w in words:
        token = w.strip(string.punctuation)
        ltok = token.lower()
        if re.match(r'^\d', token): break
        if len(token) == 1: break
        if len(token) == 2 and ltok not in ["on", "of"]: break
        if ltok == "demand": break
        keep_words.append(token)
    return " ".join(keep_words)

def extract_last_four_numbers(line):
    matches = re.findall(r'\d[\d,]*\.\d{2}', line)
    return matches[-4:] if len(matches) >= 4 else []

def get_clean_item_name_segment(line):
    words = re.split(r"\s{2,}", line.strip())[0].strip().split()
    clean_words = []
    for word in words:
        if len(word) == 1: break
        clean_words.append(word)
    return ' '.join(clean_words)

def clean_and_validate_item_code(token):
    CORRECTIONS_DICT = {'o': '0', 'O': '0', 'l': '1', 'S': '5', 'B': '8'}
    was_corrected = False
    cleaned_token = token.strip(string.punctuation + "()[]")
    for char, replacement in CORRECTIONS_DICT.items():
        if char in cleaned_token:
            cleaned_token = cleaned_token.replace(char, replacement)
            was_corrected = True
    if re.fullmatch(r"\d{3}", cleaned_token):
        return cleaned_token, was_corrected
    return None, False

def find_demand_number(lines):
    for line in lines[:30]: 
        match = re.search(r'Demand\s*:?\s*(\d+)', line, re.IGNORECASE)
        if match: return match.group(1)
    return None

def check_for_plan_non_plan(lines):
    lines_to_scan = lines[:300]
    text_to_scan = " ".join(lines_to_scan)
    if re.search(r'\b(Plan|Non-?Plan)\b', text_to_scan, re.IGNORECASE):
        return True
    return False

# --- Core Processing Functions ---

def build_full_header_map(lines):
    """
    This is a pre-pass over the TXT file.
    """
    header_map = {}
    
    HEADER_VARIATIONS = {
        "Sub Major Head": "Sub Major Head", "Sub M Head": "Sub Major Head", "Sub Maj Head": "Sub Major Head",
        "Major Head": "Major Head",
        "Minor Head": "Minor Head", "Mi Head": "Minor Head",
        "Sub Head": "Sub Head",
        "Group Head": "Group Head",
        "Sector": "Sector"
    }

    for i, line in enumerate(lines):
        triggered_head_type = None
        for variation, canonical_name in HEADER_VARIATIONS.items():
            if line.strip().startswith(variation):
                triggered_head_type = canonical_name
                break
        
        if triggered_head_type:
            end_index = min(i + 4, len(lines))
            block_of_lines = lines[i:end_index]
            full_text = " ".join(block_of_lines)
            
            number = None
            if triggered_head_type == "Sector":
                sector_match = re.search(r'Sector\s+([A-Z])\b', full_text)
                if sector_match: number = sector_match.group(1)
            else:
                keyword_pos = full_text.find(triggered_head_type)
                search_region = full_text[keyword_pos : keyword_pos + 100]
                number_match = re.search(r'\b(\d{2,4})\b', search_region)
                if number_match: number = number_match.group(1)
            
            name_text = full_text
            for variation in HEADER_VARIATIONS.keys():
                name_text = name_text.replace(variation, "")
            if number:
                name_text = name_text.replace(number, "")
            
            next_header_match = re.search(r'(Major Head|Sub Major Head|Minor Head|Sub Head|Group Head)', name_text)
            if next_header_match:
                name_text = name_text[:next_header_match.start()]

            english_only_name = re.sub(r'[\u0900-\u097F]+', '', name_text)
            cleaned_name = clean_head_name(english_only_name)
            
            if number or cleaned_name:
                header_map[i] = {
                    'type': triggered_head_type,
                    'number': number,
                    'name': cleaned_name if cleaned_name else ''
                }
    return header_map

def extract_combined_data(lines, demand_num, header_map, year_labels):
    data_rows = []
    current = {
        'Sector_num': None, 'Sector_nam': '', 'MajorHead_num': None, 'MajorHead_nam': '',
        'SubMajorHead_num': None, 'SubMajorHead_nam': '', 'MinorHead_num': None, 'MinorHead_nam': '',
        'GroupHead_num': None, 'GroupHead_nam': '', 'SubHead_num': None, 'SubHead_nam': '',
        'Dept_num': None, 'Dept_nam': None
    }
    
    processing_has_started = False
    head_status = 'OK'

    def reset_below(level):
        nonlocal current
        if level in ['sector', 'majorhead', 'submajorhead', 'minorhead', 'grouphead', 'subhead']:
            current['Dept_num'] = None; current['Dept_nam'] = ''
        if level in ['sector', 'majorhead', 'submajorhead', 'minorhead', 'grouphead']:
            current['SubHead_num'] = None; current['SubHead_nam'] = ''
        if level in ['sector', 'majorhead', 'submajorhead', 'minorhead']:
            current['GroupHead_num'] = None; current['GroupHead_nam'] = ''
        if level in ['sector', 'majorhead', 'submajorhead']:
            current['MinorHead_num'] = None; current['MinorHead_nam'] = ''
        if level in ['sector', 'majorhead']:
            current['SubMajorHead_num'] = None; current['SubMajorHead_nam'] = ''
        if level in ['sector']:
            current['MajorHead_num'] = None; current['MajorHead_nam'] = ''

    i = 0
    while i < len(lines):
        line = lines[i]

        if not processing_has_started:
            if "Sector" in line: processing_has_started = True
            else: i += 1; continue

        if 'Total' in line or 'कुल' in line:
            i += 1
            continue

        if i in header_map:
            header_info = header_map[i]
            head_type = header_info['type'].replace(' ', '')
            
            current[f'{head_type}_num'] = header_info['number']
            current[f'{head_type}_nam'] = header_info['name'] # Corrected from _name to _nam
            
            if not header_info['number']: head_status = 'MISSING_HEAD_NUMBER'
            reset_below(head_type.lower())
            i += 1
            continue

        dept_match = re.match(r'^(\d{4})\s{2,}(.*)', line)
        if dept_match:
            current['Dept_num'] = dept_match.group(1).strip()
            current['Dept_nam'] = dept_match.group(2).strip()
            i += 1
            continue

        tokens = line.split()
        if not tokens: i += 1; continue

        item_code, was_corrected = clean_and_validate_item_code(tokens[0])
        
        row_dict = current.copy()
        row_dict['Demand'] = demand_num
        
        if item_code is not None:
            item_line_remainder = line[len(tokens[0]):].strip()
            item_name = get_clean_item_name_segment(item_line_remainder)
            item_name = clean_head_name(item_name)
            values = extract_last_four_numbers(line)
            j = i + 1 
            
            status = head_status
            if was_corrected: status = "CORRECTED"
            head_status = 'OK'
            
            row_dict.update({
                'Voted_Charged': 'V', 'Plan/Non-Plan': 'NP',
                'Item_num': item_code, 'Item_nam': item_name.strip(),
                'status': status
            })
            for idx, label in enumerate(year_labels):
                row_dict[label] = values[idx] if idx < len(values) else None
            
            data_rows.append(row_dict)
            i = j
            continue

        elif len(extract_last_four_numbers(line)) >= 4:
            item_name = get_clean_item_name_segment(line)
            item_name = clean_head_name(item_name)
            
            row_dict.update({
                'Voted_Charged': 'V', 'Plan/Non-Plan': 'NP',
                'Item_num': None, 'Item_nam': item_name.strip(),
                'status': "MISSING_CODE"
            })
            values = extract_last_four_numbers(line)
            for idx, label in enumerate(year_labels):
                row_dict[label] = values[idx] if idx < len(values) else None
            
            data_rows.append(row_dict)
            i += 1
            continue

        i += 1
    return data_rows

# --- Data Quality and Finalization Functions ---

def check_ocr_errors_and_outliers(df, year_labels):
    for year_label in year_labels:
        original_col_name = f'{year_label}_Original'
        if year_label in df.columns:
            df[original_col_name] = df[year_label].astype(str)
        else:
            df[year_label] = None
            df[original_col_name] = ''

        error_column = f'{year_label}_Error'
        df[error_column] = ''
        df[year_label] = pd.to_numeric(df[year_label], errors='coerce')
        df.loc[df[year_label].isna(), error_column] = 'OCR Error'

        mean = df[year_label].mean()
        std = df[year_label].std()
        outliers = (df[year_label] > mean + 3 * std) | (df[year_label] < mean - 3 * std)
        df.loc[outliers, error_column] = df.loc[outliers, error_column].apply(
            lambda x: 'Outlier' if x == '' else 'OCR Error, Outlier'
        )
    return df

def add_data_quality_checks(df, year_labels):
    df['Data_Check'] = 'OK'
    df['Spill_Check'] = 'OK'

    for idx, row in df.iterrows():
        if 'status' in row and pd.notna(row['status']):
            if row['status'] == 'CORRECTED':
                df.at[idx, 'Data_Check'] = 'Corrected Item Code'
            elif row['status'] == 'MISSING_CODE':
                df.at[idx, 'Data_Check'] = 'Missing Item Code'
            elif row['status'] == 'MISSING_HEAD_NUMBER':
                df.at[idx, 'Data_Check'] = 'Missing Head Number'

        if not pd.isna(row[year_labels[0]]) and str(row['Item_num']) == str(row[year_labels[0]]):
            df.at[idx, 'Data_Check'] = 'CHECK'
            df.at[idx, 'Spill_Check'] = 'SPILL'

        if 'Item_nam' not in row or pd.isna(row['Item_nam']) or str(row['Item_nam']).strip() == '':
            df.at[idx, 'Item_nam'] = 'Unnamed Item'
            if df.at[idx, 'Data_Check'] == 'OK':
                df.at[idx, 'Data_Check'] = 'CHECK'
    
    if 'status' in df.columns:
        df.drop(columns=['status'], inplace=True)

    return df

# --- Main Orchestrator ---

def process_combined_folder(input_folder, output_folder, base_year):
    os.makedirs(output_folder, exist_ok=True)

    for file in os.listdir(input_folder):
        if LIMIT_TO_FILE and file != LIMIT_TO_FILE:
            continue

        if file.endswith('.txt'):
            print(f"\n--- Processing file: {file} ---")
            input_path = os.path.join(input_folder, file)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]

            include_plan_non_plan_col = check_for_plan_non_plan(lines)
            demand_num = find_demand_number(lines)
            
            print("Step 1: Building full header map from TXT...")
            header_map = build_full_header_map(lines)
            
            output_path = os.path.join(output_folder, file[:2] + "_combined.xlsx")
            
            year_labels = [
                f"{base_year - 2}-{str(base_year - 1)[-2:]}_accounts",
                f"{base_year - 1}-{str(base_year)[-2:]}_estimates",
                f"{base_year - 1}-{str(base_year)[-2:]}_revisedestimate",
                f"{base_year}-{str(base_year + 1)[-2:]}_estimates"
            ]
            
            print("Step 2: Running main data extraction...")
            rows = extract_combined_data(lines, demand_num, header_map, year_labels)
            
            df = pd.DataFrame(rows)

            if df.empty:
                print(f"Warning: No data was extracted for {file}. Skipping.")
                continue

            print("Step 3: Adding data quality checks...")
            df = check_ocr_errors_and_outliers(df, year_labels)
            df = add_data_quality_checks(df, year_labels)

            print("Step 4: Finalizing and saving to Excel...")
            
            base_columns = [
                'Demand', 'Sector_num', 'Sector_nam', 'MajorHead_num', 'MajorHead_nam',
                'SubMajorHead_num', 'SubMajorHead_nam', 'MinorHead_num', 'MinorHead_nam',
                'GroupHead_num', 'GroupHead_nam', 'SubHead_num', 'SubHead_nam',
                'Dept_num', 'Dept_nam', 'Voted_Charged'
            ]
            if include_plan_non_plan_col:
                base_columns.insert(base_columns.index('Voted_Charged') + 1, 'Plan/Non-Plan')
            
            final_ordered_columns = base_columns + ['Item_num', 'Item_nam']
            for year_col in year_labels:
                final_ordered_columns.append(year_col)
                final_ordered_columns.append(f"{year_col}_Original")
                final_ordered_columns.append(f"{year_col}_Error")
            final_ordered_columns.extend(['Data_Check', 'Spill_Check', 'Source PDF'])
            
            df['Source PDF'] = os.path.splitext(os.path.basename(input_path))[0] + ".pdf"
            
            existing_cols_in_order = [col for col in final_ordered_columns if col in df.columns]
            df = df[existing_cols_in_order]

            df['Item_num'] = df['Item_num'].astype(str).str.zfill(3)
            df['Item_nam'] = df['Item_num'].map(ITEM_DICT).fillna(df['Item_nam'])

            df.to_excel(output_path, index=False, sheet_name='Extracted Data')
            print(f"Saved: {output_path}")

# --- Script Execution ---

if __name__ == '__main__':
    input_folder = r"Data\2025-2026"
    output_folder = r"2025-26\Cleaned_Items"
    base_year = 2025
    
    print(f"Starting processing for folder: {input_folder}")
    if LIMIT_TO_FILE:
        print(f"--- Limiting to single file: {LIMIT_TO_FILE} ---")

    process_combined_folder(input_folder, output_folder, base_year)
    
    print("\nProcessing complete.")