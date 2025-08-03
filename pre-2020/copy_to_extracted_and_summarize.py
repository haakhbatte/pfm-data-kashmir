"""
Clone the lone sheet from every workbook in
2014-15_arbeena\Cleaned_Items into the workbook in
2014-15_arbeena\Extracted whose filename begins with the
same two characters, replacing that workbook’s first sheet.

✔  Values, formulas, number‑formats, fonts, fills, borders
✔  Column widths & row heights
✔  Merged ranges, freeze panes, sheet view, page setup
✖  Charts, pictures & other drawing objects are NOT copied
    (use xlwings / COM if those matter)

Requires:  pip install openpyxl>=3.1
"""

import os
from copy import copy
from collections import defaultdict
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------
def copy_sheet(src_ws, dst_ws):
    """Deep‑copy a worksheet’s cells + layout into an empty dst_ws."""
    # 1️⃣ Cells (values + full style objects)
    for row in src_ws.iter_rows():
        for cell in row:
            new = dst_ws.cell(row=cell.row, column=cell.column, value=cell.value)
            if cell.has_style:
                new.font          = copy(cell.font)
                new.border        = copy(cell.border)
                new.fill          = copy(cell.fill)
                new.number_format = copy(cell.number_format)
                new.protection    = copy(cell.protection)
                new.alignment     = copy(cell.alignment)

    # 2️⃣ Column widths
    for col_letter, col_dim in src_ws.column_dimensions.items():
        dst_ws.column_dimensions[col_letter].width = col_dim.width

    # 3️⃣ Row heights
    for row_idx, row_dim in src_ws.row_dimensions.items():
        dst_ws.row_dimensions[row_idx].height = row_dim.height

    # 4️⃣ Merged ranges
    for rng in src_ws.merged_cells.ranges:
        dst_ws.merge_cells(str(rng))

    # 5️⃣ Freeze panes / sheet view / page setup
    dst_ws.freeze_panes     = src_ws.freeze_panes
    dst_ws.sheet_view.selection = copy(src_ws.sheet_view.selection)
    dst_ws.sheet_view.zoomScale = src_ws.sheet_view.zoomScale
    dst_ws.sheet_view.zoomScaleNormal = src_ws.sheet_view.zoomScaleNormal
    dst_ws.sheet_view.showGridLines = src_ws.sheet_view.showGridLines
    dst_ws.page_setup       = copy(src_ws.page_setup)
    dst_ws.sheet_properties = copy(src_ws.sheet_properties)


# ---------------------------------------------------------------------
CLEANED_DIR   = r"2019-20\Cleaned_Items"
EXTRACTED_DIR = r"2019-20\Extracted"
XL_EXTS       = (".xlsx", ".xlsm", ".xltx", ".xltm")

# ‣ Map cleaned files by their first two characters
cleaned_by_key = defaultdict(list)
for fn in os.listdir(CLEANED_DIR):
    if fn.lower().endswith(XL_EXTS):
        cleaned_by_key[fn[:2]].append(os.path.join(CLEANED_DIR, fn))

for dst_name in os.listdir(EXTRACTED_DIR):
    if not dst_name.lower().endswith(XL_EXTS):
        continue

    key      = dst_name[:2]
    dst_path = os.path.join(EXTRACTED_DIR, dst_name)

    # --- find matching source workbook --------------------------------
    if key not in cleaned_by_key:
        print(f"⚠  No cleaned file with prefix {key} for {dst_name}")
        continue
    if len(cleaned_by_key[key]) > 1:
        print(f"⚠  Multiple cleaned files with prefix {key}; skipped {dst_name}")
        continue
    src_path = cleaned_by_key[key][0]

    # --- open workbooks -----------------------------------------------
    wb_src = load_workbook(src_path, data_only=False)  # keep formulas
    wb_dst = load_workbook(dst_path)

    src_ws = wb_src.worksheets[0]

    # --- delete the old first sheet before inserting the new one -----
    old_first_sheet = wb_dst.worksheets[0]
    wb_dst.remove(old_first_sheet)

    # --- insert cloned sheet with original title (no name clash) -----
    new_ws = wb_dst.create_sheet(title=src_ws.title, index=0)
    copy_sheet(src_ws, new_ws)

    # --- fill totals on the second sheet ---------------------------------
    totals_ws = wb_dst['Account Totals']              # second sheet
    src_name  = new_ws.title.replace("'", "''")       # make sheet name formula‑safe

    for col, dest in zip(("T", "V", "X", "Z"), ("E2", "E3", "E4", "E5")):
        # Excel will calculate the sum when the file is opened
        totals_ws[dest] = f"=SUM('{src_name}'!{col}:{col})"


    wb_dst.save(dst_path)
    print(f"✓  {dst_name} updated with {os.path.basename(src_path)}")

print("All done.")
