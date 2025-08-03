import os
import re
import pandas as pd
import string
from item_dict import ITEM_DICT

def extract_head_names_from_pdf(pdf_path):
    import pdfplumber
    import re

    head_digit_lengths = {
        "Major Head": 4,
        "Sub Major Head": 2,
        "Minor Head": 3,
        "Group Head": 4,
        "Sub Head": 4,
    }

    patterns = {
        head_type: re.compile(rf"{re.escape(head_type)}\s+(\d{{{length}}})\s+(.*?)(?=\n|$)", re.IGNORECASE)
        for head_type, length in head_digit_lengths.items()
    }

    devanagari_regex = re.compile(r'[\u0900-\u097F]+')
    head_dicts = {head_type: {} for head_type in head_digit_lengths}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for head_type, pattern in patterns.items():
                matches = pattern.findall(text)
                for number, name in matches:
                    cleaned_name = devanagari_regex.sub('', name).strip()
                    head_dicts[head_type][number.strip()] = cleaned_name
    return head_dicts

def clean_head_name(raw_text: str) -> str:
    """
    Keep tokens until we hit something that looks like garbage.
    We stop (and discard the rest) if we meet any of these:
      • token starts with a digit
      • single‑character token                                → “G”, “X”, …
      • two‑character token that is NOT “of” (case‑insensitive) → “ut”, “OL”, …
      • the word “demand” (OCR often appends ‘Demand’ stray)
    """
    if raw_text is None:
        return raw_text

    words      = raw_text.strip().split()
    keep_words = []

    for w in words:
        # strip lead/trail punctuation so “Demand,” or “(G” are caught
        token = w.strip(string.punctuation)
        ltok  = token.lower()

        # -- stop conditions --------------------------------------------------
        if re.match(r'^\d', token):          # starts with digit
            break
        if len(token) == 1:                  # single character
            break
        if len(token) == 2 and ltok not in ["on","of"]: # double char except "of"
            break
        if ltok == "demand":                 # literal "demand"
            break
        # ---------------------------------------------------------------------

        keep_words.append(token)

    return " ".join(keep_words)

import string
import re

def extract_item_code(token: str) -> str | None:
    """
    Extracts a clean 3-digit item code from a messy token like '023.', '(023)', etc.
    Returns None if not valid.
    """
    token = token.strip(string.punctuation + "()[]")
    if re.fullmatch(r"\d{3}", token):
        return token
    return None


def is_three_digit_number(token):
    return bool(re.fullmatch(r"\d{3}", token))

def extract_last_four_numbers(line):
    matches = re.findall(r'\d[\d,]*\.\d{2}', line)
    return matches[-4:] if len(matches) >= 4 else []



def get_clean_item_name_segment(line):
    words = re.split(r"\s{2,}", line.strip())[0].strip().split()
    clean_words = []
    for word in words:
        if len(word) == 1:
            break
        clean_words.append(word)
    return ' '.join(clean_words)

def check_ocr_errors_and_outliers(df, year_labels):
    for year_label in year_labels:
        # Create a new error column
        error_column = f'{year_label}_Error'
        df[error_column] = ''

        # Ensure numeric conversion
        df[year_label] = pd.to_numeric(df[year_label], errors='coerce')

        # Mark OCR errors
        df.loc[df[year_label].isna(), error_column] = 'OCR Error'

        # Detect outliers
        mean = df[year_label].mean()
        std = df[year_label].std()
        outliers = (df[year_label] > mean + 3 * std) | (df[year_label] < mean - 3 * std)

        # Combine error types if needed
        df.loc[outliers, error_column] = df.loc[outliers, error_column].apply(
            lambda x: 'Outlier' if x == '' else 'OCR Error, Outlier'
        )
    return df

import re

def add_data_quality_checks(df, year_labels):
    df['Data_Check'] = 'OK'
    df['Spill_Check'] = 'OK'

    for idx, row in df.iterrows():
        data_check = 'OK'
        spill_check = 'OK'

        # Check for invalid year values
        for year_label in year_labels:
            val = row[year_label]
            if pd.isna(val) or not re.match(r'^\d+\.?\d*$', str(val)):
                data_check = 'CHECK'

        # Check for spillover (Item_num == value in first year col)
        if not pd.isna(row[year_labels[0]]) and str(row['item_code_cleaned']) == str(row[year_labels[0]]):
            data_check = 'CHECK'
            spill_check = 'SPILL'

        # Check for unnamed items
        if not row['item_name_cleaned'] or str(row['item_name_cleaned']).strip() == '':
            df.at[idx, 'item_name_cleaned'] = 'Unnamed Item'
            data_check = 'CHECK'

        df.at[idx, 'Data_Check'] = data_check
        df.at[idx, 'Spill_Check'] = spill_check

    return df


