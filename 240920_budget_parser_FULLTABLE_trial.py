import os
import pytesseract
from pdf2image import convert_from_path
import numpy as np
import re
import pandas as pd
import sys
from PIL import Image

# use the option below to process one file at a time
LIMIT_TO_FILE = None
# LIMIT_TO_FILE = '03_03-Planning_and_Development.pdf'


def extract_text_from_pdf(pdf_path, max_pages=None):
    try:
        pages = convert_from_path(pdf_path, first_page=1, last_page=max_pages)
        text = ""
        for page in pages:
            text += pytesseract.image_to_string(page, config='--psm 6 --oem 3 -c preserve_interword_spaces=1 -l eng+hin+urd')  # Added Hindi and Urdu
        return text
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return None

def clean_text(text):
    text = ''.join(char for char in text if ord(char) < 128)
    return ' '.join(text.split())

def check_ocr_errors_and_outliers(df, year_labels):
    for year_label in year_labels:
        df[year_label] = pd.to_numeric(df[year_label], errors='coerce')
        
        # Create a new error column for each year
        error_column = f'{year_label}_Error'
        df[error_column] = ''
        
        # Check for OCR errors (NaN values)
        ocr_errors = df[year_label].isna()
        df.loc[ocr_errors, error_column] = 'OCR Error'
        
        # Check for outliers
        mean = df[year_label].mean()
        std = df[year_label].std()
        outliers = (df[year_label] > mean + 3*std) | (df[year_label] < mean - 3*std)
        
        # Add 'Outlier' to the error column, handling cases where both errors occur
        df.loc[outliers, error_column] = df.loc[outliers, error_column].apply(
            lambda x: 'Outlier' if x == '' else 'OCR Error, Outlier'
        )
    
    return df

def clean_item_name(item_name):
    # Remove any extra whitespace and '=' signs
    cleaned_name = ' '.join(item_name.replace('=', '').split())
    
    # Remove any non-alphanumeric characters at the start or end
    cleaned_name = cleaned_name.strip('.,;:()-/')
    
    # Capitalize the first letter of each word
    cleaned_name = cleaned_name.title()
    
    return cleaned_name


def get_default_years(folder_name):
    base_year = int(folder_name.split('-')[0])
    return [
        f"{base_year-1}-{base_year}",
        f"{base_year}-{base_year+1}",
        f"{base_year}-{base_year+1}",
        f"{base_year+1}-{base_year+2}"
    ]



def detect_years_original(text, folder_name):
    lines = text.split('\n')
    for line in lines[:20]:  # Check first 20 lines
        numbers = re.findall(r'\d{4}-\d{4}|\d{4}-\d{2}|\d{4}', line)
        if len(numbers) == 4:
            full_years = [
                year if len(year) == 9 else 
                f"{year[:4]}-{int(year[:4])+1}" if len(year) == 4 else 
                f"20{year[:2]}-20{int(year[:2])+1}" 
                for year in numbers
            ]
            year_labels = [
                f"{full_years[0]}_accounts",
                f"{full_years[1]}_estimates",
                f"{full_years[2]}_revisedestimate",
                f"{full_years[3]}_estimates"
            ]
            print(f"Detected year labels for {folder_name} (original method): {year_labels}")
            return year_labels
    print(f"Warning: Unable to detect years for {folder_name} using original method.")
    return None

