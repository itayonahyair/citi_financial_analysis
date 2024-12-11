import pandas as pd
import utils as ut


def find_column_index_for_quarter_year(summary_df, quarter, year):
    """
    Detect the column index for a given quarter and year in the specified sheet of an Excel file.
    """
    # Detect the header rows
    def detect_header_rows(df):
        """
        Detects the rows for quarters (Qx) and corresponding years in the DataFrame.
        """
        header_row_with_q = None
        header_row_with_years = None

        for idx, row in df.iterrows():
            # Check for 'Qx' pattern (e.g., Q1, 3Q, 4Q)
            q_count = row.astype(str).str.contains(r'\dQ|Q\d', case=False, na=False).sum()

            if q_count > 1 and header_row_with_q is None:  # Identify first row with multiple 'Q'
                header_row_with_q = idx

            # Check if the next row contains numeric values (for years)
            if header_row_with_q is not None and idx == header_row_with_q + 1:
                year_count = row.astype(str).str.fullmatch(r'\d{4}', na=False).sum()
                if year_count > 1:  # Check for at least two years
                    header_row_with_years = idx
                    break

        return header_row_with_q, header_row_with_years

    # Detect header rows
    header_q_row, header_year_row = detect_header_rows(summary_df)

    # Validate detected rows
    if header_q_row is None or header_year_row is None:
        return None, None

    # Extract quarter and year rows
    quarter_row = summary_df.iloc[header_q_row].fillna('').astype(str)
    year_row = summary_df.iloc[header_year_row].fillna('').astype(str)

    # Search for the matching quarter and year
    for col_idx, (q, y) in enumerate(zip(quarter_row, year_row)):
        q_ref_as_lst = set(list(q.strip().upper()))
        q_as_lst = set(list(quarter.upper()))
        if q_as_lst == q_ref_as_lst and y.strip() == year:
            return header_year_row, col_idx

    # If no match found
    return header_year_row, None


def get_metrics_from_df(df, text_idx, column_index):
    """
    For each metric, find the single best row in the DataFrame that matches it, starting from `text_idx`.
    Uses both the original loose containment and fuzzy matching to pick the best possible match.
    """
    metrics = [
        "CET1 Capital Ratio",
        "Tangible book value per share",
        "Book value per share",
        "Net income",
        "Revenues"
    ]
    metric_to_val = {}

    # Iterate over each metric and find the best match
    for metric in metrics:
        normalized_metric = metric.lower()

        best_score = -1
        best_value = None

        # Scan all rows for the best fuzzy match for the current metric
        for i, row in df.iterrows():
            if i < text_idx:
                continue

            # Combine all non-NaN cells into one string
            row_text = " ".join(str(cell) for cell in row if pd.notna(cell)).strip()
            if not row_text:
                continue
            normalized_row_text = row_text.lower()

            # Check loose containment first
            if ut.is_loosely_contained_nltk_no_punctuation(normalized_metric, normalized_row_text):
                # Compute fuzzy score to measure how closely it matches
                normalized_row_text_without_numbers = ut.strip_trailing_numbers(normalized_row_text)
                score = ut.get_edit_distance_score(normalized_metric, normalized_row_text_without_numbers)
                if score > best_score:
                    best_score = score
                    best_value = row[column_index]

        # After checking all rows, if we have a best match, store it
        if best_score > -1:
            metric_to_val[metric] = best_value

    return metric_to_val


def get_metrics_values_from_excel(excel_path):
    sheet_name = "Summary"
    quarter, year = ut.find_quarter_year_from_filename(excel_path)
    if not quarter or not year:
        print("Didn't find quarter and year")
        return {}
    summary_df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
    header_row, column_index = find_column_index_for_quarter_year(summary_df, quarter, year)
    if not header_row or not column_index:
        print("Didn't find header row and column index of the table")
        return {}
    metric_to_val = get_metrics_from_df(summary_df, header_row + 1, column_index)
    return metric_to_val
