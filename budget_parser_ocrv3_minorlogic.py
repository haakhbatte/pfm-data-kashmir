import os
import pytesseract
from pdf2image import convert_from_path
import re
import pandas as pd

def extract_text_from_pdf(pdf_path):
    pages = convert_from_path(pdf_path)
    text = ""
    for page in pages:
        text += pytesseract.image_to_string(page, config='--psm 6 --oem 3 -c preserve_interword_spaces=1') + "\n"
    return text

def clean_text(text):
    text = ''.join(char for char in text if ord(char) < 128)
    return ' '.join(text.split())

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

def extract_totals_from_first_page(text):
    lines = text.split('\n')
    totals = {
        'Revenue Account': {'2015-2016': 0, '2016-2017': 0, '2016-2017 RE': 0, '2017-2018': 0},
        'Capital Account': {'2015-2016': 0, '2016-2017': 0, '2016-2017 RE': 0, '2017-2018': 0}
    }
    for line in lines:
        if 'Total Revenue Account' in line:
            parts = line.split()
            for i, year in enumerate(['2015-2016', '2016-2017', '2016-2017 RE', '2017-2018']):
                try:
                    totals['Revenue Account'][year] = float(parts[-4+i])
                except (ValueError, IndexError):
                    print(f"Warning: Could not extract Revenue Account total for {year}")
        elif 'Total Capital Account' in line:
            parts = line.split()
            for i, year in enumerate(['2015-2016', '2016-2017', '2016-2017 RE', '2017-2018']):
                try:
                    totals['Capital Account'][year] = float(parts[-4+i])
                except (ValueError, IndexError):
                    print(f"Warning: Could not extract Capital Account total for {year}")
    return totals

def extract_tables(text):
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
    for i, line in enumerate(lines):
        line = clean_text(line)
        
        if 'Demand Number' in line:
            match = re.search(r'Demand Number\s*:\s*(\d+)', line)
            if match:
                context['Demand'] = match.group(1)
        elif re.match(r'Sector\s+([A-Z])\s+(.+)', line):
            match = re.match(r'Sector\s+([A-Z])\s+(.+)', line)
            context['Sector_num'], context['Sector_nam'] = match.groups()
        elif 'Major Head' in line:
            match = re.search(r'Major Head\s+(\d{4})\s+(.+)', line)
            if match:
                context['MajorHead_num'], context['MajorHead_nam'] = match.groups()
                context['SubMajorHead_num'] = context['SubMajorHead_name'] = ''
                context['MinorHead_num'] = context['MinorHead_nam'] = ''
                context['GroupHead_num'] = context['GroupHead_nam'] = ''
        elif re.search(r'Sub\s*Major\s*Head', line, re.IGNORECASE):
            match = re.search(r'Sub\s*Major\s*Head\s+(\d{2})\s*(.+)?', line, re.IGNORECASE)
            if match:
                context['SubMajorHead_num'] = match.group(1)
                context['SubMajorHead_name'] = match.group(2) if match.group(2) else ''
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
            current_table.append(line)
        elif 'Total' in line or 'Sub Total' in line:
            if current_table:
                tables.append((context.copy(), current_table))
                current_table = []
                new_context = previous_context.copy()
                new_context.update({k: v for k, v in context.items() if v})
                context = new_context
                previous_context = context.copy()
                context['Dept_num'] = context['Dept_nam'] = ''
        
        # Check for Sub Major Head changes
        sub_major_match = re.search(r'Sub\s*Major\s*Head\s+(\d{2})\s*(.+)?', line, re.IGNORECASE)
        if sub_major_match:
            new_sub_major_num = sub_major_match.group(1)
            new_sub_major_name = sub_major_match.group(2) if sub_major_match.group(2) else ''
            if new_sub_major_num != context['SubMajorHead_num']:
                context['SubMajorHead_num'] = new_sub_major_num
                context['SubMajorHead_name'] = new_sub_major_name
                context['MinorHead_num'] = context['MinorHead_nam'] = ''
                context['GroupHead_num'] = context['GroupHead_nam'] = ''

        # Check for Minor Head changes
        minor_match = re.search(r'Minor Head\s+(\d{3})\s+(.+)', line)
        if minor_match:
            new_minor_num, new_minor_name = minor_match.groups()
            if new_minor_num != context['MinorHead_num']:
                context['MinorHead_num'] = new_minor_num
                context['MinorHead_nam'] = new_minor_name
                context['GroupHead_num'] = context['GroupHead_nam'] = ''

        # Check for Group Head changes
        group_match = re.search(r'Group Head\s+(\d+)\s+(.+)', line)
        if group_match:
            new_group_num, new_group_name = group_match.groups()
            if new_group_num != context['GroupHead_num']:
                context['GroupHead_num'] = new_group_num
                context['GroupHead_nam'] = new_group_name

    if current_table:
        tables.append((context.copy(), current_table))
    
    return tables