def extract_combined_data(input_file, demand_num):
    data_rows = []
    current = {
        'sector_num': None,
        'sector_name': '',
        'majorhead_num': None,
        'majorhead_name': '',
        'submajorhead_num': None,
        'submajorhead_name': '',
        'minorhead_num': None,
        'minorhead_name': '',
        'grouphead_num': None,
        'grouphead_name': '',
        'subhead_num': None,
        'subhead_name': '',
        'dept_num': None,
        'dept_name': None
    }

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]

        # --- HEAD Extraction ---
        sector_match = re.match(r'^Sector\s{2,}([A-Za-z]{1,2})\s{2,}(.*)', line)
        if sector_match:
            current['sector_num'] = sector_match.group(1).strip()[0]
            current['sector_name'] = sector_match.group(2).strip()
            i += 1
            while i < len(lines) and not re.match(r'^(Major Head|Sub Major Head|Minor Head|Group Head|Sub Head|\d{2}\s+)', lines[i]):
                segment = re.split(r'\s{2,}', lines[i])[0].strip()
                current['sector_name'] += ' ' + segment
                i += 1
            current['sector_name'] = clean_head_name(current['sector_name'])
            continue

        def extract_head(pattern, key_num, key_name, next_key):
            nonlocal i
            match = re.match(pattern, line)
            if match:
                current[key_num] = match.group(1)
                current[key_name] = (match.group(2) or '').strip()
                i += 1
                while i < len(lines) and not re.match(next_key, lines[i]) and not re.match(r'^\d{2,}\s+', lines[i]):
                    segment = re.split(r'\s{2,}', lines[i])[0].strip()
                    current[key_name] += ' ' + segment
                    i += 1
                current[key_name] = clean_head_name(current[key_name])
                return True
            return False

        if re.match(r'^Major Head\s*$', line):
            i += 1
            if i < len(lines):
                next_line = lines[i]
                tokens = re.split(r'\s{2,}', next_line.strip(), maxsplit=1)
                if len(tokens) >= 2 and re.match(r'^\d{4}$', tokens[0]):
                    current['majorhead_num'] = tokens[0]
                    current['majorhead_name'] = clean_head_name(tokens[1])
                else:
                    current['majorhead_num'] = None
                    current['majorhead_name'] = ''
            i += 1
            continue

        if extract_head(r'^Sub Major Head\s+(\d+)(?:\s+(.*?))?(?:\s{2,}|$)', 'submajorhead_num', 'submajorhead_name', r'^Minor Head'):
            continue
        if extract_head(r'^Minor Head\s+(\d+)(?:\s+(.*?))?(?:\s{2,}|$)', 'minorhead_num', 'minorhead_name', r'^Group Head'):
            continue
        if extract_head(r'^Group Head\s+(\d+)(?:\s+(.*?))?(?:\s{2,}|$)', 'grouphead_num', 'grouphead_name', r'^Sub Head'):
            continue

        subhead_match = re.match(r'^Sub Head\s+(\d{4})(?:\s+(.*?))?(?:\s{2,}|$)', line)
        if subhead_match:
            current['subhead_num'] = subhead_match.group(1)
            current['subhead_name'] = (subhead_match.group(2) or '').strip()
            i += 1
            while i < len(lines) and not re.match(r'^\d{3}\s+', lines[i]):
                if re.match(r'^\d', lines[i]):
                    break
                segment = re.split(r'\s{2,}', lines[i])[0].strip()
                current['subhead_name'] += ' ' + segment
                i += 1
            current['subhead_name'] = clean_head_name(current['subhead_name'])
            continue
        dept_match = re.match(r'^(\d{4})\s{2,}(.*)', line)
        if dept_match:
            current['dept_num'] = dept_match.group(1).strip()
            current['dept_name'] = dept_match.group(2).strip()
            i += 1
            continue
        # --- ITEM Extraction ---
        tokens = line.split()
        code = extract_item_code(tokens[0])
        if code is not None and len(tokens) >= 2:
            item_code = code
            item_line_remainder = line[len(tokens[0]):].strip()
            item_name = get_clean_item_name_segment(item_line_remainder)
            item_name = clean_head_name(item_name)
            values = extract_last_four_numbers(line)
            if len(values) < 4:
                i += 1
                continue  # Skip rows missing 4 proper numeric columns

            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue
                next_tokens = next_line.split()
                if extract_item_code(next_tokens[0]) is not None or next_tokens[0] == 'Total':
                    break
                if not next_line[0].isalpha():
                    break
                segment = get_clean_item_name_segment(next_line)
                if segment:
                    item_name += " " + segment
                j += 1
            vc_value = 'V'  # default, can be modified later
            pn_value = 'P' if item_code == '000' else 'NP'
            row = [demand_num] + list(current.values()) + [vc_value, pn_value, item_code, item_name.strip()] + values
            data_rows.append(row)
            i = j
            continue

        i += 1

    return data_rows

