import os
import pytesseract
from pdf2image import convert_from_path
import re
import pandas as pd

def extract_text_from_pdf(pdf_path, max_pages=None):
    try:
        pages = convert_from_path(pdf_path, first_page=1, last_page=max_pages)
        text = ""
        for page in pages:
            text += pytesseract.image_to_string(page, config='--psm 6 --oem 3 -c preserve_interword_spaces=1') + "\n"
        return text
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return None

def clean_text(text):
    text = ''.join(char for char in text if ord(char) < 128)
    return ' '.join(text.split())

def detect_years(text):
    lines = text.split('\n')
    for line in lines[:20]:  # Check first 20 lines to be safe
        numbers = re.findall(r'\d{4}-\d{4}|\d{4}-\d{2}|\d{4}', line)
        if len(numbers) == 4:
            # Convert two-digit years to four-digit years
            full_years = [year if len(year) == 7 else f"{year[:2]}{int(year[2:4])+1:02d}-{year[5:]}" if len(year) == 7 else f"20{year[-2:]}-20{int(year[-2:])+1:02d}" if len(year) == 4 else year for year in numbers]
            return full_years
    print("Warning: Unable to detect years. Please check the PDF content.")
    return None

def extract_numbers(line):
    return [float(part.replace(',', '')) for part in line.split() if part.replace('.', '').isdigit()]

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

def extract_plan_non_plan_totals(text, years):
    lines = text.split('\n')
    totals = {f"{years[0]}_accounts": {'Revenue': 0, 'Revenue Plan': 0, 'Revenue Non-Plan': 0, 'Capital': 0, 'Capital Plan': 0, 'Capital Non-Plan': 0},
              f"{years[1]}_estimates": {'Revenue': 0, 'Revenue Plan': 0, 'Revenue Non-Plan': 0, 'Capital': 0, 'Capital Plan': 0, 'Capital Non-Plan': 0},
              f"{years[2]}_revisedestimate": {'Revenue': 0, 'Revenue Plan': 0, 'Revenue Non-Plan': 0, 'Capital': 0, 'Capital Plan': 0, 'Capital Non-Plan': 0},
              f"{years[3]}_estimates": {'Revenue': 0, 'Revenue Plan': 0, 'Revenue Non-Plan': 0, 'Capital': 0, 'Capital Plan': 0, 'Capital Non-Plan': 0}}
    
    revenue_section = False
    capital_section = False
    plan_found = False
    non_plan_found = False

    for line in lines:
        if 'REVENUE ACCOUNT' in line.upper():
            revenue_section = True
            capital_section = False
            continue
        if 'CAPITAL ACCOUNT' in line.upper():
            revenue_section = False
            capital_section = True
            continue

        numbers = extract_numbers(line)
        if len(numbers) == 4:
            if revenue_section:
                if 'Plan' in line and 'Non-Plan' not in line:
                    plan_found = True
                    for i, (year, value) in enumerate(zip(years, numbers)):
                        year_key = f"{year}_{'accounts' if i == 0 else 'estimates' if i == 3 else 'revisedestimate'}"
                        totals[year_key]['Revenue Plan'] = value
                elif 'Non-Plan' in line:
                    non_plan_found = True
                    for i, (year, value) in enumerate(zip(years, numbers)):
                        year_key = f"{year}_{'accounts' if i == 0 else 'estimates' if i == 3 else 'revisedestimate'}"
                        totals[year_key]['Revenue Non-Plan'] = value
                else:
                    for i, (year, value) in enumerate(zip(years, numbers)):
                        year_key = f"{year}_{'accounts' if i == 0 else 'estimates' if i == 3 else 'revisedestimate'}"
                        totals[year_key]['Revenue'] = value
            elif capital_section:
                if 'Plan' in line and 'Non-Plan' not in line:
                    plan_found = True
                    for i, (year, value) in enumerate(zip(years, numbers)):
                        year_key = f"{year}_{'accounts' if i == 0 else 'estimates' if i == 3 else 'revisedestimate'}"
                        totals[year_key]['Capital Plan'] = value
                elif 'Non-Plan' in line:
                    non_plan_found = True
                    for i, (year, value) in enumerate(zip(years, numbers)):
                        year_key = f"{year}_{'accounts' if i == 0 else 'estimates' if i == 3 else 'revisedestimate'}"
                        totals[year_key]['Capital Non-Plan'] = value
                else:
                    for i, (year, value) in enumerate(zip(years, numbers)):
                        year_key = f"{year}_{'accounts' if i == 0 else 'estimates' if i == 3 else 'revisedestimate'}"
                        totals[year_key]['Capital'] = value

    # If Plan and Non-Plan are found, calculate the totals
    if plan_found and non_plan_found:
        for year_key in totals:
            totals[year_key]['Revenue'] = totals[year_key]['Revenue Plan'] + totals[year_key]['Revenue Non-Plan']
            totals[year_key]['Capital'] = totals[year_key]['Capital Plan'] + totals[year_key]['Capital Non-Plan']

    return totals, plan_found or non_plan_found