def detect_years(text, pdf_path):
    folder_name = os.path.basename(os.path.dirname(pdf_path))
    print(f"Processing folder: {folder_name}")  # Debug print

    # Special case for 2013-14 and 2014-15
    if folder_name in ["2013-14", "2014-15"]:
        return detect_years_original(text, folder_name)

    try:
        base_year = int(folder_name.split('-')[0])
    except ValueError:
        print(f"Warning: Unable to parse base year from folder name: {folder_name}")
        base_year = None

    lines = text.split('\n')
    detected_years = []

    # Attempt to detect years from text
    for i in range(len(lines) - 1):
        combined_line = lines[i] + ' ' + lines[i+1]
        numbers = re.findall(r'\d{4}-\d{4}|\d{4}-\d{2}|\d{4}', combined_line)
        if len(numbers) >= 4:
            detected_years = [
                year if len(year) == 9 else 
                f"{year[:4]}-{int(year[:4])+1}" if len(year) == 4 else 
                f"20{year[:2]}-20{int(year[:2])+1}" 
                for year in numbers
            ]
            break

    # Generate year labels based on folder name and detected years
    if folder_name == "2020-21":
        year_labels = [
            f"{base_year-2}-{base_year-1}_accounts",
            f"{base_year-1}-{base_year}_accountspreactual",
            f"{base_year-1}-{base_year}_budgetestimates",
            f"{base_year-1}-{base_year}_revisedestimates",
            f"{base_year}-{base_year+1}_budgetestimates"
        ]
    elif folder_name == "2021-22":
        year_labels = [
            f"2019-2020_accounts",
            f"2020-2021_budgetestimates",
            f"2020-2021_revisedestimate",
            f"2021-2022_budgetestimates"
        ]
    elif folder_name in ["2022-23", "2023-24"]:
        year_labels = [
            f"{base_year-2}-{base_year-1}_accounts",
            f"{base_year-1}-{base_year}_budgetestimates",
            f"{base_year-1}-{base_year}_revisedestimates",
            f"{base_year}-{base_year+1}_budgetestimates"
        ]
    elif folder_name == "2024-25":
        year_labels = [
            f"{base_year-2}-{base_year-1}_accounts",
            f"{base_year-1}-{base_year}_budgetestimates",
            f"{base_year-1}-{base_year}_revisedestimates",
            f"{base_year}-{base_year+1}_voteonaccount"
        ]
    else:
        # For other years, use detected years if available, otherwise use folder-based labels
        if detected_years:
            year_labels = [
                f"{detected_years[0]}_accounts",
                f"{detected_years[1]}_estimates",
                f"{detected_years[2]}_revisedestimate",
                f"{detected_years[3]}_estimates"
            ]
        else:
            year_labels = [
                f"{base_year-2}-{base_year-1}_accounts",
                f"{base_year-1}-{base_year}_estimates",
                f"{base_year-1}-{base_year}_revisedestimate",
                f"{base_year}-{base_year+1}_estimates"
            ]

    print(f"Generated year labels for {folder_name}: {year_labels}")  # Debug print
    return year_labels


def extract_numbers(line):
    print(f"Extracting numbers from: {line}")  # Debug print
    number_strings = re.findall(r'\d+\.?\d*', line)
    numbers = []
    for num_str in number_strings:
        try:
            numbers.append(float(num_str.replace(',', '')))
        except ValueError:
            # If conversion fails, try to split the string into valid numbers
            split_numbers = re.findall(r'\d+\.?\d*', num_str)
            numbers.extend([float(n) for n in split_numbers])
    print(f"Extracted numbers: {numbers}")  # Debug print
    return numbers

def find_sub_major_head(lines, start_index):
    for i in range(start_index, min(start_index + 4, len(lines))):
        line = clean_text(lines[i])
        match = re.search(r'Sub\s*Major\s*Head\s+(\d{2})\s*(.+)?', line, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2) if match.group(2) else ''
    return None, None

def find_group_head(lines, start_index):
    for i in range(start_index, min(start_index + 4, len(lines))):
        line = clean_text(lines[i])
        match = re.search(r'Group Head\s+(\d+)\s+(.+)', line)
        if match:
            return match.group(1), match.group(2)
    return None, None

def find_department_info(lines, start_index):
    for i in range(start_index, min(start_index + 3, len(lines))):
        line = clean_text(lines[i])
        match = re.match(r'^(\d+)\s+(.+)', line)
        if match:
            return match.group(1), match.group(2)
    return None, None

