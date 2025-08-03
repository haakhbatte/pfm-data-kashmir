import pandas as pd
import os
from pathlib import Path

# Directory containing the Excel files
input_dir = Path(r"2019-20\Cleaned_Items")
output_dir = Path(r"2019-20\Match_Files")  # same directory for output

# Updated column mappings and desired sheet names
columns_to_extract = [
    ('MajorHead_num', 'MajorHead_nam', 'Major_Head'),
    ('SubMajorHead_num', 'SubMajorHead_name', 'Submajor_Head'),
    ('MinorHead_num', 'MinorHead_nam', 'Minor_Head'),
    ('GroupHead_num', 'GroupHead_nam', 'Group_Head'),
    ('SubHead_num', 'SubHead_nam', 'Subhead'),
    ('Dept_num', 'Dept_nam', 'Department'),
    ('Item_num', 'Item_nam', 'Items')
]

# Process all Excel files in the directory
for file in input_dir.glob("*.xlsx"):
    try:
        df = pd.read_excel(file, dtype=str)  # read all as string

        output_file = output_dir / f"match_file_{file.stem}.xlsx"

        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for num_col, name_col, sheet_name in columns_to_extract:
                if num_col in df.columns and name_col in df.columns:
                    if(num_col=='Item_num' or num_col=='GroupHead_num'):
                        temp_df = df[[num_col, name_col]].drop_duplicates(subset=[num_col])
                    else:
                        temp_df = df[[num_col, name_col]].drop_duplicates(subset=[name_col])
                    temp_df[num_col] = temp_df[num_col].astype(str)
                    temp_df = temp_df.sort_values(by=num_col)
                    temp_df.to_excel(writer, sheet_name=sheet_name, index=False, na_rep='')
    except Exception as e:
        print(f"Error processing {file.name}: {e}")