def extract_account_totals(text, years):
    lines = text.split('\n')
    revenue_totals = None
    capital_totals = None

    print("Searching for account totals...")
    revenue_section = False
    capital_section = False
    capital_lines = []

    for i, line in enumerate(lines):
        print(f"Line {i}: {line}")  # Debug print
        
        if 'Detail Head Code and Description' in line:
            break

        if 'REVENUE ACCOUNT' in line.upper():
            revenue_section = True
            capital_section = False
            continue

        if 'CAPITAL ACCOUNT' in line.upper():
            if revenue_section:
                revenue_totals = [float(part.replace(',', '')) for part in lines[i-1].split() if part.replace('.', '').isdigit()]
            revenue_section = False
            capital_section = True
            continue

        if capital_section:
            numbers = [float(part.replace(',', '')) for part in line.split() if part.replace('.', '').isdigit()]
            if len(numbers) == 4:  # We're looking for 4 numbers in a row
                capital_lines.append(numbers)

    if capital_lines:
        capital_totals = capital_lines[-1]  # Take the last line of numbers

    if revenue_totals and capital_totals:
        print(f"Found revenue totals: {revenue_totals}")
        print(f"Found capital totals: {capital_totals}")
        return {
            f'{years[0]}_accounts': {'Revenue': revenue_totals[0], 'Capital': capital_totals[0], 'Total': revenue_totals[0] + capital_totals[0]},
            f'{years[1]}_estimates': {'Revenue': revenue_totals[1], 'Capital': capital_totals[1], 'Total': revenue_totals[1] + capital_totals[1]},
            f'{years[2]}_revisedestimate': {'Revenue': revenue_totals[2], 'Capital': capital_totals[2], 'Total': revenue_totals[2] + capital_totals[2]},
            f'{years[3]}_estimates': {'Revenue': revenue_totals[3], 'Capital': capital_totals[3], 'Total': revenue_totals[3] + capital_totals[3]}
        }

    print("Warning: Account totals not found or incomplete.")
    return None

def extract_tables(text, years):
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
        elif ('Total' in line or 'Sub Total' in line) and current_table:
            tables.append((context.copy(), current_table))
            current_table = []
            new_context = previous_context.copy()
            new_context.update({k: v for k, v in context.items() if v})
            context = new_context
            previous_context = context.copy()
            context['Dept_num'] = context['Dept_nam'] = ''
        
        sub_major_num, sub_major_name = find_sub_major_head(lines, i)
        if sub_major_num and sub_major_num != context['SubMajorHead_num']:
            context['SubMajorHead_num'] = sub_major_num
            context['SubMajorHead_name'] = sub_major_name
            context['MinorHead_num'] = context['MinorHead_nam'] = ''
            context['GroupHead_num'] = context['GroupHead_nam'] = ''
        
        group_head_num, group_head_name = find_group_head(lines, i)
        if group_head_num and group_head_num != context['GroupHead_num']:
            context['GroupHead_num'] = group_head_num
            context['GroupHead_nam'] = group_head_name

    if current_table:
        tables.append((context.copy(), current_table))
    
    return tables