def extract_plan_non_plan_totals(text, year_labels):
    lines = text.split('\n')
    totals = {year_label: {'Revenue': 0, 'Revenue Plan': 0, 'Revenue Non-Plan': 0,
                           'Capital': 0, 'Capital Plan': 0, 'Capital Non-Plan': 0}
              for year_label in year_labels}
    
    revenue_section = False
    capital_section = False
    has_plan_non_plan = False

    for i, line in enumerate(lines):
        print(f"Line {i}: {line}")  # Debug print
        
        if 'Detail Head Code and Description' in line:
            break

        if 'REVENUE ACCOUNT' in line.upper():
            revenue_section = True
            capital_section = False
            continue

        if 'CAPITAL ACCOUNT' in line.upper():
            revenue_section = False
            capital_section = True
            continue

        if 'Plan' in line or 'Non-Plan' in line:
            has_plan_non_plan = True

        numbers = extract_numbers(line)
        if len(numbers) == len(year_labels):
            if revenue_section:
                if 'Non-Plan' in line:
                    for year_label, value in zip(year_labels, numbers):
                        totals[year_label]['Revenue Non-Plan'] = value
                elif 'Plan' in line:
                    for year_label, value in zip(year_labels, numbers):
                        totals[year_label]['Revenue Plan'] = value
                else:
                    for year_label, value in zip(year_labels, numbers):
                        totals[year_label]['Revenue'] = value
            elif capital_section:
                if 'Non-Plan' in line:
                    for year_label, value in zip(year_labels, numbers):
                        totals[year_label]['Capital Non-Plan'] = value
                elif 'Plan' in line:
                    for year_label, value in zip(year_labels, numbers):
                        totals[year_label]['Capital Plan'] = value
                else:
                    for year_label, value in zip(year_labels, numbers):
                        totals[year_label]['Capital'] = value

    if has_plan_non_plan:
        for year_label in year_labels:
            totals[year_label]['Revenue'] = totals[year_label]['Revenue Plan'] + totals[year_label]['Revenue Non-Plan']
            totals[year_label]['Capital'] = totals[year_label]['Capital Plan'] + totals[year_label]['Capital Non-Plan']

    print("Extracted totals:", totals)

    return totals, has_plan_non_plan