def parse_table(context, table):
    data = []
    for line in table:
        parts = line.split()
        if len(parts) >= 2 and re.match(r'^\d{3}$', parts[0]):  # Check if first part is a 3-digit number
            row = context.copy()
            row['Item_num'] = parts[0]
            
            # Find numeric values (rightmost 4 columns)
            numeric_values = [part for part in parts[-4:] if re.match(r'^\d+\.?\d*$', part)]
            
            # Extract item name (everything between item number and numeric values)
            row['Item_nam'] = ' '.join(parts[1:-len(numeric_values)]).strip()
            
            # Assign numeric values to columns
            row['2015-2016 Accounts'] = numeric_values[0] if len(numeric_values) > 0 else ''
            row['2016-2017 Estimates'] = numeric_values[1] if len(numeric_values) > 1 else ''
            row['2016-2017 Revised Estimates'] = numeric_values[2] if len(numeric_values) > 2 else ''
            row['2017-2018 Estimates'] = numeric_values[3] if len(numeric_values) > 3 else ''
            
            # Check for data quality issues
            row['Data_Check'] = 'OK'
            row['Spill_Check'] = 'OK'
            
            for col in ['2015-2016 Accounts', '2016-2017 Estimates', '2016-2017 Revised Estimates', '2017-2018 Estimates']:
                if not row[col] or not re.match(r'^\d+\.?\d*$', str(row[col])):
                    row['Data_Check'] = 'CHECK'
            
            if row['2015-2016 Accounts'] and row['2015-2016 Accounts'] == row['Item_num']:
                row['Data_Check'] = 'CHECK'
                row['Spill_Check'] = 'SPILL'
            
            data.append(row)
    return data

def safe_float(x):
    try:
        return float(x) if x else 0.0
    except ValueError:
        print(f"Warning: Could not convert '{x}' to float. Treating as 0.")
        return 0.0

def process_pdf(pdf_path):
    text = extract_text_from_pdf(pdf_path)
    first_page_totals = extract_totals_from_first_page(text)
    tables = extract_tables(text)
    all_data = []
    for context, table in tables:
        all_data.extend(parse_table(context, table))
    df = pd.DataFrame(all_data)
    
    if df.empty:
        print("Warning: No data extracted from the PDF.")
        return df, []
    
    extracted_totals = {
        '2015-2016': df['2015-2016 Accounts'].apply(safe_float).sum(),
        '2016-2017': df['2016-2017 Estimates'].apply(safe_float).sum(),
        '2016-2017 RE': df['2016-2017 Revised Estimates'].apply(safe_float).sum(),
        '2017-2018': df['2017-2018 Estimates'].apply(safe_float).sum()
    }
    
    discrepancies = []
    for year in ['2015-2016', '2016-2017', '2016-2017 RE', '2017-2018']:
        expected_total = first_page_totals['Revenue Account'][year] + first_page_totals['Capital Account'][year]
        actual_total = extracted_totals[year]
        if abs(expected_total - actual_total) > 0.01:
            discrepancies.append(f"Discrepancy in {year}: Expected {expected_total}, Actual {actual_total}")
    
    if discrepancies:
        print("Discrepancies found:")
        for disc in discrepancies:
            print(disc)
        print("Please check the following:")
        print("1. Ensure all pages are properly scanned and OCR'd")
        print("2. Look for any missing tables or data in the PDF")
        print("3. Verify the totals on the first page of the PDF")
    else:
        print("No discrepancies found. Totals match.")
    
    return df, discrepancies

def check_ocr_errors(df):
    potential_errors = []
    
    numeric_columns = ['2015-2016 Accounts', '2016-2017 Estimates', '2016-2017 Revised Estimates', '2017-2018 Estimates']
    for col in numeric_columns:
        non_numeric = df[~df[col].apply(lambda x: x.replace('.', '').isdigit() if x else True)]
        if not non_numeric.empty:
            potential_errors.append(f"Non-numeric values found in {col}:")
            potential_errors.extend(non_numeric[['Item_num', 'Item_nam', col]].values.tolist())
    
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        mean = df[col].mean()
        std = df[col].std()
        outliers = df[(df[col] > mean + 3*std) | (df[col] < mean - 3*std)]
        if not outliers.empty:
            potential_errors.append(f"Potential outliers found in {col}:")
            potential_errors.extend(outliers[['Item_num', 'Item_nam', col]].values.tolist())
    
    return potential_errors

# Main execution
pdf_path = '/Users/aashnajamal/Desktop/Budget_PDFs/2023-2024/27_27-Higher_Education.pdf'
output_file = '/Users/aashnajamal/Desktop/budget_data_allgen.xlsx'

print(f"Processing {pdf_path}")
df, discrepancies = process_pdf(pdf_path)
df['Source PDF'] = '07 education.pdf'

result = df

columns = ['Demand', 'Sector_num', 'Sector_nam', 'MajorHead_num', 'MajorHead_nam', 
           'SubMajorHead_num', 'SubMajorHead_name', 'MinorHead_num', 'MinorHead_nam', 
           'GroupHead_num', 'GroupHead_nam', 'SubHead_num', 'SubHead_nam', 
           'Dept_num', 'Dept_nam', 'Voted_Charged', 'Item_num', 'Item_nam', 
           '2015-2016 Accounts', '2016-2017 Estimates', '2016-2017 Revised Estimates', 
           '2017-2018 Estimates', 'Data_Check', 'Spill_Check', 'Source PDF']
result = result.reindex(columns=columns)

print(f"Total rows extracted: {len(result)}")
print(f"Columns: {result.columns}")
if not result.empty:
    print("First few rows:")
    print(result.head())
else:
    print("No data was extracted.")

ocr_errors = check_ocr_errors(result)
if ocr_errors:
    print("\nPotential OCR errors detected:")
    for error in ocr_errors:
        print(error)

result.to_excel(output_file, index=False)
print(f"Data extracted and saved to '{output_file}'")

if discrepancies:
    print("\nWarning: Discrepancies found. Please review the extracted data and the original PDF.")