def parse_table(context, table, years):
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
            row[f'{years[0]}_accounts'] = numeric_values[0] if len(numeric_values) > 0 else ''
            row[f'{years[1]}_estimates'] = numeric_values[1] if len(numeric_values) > 1 else ''
            row[f'{years[2]}_revisedestimate'] = numeric_values[2] if len(numeric_values) > 2 else ''
            row[f'{years[3]}_estimates'] = numeric_values[3] if len(numeric_values) > 3 else ''
            
            # Check for data quality issues
            row['Data_Check'] = 'OK'
            row['Spill_Check'] = 'OK'
            
            for year in years:
                col = f'{year}_accounts' if year == years[0] else f'{year}_estimates' if year == years[3] else f'{year}_revisedestimate'
                if not row[col] or not re.match(r'^\d+\.?\d*$', str(row[col])):
                    row['Data_Check'] = 'CHECK'
            
            if row[f'{years[0]}_accounts'] and row[f'{years[0]}_accounts'] == row['Item_num']:
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
    if text is None:
        print("Failed to extract text from PDF.")
        return None, None, None

    years = detect_years(text)
    if not years:
        print("Failed to detect years. Cannot proceed without year information.")
        return None, None, None

    plan_non_plan_totals, has_plan_non_plan = extract_plan_non_plan_totals(text, years)
    account_totals = extract_account_totals(text, years)
    tables = extract_tables(text, years)
    all_data = []
    for context, table in tables:
        all_data.extend(parse_table(context, table, years))
    df = pd.DataFrame(all_data)
    
    if df.empty:
        print("Warning: No data extracted from the PDF.")
        return df, [], None

    year_keys = [f"{years[0]}_accounts", f"{years[1]}_estimates", f"{years[2]}_revisedestimate", f"{years[3]}_estimates"]
    extracted_totals = {
        year_key: df[year_key].apply(safe_float).sum()
        for year_key in year_keys
    }
    
    discrepancies = []
    if has_plan_non_plan:
        for year_key in year_keys:
            expected_total = plan_non_plan_totals[year_key]['Revenue'] + plan_non_plan_totals[year_key]['Capital']
            actual_total = extracted_totals[year_key]
            if abs(expected_total - actual_total) > 0.01:
                discrepancies.append(f"Discrepancy in {year_key}: Expected {expected_total}, Actual {actual_total}")
    elif account_totals:
        for year_key, totals in zip(year_keys, account_totals.values()):
            expected_total = totals['Total']
            actual_total = extracted_totals[year_key]
            if abs(expected_total - actual_total) > 0.01:
                discrepancies.append(f"Discrepancy in {year_key}: Expected {expected_total}, Actual {actual_total}")
    
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
    
    return df, discrepancies, plan_non_plan_totals if has_plan_non_plan else account_totals

def check_ocr_errors(df, years):
    potential_errors = []
    
    for year in years:
        col = f'{year}_accounts' if year == years[0] else f'{year}_estimates' if year == years[3] else f'{year}_revisedestimate'
        # Convert column to string and replace NaN with empty string
        col_data = df[col].astype(str).replace('nan', '')
        
        # Check for non-numeric values
        non_numeric = df[~col_data.apply(lambda x: x.replace('.', '').isdigit() if x else True)]
        if not non_numeric.empty:
            potential_errors.append(f"Non-numeric values found in {col}:")
            potential_errors.extend(non_numeric[['Item_num', 'Item_nam', col]].values.tolist())
    
    for year in years:
        col = f'{year}_accounts' if year == years[0] else f'{year}_estimates' if year == years[3] else f'{year}_revisedestimate'
        # Convert to numeric, coercing errors to NaN
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calculate mean and std, ignoring NaN values
        mean = df[col].mean()
        std = df[col].std()

        # Identify outliers, ignoring NaN values
        outliers = df[(df[col] > mean + 3*std) | (df[col] < mean - 3*std)].dropna(subset=[col])
        if not outliers.empty:
            potential_errors.append(f"Potential outliers found in {col}:")
            potential_errors.extend(outliers[['Item_num', 'Item_nam', col]].values.tolist())

    return potential_errors