def extract_tables(text, year_labels, folder_name):
    tables = []
    current_table = []
    context = {
        'Demand': '', 'Sector_num': '', 'Sector_nam': '', 'MajorHead_num': '', 'MajorHead_nam': '',
        'SubMajorHead_num': '', 'SubMajorHead_name': '', 'MinorHead_num': '', 'MinorHead_nam': '', 
        'GroupHead_num': '', 'GroupHead_nam': '', 'SubHead_num': '', 'SubHead_nam': '', 
        'Dept_num': '', 'Dept_nam': '', 'Voted_Charged': ''
    }
    previous_context = context.copy()
    
    lines = text.split('\n')
    base_year = int(folder_name.split('-')[0])
    is_post_2020 = base_year >= 2020
    is_2013_14 = '2013-14' in folder_name
    is_2014_15 = '2014-15' in folder_name
    is_2019_20 = '2019-20' in folder_name

    # Special handling for 2019-20 files
    if is_2019_20:
        for i, line in enumerate(lines[:30]):  # Check first 30 lines
            if 'Demand' in line:
                demand_match = re.search(r'Demand\s*:?\s*(?:No\.)?\s*(\d+)', line, re.IGNORECASE)
                if demand_match:
                    context['Demand'] = demand_match.group(1)
            if 'Sector' in line:
                sector_match = re.search(r'Sector\s+(\S+)\s+(.+)', line)
                if sector_match:
                    context['Sector_num'] = sector_match.group(1)
                    context['Sector_nam'] = sector_match.group(2).strip()
            if context['Demand'] and context['Sector_num']:
                break
    elif is_2013_14 or is_2014_15:
        for line in lines[:10]:  # Check first 10 lines
            if 'Demand' in line:
                match = re.search(r'Demand:?\s*(?:Number:?)?\s*(\d+)', line, re.IGNORECASE)
                if match:
                    context['Demand'] = match.group(1)
                break

    for i, line in enumerate(lines):
        line = clean_text(line)

        if 'Major Head' in line:
            match = re.search(r'Major Head\s+(\d{4})\s+(.+)', line)
            if match:
                context['MajorHead_num'], context['MajorHead_nam'] = match.groups()
                context['SubMajorHead_num'] = context['SubMajorHead_name'] = ''
                context['MinorHead_num'] = context['MinorHead_nam'] = ''
                context['GroupHead_num'] = context['GroupHead_nam'] = ''

        if not is_2019_20:
            if is_2013_14 or is_2014_15:
                if 'Sector' in line:
                    match = re.match(r'Sector\s+(\S+)\s+(.+)', line)
                    if match:
                        context['Sector_num'], context['Sector_nam'] = match.groups()
            else:
                if 'Demand Number' in line:
                    match = re.search(r'Demand Number\s*:\s*(\d+)', line)
                    if match:
                        context['Demand'] = match.group(1)
                elif re.match(r'Sector\s+([A-Z])\s+(.+)', line):
                    match = re.match(r'Sector\s+([A-Z])\s+(.+)', line)
                    context['Sector_num'], context['Sector_nam'] = match.groups()

        if re.search(r'Sub\s*Major\s*Head', line, re.IGNORECASE):
            match = re.search(r'Sub\s*Major\s*Head\s+(\d{2})?\s*(.+)?', line, re.IGNORECASE)
            if match:
                context['SubMajorHead_num'] = match.group(1) if match.group(1) else ''
                context['SubMajorHead_name'] = match.group(2).strip() if match.group(2) else ''
                if context['SubMajorHead_name'] == 'NA':
                    context['SubMajorHead_num'] = ''
                context['MinorHead_num'] = context['MinorHead_nam'] = ''
                context['GroupHead_num'] = context['GroupHead_nam'] = ''
        elif 'Minor Head' in line:
            match = re.search(r'Minor Head\s+(\d{3})\s+(.+)', line)
            if match:
                context['MinorHead_num'], context['MinorHead_nam'] = match.groups()
                context['GroupHead_num'] = context['GroupHead_nam'] = ''
        elif 'Group Head' in line:
            match = re.search(r'Group Head\s+(\d+)\s+(.+)', line)
            if match:
                context['GroupHead_num'], context['GroupHead_nam'] = match.groups()
        elif 'Sub Head' in line:
            match = re.search(r'Sub Head\s+(\d+)\s+(.+)', line)
            if match:
                context['SubHead_num'], context['SubHead_nam'] = match.groups()
                dept_num, dept_name = find_department_info(lines, i+1)
                if dept_num and dept_name:
                    context['Dept_num'], context['Dept_nam'] = dept_num, dept_name
        elif 'Voted' in line:
            context['Voted_Charged'] = 'V'
        elif 'Charged' in line:
            context['Voted_Charged'] = 'C'
        elif re.match(r'^\d{3}\s|\d+\.\d+', line):
            if is_post_2020:
                combined_line = line
                while i + 1 < len(lines) and not re.match(r'^\d{3}\s|\d+\.\d+', lines[i+1]):
                    i += 1
                    combined_line += ' ' + clean_text(lines[i])
                current_table.append(combined_line)
            else:
                current_table.append(line)
        elif ('Total' in line or 'Sub Total' in line) and current_table:
            tables.append((context.copy(), current_table))
            current_table = []
            new_context = previous_context.copy()
            new_context.update({k: v for k, v in context.items() if v})
            context = new_context
            previous_context = context.copy()
            context['Dept_num'] = context['Dept_nam'] = ''

    if current_table:
        tables.append((context.copy(), current_table))
    
    return tables


def is_english(s):
    return all(ord(c) < 128 for c in s)


def clean_item_name(item_name):
    # Remove any extra whitespace
    cleaned_name = ' '.join(item_name.split())
    
    # Remove any non-alphanumeric characters at the start or end
    cleaned_name = cleaned_name.strip('.,;:()-/')
    
    # Capitalize the first letter of each word
    cleaned_name = cleaned_name.title()
    
    # Add any other cleaning steps as needed
    
    return cleaned_name

def safe_float(x):
    try:
        return float(x) if x else 0.0
    except ValueError:
        print(f"Warning: Could not convert '{x}' to float. Treating as 0.")
        return 0.0


# Original functions for pre-2020 folders
def extract_header_info_pre_2020(text):
    lines = text.split('\n')
    headers = {
        'Sector': '', 'Sector_num': '',
        'Major Head': '', 'MajorHead_num': '',
        'Sub Major Head': '', 'SubMajorHead_num': '',
        'Minor Head': '', 'MinorHead_num': '',
        'Group Head': '', 'GroupHead_num': '',
        'Sub Head': '', 'SubHead_num': ''
    }
    
    for line in lines:
        for header in headers.keys():
            if header in line:
                match = re.match(r'(\w+)\s+(\d+)\s+([^\u0600-\u06FF]+)', line)
                if match:
                    headers[f'{header}_num'] = match.group(2)
                    headers[header] = match.group(3).strip()
    
    return headers