def generate_combined_column_names(base_year):
    head_keys = [
        'sector_num', 'sector_name',
        'majorhead_num', 'majorhead_name',
        'submajorhead_num', 'submajorhead_name',
        'minorhead_num', 'minorhead_name',
        'grouphead_num', 'grouphead_name',
        'subhead_num', 'subhead_name',
        'dept_num', 'dept_name'
    ]
    extra_fields = ['Voted_Charged', 'Plan/Non-Plan']
    item_fields = ['item_code', 'item_name']

    # Updated based on the 2021–2022 format (4 columns)
    year_cols = [
        (base_year - 2, base_year - 1, "accounts"),          # 2019–2020
        (base_year - 1, base_year,     "estimates"),         # 2020–2021 (BE)
        (base_year - 1, base_year,     "revisedestimate"),   # 2020–2021 (RE)
        (base_year,     base_year + 1, "estimates")          # 2021–2022 (BE)
    ]

    value_cols = [f"{y1}-{str(y2)[-2:]}_{label}" for (y1, y2, label) in year_cols]
    return ['Demand'] + [key + '_cleaned' for key in head_keys] + extra_fields + [f"{f}_cleaned" for f in item_fields] + value_cols

def process_combined_folder(input_folder, output_folder, base_year):
    os.makedirs(output_folder, exist_ok=True)

    for file in os.listdir(input_folder):
        if file.endswith('.txt'):
            pdf_path = os.path.join(input_folder, file.replace(".txt", ".pdf"))
            head_dicts = extract_head_names_from_pdf(pdf_path)
            input_path = os.path.join(input_folder, file)
            output_path = os.path.join(output_folder, file[:2] + "_combined.xlsx")
            demand_num = file[:2]

            rows = extract_combined_data(input_path, demand_num)
            columns = generate_combined_column_names(base_year)
            df = pd.DataFrame(rows, columns=columns)

            # --- Step 1: Convert value columns to numeric ---
            year_labels = [
                f"{base_year - 2}-{str(base_year - 1)[-2:]}_accounts",       # 2019–2020
                f"{base_year - 1}-{str(base_year)[-2:]}_estimates",          # 2020–2021 BE
                f"{base_year - 1}-{str(base_year)[-2:]}_revisedestimate",    # 2020–2021 RE
                f"{base_year}-{str(base_year + 1)[-2:]}_estimates"           # 2021–2022 BE
            ]



            for col in year_labels:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # --- Step 2: Run error + outlier check ---
            df = check_ocr_errors_and_outliers(df, year_labels)

            # Reorder columns to place each _Error column after its year column
            for year_col in year_labels:
                error_col = f"{year_col}_Error"
                if error_col in df.columns:
                    cols = list(df.columns)
                    cols.remove(error_col)
                    insert_pos = cols.index(year_col) + 1
                    cols.insert(insert_pos, error_col)
                    df = df[cols]

            df = add_data_quality_checks(df, year_labels)
            df['Source PDF'] = os.path.splitext(os.path.basename(input_path))[0]+".pdf"
            df.rename(columns={
                'sector_num_cleaned': 'Sector_num',
                'sector_name_cleaned': 'Sector_nam',
                'majorhead_num_cleaned': 'MajorHead_num',
                'majorhead_name_cleaned': 'MajorHead_nam',
                'submajorhead_num_cleaned': 'SubMajorHead_num',
                'submajorhead_name_cleaned': 'SubMajorHead_name',
                'minorhead_num_cleaned': 'MinorHead_num',
                'minorhead_name_cleaned': 'MinorHead_nam',
                'grouphead_num_cleaned': 'GroupHead_num',
                'grouphead_name_cleaned': 'GroupHead_nam',
                'subhead_num_cleaned': 'SubHead_num',
                'subhead_name_cleaned': 'SubHead_nam',
                'dept_num_cleaned': 'Dept_num',
                'dept_name_cleaned': 'Dept_nam',
                'item_code_cleaned': 'Item_num',
                'item_name_cleaned': 'Item_nam'
            }, inplace=True)

            # ---- Final item name overwrite using dictionary ----
            from item_dict import ITEM_DICT  # you should've generated this using the earlier script

            df['Item_num'] = df['Item_num'].astype(str).str.zfill(3)
            df['Item_nam'] = df['Item_num'].map(ITEM_DICT).fillna(df['Item_nam'])
            # -----------------------------------------------------
            # Mapping of DataFrame column names to head types and their number columns
            head_column_map = {
                'Major Head': ('MajorHead_num', 'MajorHead_nam'),
                'Sub Major Head': ('SubMajorHead_num', 'SubMajorHead_name'),
                'Minor Head': ('MinorHead_num', 'MinorHead_nam'),
                'Group Head': ('GroupHead_num', 'GroupHead_nam'),
                'Sub Head': ('SubHead_num', 'SubHead_nam'),
            }

            # Overwrite cleaned head names
            for head_type, (num_col, name_col) in head_column_map.items():
                if head_type in head_dicts:
                    df[name_col] = df[num_col].astype(str).str.strip().map(head_dicts[head_type]).fillna(df[name_col])


            # --- Step 3: Save final output ---
            df.to_excel(output_path, index=False, sheet_name='Extracted Data')
            print(f"Saved: {output_path}")


# Example usage:
process_combined_folder(r"Data\2021-2022", r"2021-22\Cleaned_Items", 2021)
