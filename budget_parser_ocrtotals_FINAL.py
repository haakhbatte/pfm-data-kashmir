import os
import pytesseract
from pdf2image import convert_from_path
import re

def extract_text_from_pdf(pdf_path, max_pages=3):
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

def extract_numbers(line):
    return [float(part.replace(',', '')) for part in line.split() if part.replace('.', '').isdigit()]

def detect_years(text):
    lines = text.split('\n')
    for line in lines[:10]:  # Check first 10 lines
        numbers = re.findall(r'\d{4}-\d{4}', line)
        if len(numbers) == 4:
            return numbers
    return None

def extract_account_totals(text):
    lines = text.split('\n')
    revenue_totals = [0, 0, 0, 0]
    capital_totals = [0, 0, 0, 0]
    revenue_plan = [0, 0, 0, 0]
    revenue_non_plan = [0, 0, 0, 0]
    capital_plan = [0, 0, 0, 0]
    capital_non_plan = [0, 0, 0, 0]

    print("Searching for account totals...")
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
        if len(numbers) == 4:
            if revenue_section:
                if 'Non-Plan' in line:
                    revenue_non_plan = numbers
                elif 'Plan' in line:
                    revenue_plan = numbers
                else:
                    revenue_totals = numbers
            elif capital_section:
                if 'Non-Plan' in line:
                    capital_non_plan = numbers
                elif 'Plan' in line:
                    capital_plan = numbers
                else:
                    capital_totals = numbers

    if has_plan_non_plan:
        revenue_totals = [sum(x) for x in zip(revenue_plan, revenue_non_plan)]
        capital_totals = [sum(x) for x in zip(capital_plan, capital_non_plan)]
    else:
        # If no Plan/Non-Plan, use the last found totals
        pass

    print(f"Found revenue totals: {revenue_totals}")
    print(f"Found capital totals: {capital_totals}")
    print(f"Revenue Plan: {revenue_plan}")
    print(f"Revenue Non-Plan: {revenue_non_plan}")
    print(f"Capital Plan: {capital_plan}")
    print(f"Capital Non-Plan: {capital_non_plan}")

    return revenue_totals, capital_totals, revenue_plan, revenue_non_plan, capital_plan, capital_non_plan

# Main execution
pdf_path = '/Users/aashnajamal/Desktop/PFM data K/2017-18/07 education.pdf'
print(f"Processing {pdf_path}")

text = extract_text_from_pdf(pdf_path)
if text is None:
    print("Failed to extract text from PDF. Please check if the file is accessible and not corrupted.")
else:
    years = detect_years(text)
    if not years:
        print("Failed to detect years. Using default years.")
        years = ['2015-2016', '2016-2017', '2016-2017', '2017-2018']

    revenue_totals, capital_totals, revenue_plan, revenue_non_plan, capital_plan, capital_non_plan = extract_account_totals(text)

    print("\nExtracted Account Totals:")
    for i, year in enumerate(years):
        print(f"\n{year}:")
        print(f"  Revenue: {revenue_totals[i]:.2f}")
        print(f"    Plan: {revenue_plan[i]:.2f}")
        print(f"    Non-Plan: {revenue_non_plan[i]:.2f}")
        print(f"  Capital: {capital_totals[i]:.2f}")
        print(f"    Plan: {capital_plan[i]:.2f}")
        print(f"    Non-Plan: {capital_non_plan[i]:.2f}")
        print(f"  Total: {revenue_totals[i] + capital_totals[i]:.2f}")