# New functions for 2020 onwards
def extract_header_info_2020_onwards(text):
    lines = text.split('\n')
    headers = {
        'Sector': '', 'Sector_num': '',
        'Major Head': '', 'MajorHead_num': '',
        'Sub Major Head': '', 'SubMajorHead_num': '',
        'Minor Head': '', 'MinorHead_num': '',
        'Group Head': '', 'GroupHead_num': '',
        'Sub Head': '', 'SubHead_num': ''
    }
    
    header_keys = list(headers.keys())  # Create a list of keys
    for line in lines:
        for header in header_keys:  # Iterate over the list instead of headers.keys()
            if header in line:
                parts = line.split()
                if len(parts) >= 3:
                    headers[f'{header}_num'] = parts[1]
                    # Find the first part that's all ASCII (likely English)
                    headers[header] = next((part for part in parts[2:] if all(ord(c) < 128 for c in part)), '')
    
    return headers


def parse_table(context, table, year_labels, folder_name):
    data = []
    base_year = int(folder_name.split('-')[0])
    is_post_2020 = base_year >= 2020

    for line in table:
        parts = line.split()
        if len(parts) >= 2 and re.match(r'^\d{3}$', parts[0]):  # Check if first part is a 3-digit number
            row = context.copy()
            row['Item_num'] = parts[0]
            
            if is_post_2020:
                # For 2020-21 and onwards: Find English text after Hindi
                eng_start = next((j for j, part in enumerate(parts[1:], 1) if all(ord(c) < 128 for c in part)), 1)
                item_name_parts = parts[eng_start:-len(year_labels)] if len(parts) > len(year_labels) else parts[eng_start:]
                numeric_values = parts[-len(year_labels):]
            else:
                # For pre-2020: Use original logic
                item_name_parts = []
                numeric_values = []
                for part in parts[1:]:
                    if part.replace('.', '').isdigit() or part == '':
                        numeric_values.append(part)
                    else:
                        item_name_parts.append(part)
            
            # Remove '=' from the beginning of item name parts
            item_name_parts = [part.lstrip('=') for part in item_name_parts]
            
            raw_item_name = ' '.join(item_name_parts).strip()
            row['Item_nam'] = raw_item_name
            row['Item_nam_Cleaned'] = clean_item_name(raw_item_name)
            
            # Assign numeric values to columns
            for k, year_label in enumerate(year_labels):
                row[year_label] = numeric_values[k] if k < len(numeric_values) else ''
            
            # Check for data quality issues
            row['Data_Check'] = 'OK'
            row['Spill_Check'] = 'OK'
            
            for year_label in year_labels:
                if not row[year_label] or not re.match(r'^\d+\.?\d*$', str(row[year_label])):
                    row['Data_Check'] = 'CHECK'
            
            if row[year_labels[0]] and row[year_labels[0]] == row['Item_num']:
                row['Data_Check'] = 'CHECK'
                row['Spill_Check'] = 'SPILL'
            
            # Add a check for empty item names
            if not row['Item_nam']:
                row['Item_nam'] = 'Unnamed Item'
                row['Item_nam_Cleaned'] = 'Unnamed Item'
                row['Data_Check'] = 'CHECK'
            
            data.append(row)
    
    return data