# Main execution
if __name__ == "__main__":
    pdf_path = '/Users/aashnajamal/Desktop/PFM data K/2017-18/07 education.pdf'
    output_file = '/Users/aashnajamal/Desktop/budget_data_allgen.xlsx'

    print(f"Processing {pdf_path}")
    df, discrepancies, totals = process_pdf(pdf_path)

    if df is not None and not df.empty:
        df['Source PDF'] = os.path.basename(pdf_path)

        # Detect years
        text = extract_text_from_pdf(pdf_path)
        years = detect_years(text)
        if not years:
            print("Failed to detect years. Cannot proceed without year information.")
            exit()

        # Reorder and rename columns
        columns = ['Demand', 'Sector_num', 'Sector_nam', 'MajorHead_num', 'MajorHead_nam', 
                   'SubMajorHead_num', 'SubMajorHead_name', 'MinorHead_num', 'MinorHead_nam', 
                   'GroupHead_num', 'GroupHead_nam', 'SubHead_num', 'SubHead_nam', 
                   'Dept_num', 'Dept_nam', 'Voted_Charged', 'Item_num', 'Item_nam']
        columns.extend([f'{years[0]}_accounts', f'{years[1]}_estimates', f'{years[2]}_revisedestimate', f'{years[3]}_estimates'])
        columns.extend(['Data_Check', 'Spill_Check', 'Source PDF'])
        df = df.reindex(columns=columns)

        print(f"Total rows extracted: {len(df)}")
        print(f"Columns: {df.columns}")
        print("First few rows:")
        print(df.head())

        # Check for OCR errors
        try:
            ocr_errors = check_ocr_errors(df, years)
            if ocr_errors:
                print("\nPotential OCR errors detected:")
                for error in ocr_errors:
                    print(error)
        except Exception as e:
            print(f"An error occurred while checking for OCR errors: {e}")

        # Print and save totals
        if totals:
            print("\nExtracted Account Totals:")
            totals_data = []
            year_keys = [f"{years[0]}_accounts", f"{years[1]}_estimates", f"{years[2]}_revisedestimate", f"{years[3]}_estimates"]
            for year_key in year_keys:
                total_revenue = totals[year_key]['Revenue']
                total_capital = totals[year_key]['Capital']
                total = total_revenue + total_capital
                
                totals_data.append({
                    'Year': year_key,
                    'Revenue': total_revenue,
                    'Revenue Plan': totals[year_key]['Revenue Plan'],
                    'Revenue Non-Plan': totals[year_key]['Revenue Non-Plan'],
                    'Capital': total_capital,
                    'Capital Plan': totals[year_key]['Capital Plan'],
                    'Capital Non-Plan': totals[year_key]['Capital Non-Plan'],
                    'Total': total,
                })
                
                df_total = df[year_key].apply(safe_float).sum()
                totals_data[-1]['DataFrame Total'] = df_total
                totals_data[-1]['Check'] = 'OK' if abs(total - df_total) < 0.01 else 'CHECK'
                
                # Print the totals
                print(f"\n{year_key}:")
                print(f"  Revenue: {total_revenue:.2f}")
                print(f"    Plan: {totals[year_key]['Revenue Plan']:.2f}")
                print(f"    Non-Plan: {totals[year_key]['Revenue Non-Plan']:.2f}")
                print(f"  Capital: {total_capital:.2f}")
                print(f"    Plan: {totals[year_key]['Capital Plan']:.2f}")
                print(f"    Non-Plan: {totals[year_key]['Capital Non-Plan']:.2f}")
                print(f"  Total: {total:.2f}")
                print(f"  DataFrame Total: {df_total:.2f}")
                print(f"  Check: {totals_data[-1]['Check']}")

            totals_df = pd.DataFrame(totals_data)

            # Save to Excel
            try:
                with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Extracted Data')
                    totals_df.to_excel(writer, sheet_name='Account Totals', index=False)

                print(f"Data extracted and saved to '{output_file}'")
            except Exception as e:
                print(f"An error occurred while saving to Excel: {e}")

        if discrepancies:
            print("\nWarning: Discrepancies found. Please review the extracted data and the original PDF.")
    else:
        print("No data was extracted or the DataFrame is empty.")