def process_pdf(pdf_path):
    txt_path = pdf_path.replace('.pdf', '.txt')
    folder_name = os.path.basename(os.path.dirname(pdf_path))

    if os.path.exists(txt_path):
        with open(txt_path, 'r', encoding='utf-8') as file:
            text = file.read()
    else:
        text = extract_text_from_pdf(pdf_path)
        if text:
            with open(txt_path, 'w', encoding='utf-8') as file:
                file.write(text)
    if text is None:
        print(f"Failed to extract text from PDF: {pdf_path}")
        return None, None, None, None

    year_labels = detect_years(text, pdf_path)
    if not year_labels:
        print(f"Failed to detect years in: {pdf_path}")
        return None, None, None, None

    plan_non_plan_totals, has_plan_non_plan = extract_plan_non_plan_totals(text, year_labels)
    tables = extract_tables(text, year_labels, folder_name)
    
    all_data = []
    for context, table in tables:
        all_data.extend(parse_table(context, table, year_labels, folder_name))
    
    df = pd.DataFrame(all_data)
    
    if df.empty:
        print(f"Warning: No data extracted from the PDF: {pdf_path}")
        return df, [], None, year_labels

    df['Source PDF'] = os.path.basename(pdf_path)
    df['Item_nam_Cleaned'] = df['Item_nam'].apply(clean_item_name)
    df = check_ocr_errors_and_outliers(df, year_labels)

    # Add missing columns for 2013-14 files
    if '2013-14' in folder_name:
        if 'Demand' not in df.columns:
            df['Demand'] = ''
        if 'Sector_num' not in df.columns:
            df['Sector_num'] = ''
        if 'Sector_nam' not in df.columns:
            df['Sector_nam'] = ''

    columns = ['Demand', 'Sector_num', 'Sector_nam', 'MajorHead_num', 'MajorHead_nam', 
               'SubMajorHead_num', 'SubMajorHead_name', 'MinorHead_num', 'MinorHead_nam', 
               'GroupHead_num', 'GroupHead_nam', 'SubHead_num', 'SubHead_nam', 
               'Dept_num', 'Dept_nam', 'Voted_Charged', 'Item_num', 'Item_nam', 'Item_nam_Cleaned']
    
    for year_label in year_labels:
        columns.extend([year_label, f'{year_label}_Error'])
    
    columns.extend(['Data_Check', 'Spill_Check', 'Source PDF'])
    df = df.reindex(columns=columns)

    extracted_totals = {year_label: df[year_label].apply(safe_float).sum() for year_label in year_labels}
    
    discrepancies = []
    for year_label in year_labels:
        expected_total = plan_non_plan_totals[year_label]['Revenue'] + plan_non_plan_totals[year_label]['Capital']
        actual_total = extracted_totals[year_label]
        if abs(expected_total - actual_total) > 0.01:
            discrepancies.append(f"Discrepancy in {year_label}: Expected {expected_total}, Actual {actual_total}")
    
    if discrepancies:
        print(f"Discrepancies found in {os.path.basename(pdf_path)}:")
        for disc in discrepancies:
            print(disc)

    return df, discrepancies, plan_non_plan_totals, year_labels


# ... (include other necessary functions like check_ocr_errors_and_outliers, clean_item_name, safe_float, etc.)
def check_ocr_errors_and_outliers(df, year_labels):
    for year_label in year_labels:
        # Convert to numeric, treating non-convertible values as NaN
        df[year_label] = pd.to_numeric(df[year_label], errors='coerce')
        
        error_column = f'{year_label}_Error'
        df[error_column] = ''
        
        # Check for OCR errors (NaN values or empty strings)
        ocr_errors = df[year_label].isna() | (df[year_label] == '')
        df.loc[ocr_errors, error_column] = 'OCR Error'
        
        # Check for outliers (using a lower threshold)
        non_zero_values = df[df[year_label] != 0][year_label]
        if len(non_zero_values) > 0:
            median = non_zero_values.median()
            mad = np.abs(non_zero_values - median).median()
            lower_bound = median - 5 * mad
            upper_bound = median + 5 * mad
            outliers = (df[year_label] < lower_bound) | (df[year_label] > upper_bound)
            df.loc[outliers & ~ocr_errors, error_column] = 'Outlier'
            df.loc[outliers & ocr_errors, error_column] = 'OCR Error, Outlier'
        
        # Check for suspicious zero values
        zero_values = df[year_label] == 0
        df.loc[zero_values & (df[error_column] == ''), error_column] = 'Suspicious Zero'
    
    return df


def safe_float(x):
    try:
        return float(x) if x else 0.0
    except ValueError:
        print(f"Warning: Could not convert '{x}' to float. Treating as 0.")
        return 0.0


def check_ocr_errors(df, year_labels):
    potential_errors = []
    
    for year_label in year_labels:
        # Convert column to string and replace NaN with empty string
        col_data = df[year_label].astype(str).replace('nan', '')
        
        # Check for non-numeric values
        non_numeric = df[~col_data.apply(lambda x: x.replace('.', '').isdigit() if x else True)]
        if not non_numeric.empty:
            potential_errors.append(f"Non-numeric values found in {year_label}:")
            potential_errors.extend(non_numeric[['Item_num', 'Item_nam', year_label]].values.tolist())
    
    for year_label in year_labels:
        # Convert to numeric, coercing errors to NaN
        df[year_label] = pd.to_numeric(df[year_label], errors='coerce')
        
        # Calculate mean and std, ignoring NaN values
        mean = df[year_label].mean()
        std = df[year_label].std()

        # Identify outliers, ignoring NaN values
        outliers = df[(df[year_label] > mean + 3*std) | (df[year_label] < mean - 3*std)].dropna(subset=[year_label])
        if not outliers.empty:
            potential_errors.append(f"Potential outliers found in {year_label}:")
            potential_errors.extend(outliers[['Item_num', 'Item_nam', year_label]].values.tolist())

    return potential_errors



def process_folder(input_folder, output_folder):
    for root, dirs, files in os.walk(input_folder):
        if LIMIT_TO_FILE and LIMIT_TO_FILE not in files:
            continue
        for file in files:
            if LIMIT_TO_FILE and file != LIMIT_TO_FILE:
                continue
            if file.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, file)
                relative_path = os.path.relpath(root, input_folder)
                output_subfolder = os.path.join(output_folder, relative_path)
                
                os.makedirs(output_subfolder, exist_ok=True)
                
                output_base = os.path.join(output_subfolder, os.path.splitext(file)[0])
                
                print(f"Processing {pdf_path}")
                df, discrepancies, totals, year_labels = process_pdf(pdf_path)
                
                if df is not None and not df.empty:
                    # Save to Excel
                    try:
                        xlsx_filename = f"{output_base}.xlsx"
                        with pd.ExcelWriter(xlsx_filename, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='Extracted Data')
                            
                            # Create and save totals dataframe
                            if totals:
                                totals_data = []
                                for year_label in year_labels:
                                    total_row = {
                                        'Year': year_label,
                                        'Revenue': totals[year_label]['Revenue'],
                                        'Capital': totals[year_label]['Capital'],
                                        'Total': totals[year_label]['Revenue'] + totals[year_label]['Capital'],
                                        'DataFrame Total': df[year_label].apply(safe_float).sum(),
                                        'Check': 'OK' if abs(totals[year_label]['Revenue'] + totals[year_label]['Capital'] - df[year_label].apply(safe_float).sum()) < 0.01 else 'CHECK'
                                    }
                                    if 'Revenue Plan' in totals[year_label]:
                                        total_row.update({
                                            'Revenue Plan': totals[year_label]['Revenue Plan'],
                                            'Revenue Non-Plan': totals[year_label]['Revenue Non-Plan'],
                                            'Capital Plan': totals[year_label]['Capital Plan'],
                                            'Capital Non-Plan': totals[year_label]['Capital Non-Plan']
                                        })
                                    totals_data.append(total_row)
                                
                                totals_df = pd.DataFrame(totals_data)
                                totals_df.to_excel(writer, sheet_name='Account Totals', index=False)
                        
                        print(f"Data extracted and saved to '{xlsx_filename}'")
                    except Exception as e:
                        print(f"An error occurred while saving to Excel for {file}: {e}")
                
                else:
                    print(f"No data was extracted or the DataFrame is empty for {file}.")

def safe_float(x):
    try:
        return float(x) if x else 0.0
    except ValueError:
        print(f"Warning: Could not convert '{x}' to float. Treating as 0.")
        return 0.0


# Replace the existing main() function with this updated version
def main():
    input_folder = os.path.expanduser('~/Desktop/PFM data K/00 input trial')
    output_folder = os.path.expanduser('~/Desktop/PFM data K/Trial data')
    
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    process_folder(input_folder, output_folder)

if __name__ == "__main__":
    main()