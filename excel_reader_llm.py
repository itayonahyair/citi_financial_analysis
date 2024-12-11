import os
import json
import pandas as pd
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter
import llm


def chunk_lines(lines, chunk_size=10, overlap=5):
    """
    Yield chunks of lines with the given chunk size and overlap.
    """
    start = 0
    while start < len(lines):
        end = start + chunk_size
        yield start, lines[start:end]
        if end >= len(lines):
            break
        start += (chunk_size - overlap)


def find_header_rows(df):
    """
    Use the LLM to identify header rows. Returns a list of row indices or -1 if not found.
    """
    lines = []
    for idx, row in df.iterrows():
        line = "\t".join([str(item) if pd.notnull(item) else "" for item in row])
        line_with_idx = f"{idx}\t{line}"
        lines.append(line_with_idx)

    # We'll ask the LLM chunk by chunk if it contains header rows
    for start_idx, chunk in chunk_lines(lines, chunk_size=10, overlap=5):
        cleaned_lines = []
        for l in chunk:
            l = l.strip()
            if l:
                cleaned_lines.append(l)

        if not cleaned_lines:
            continue

        chunk_text = "\n".join(cleaned_lines)
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": (
                "The following content comes from a summary of a financial report. "
                "The CSV-like rows represent lines extracted from an Excel sheet without known headers. "
                "The table usually has a header row or multiple header rows containing column names or descriptive labels. "
                "Header rows generally are textual and appear before numeric data.\n\n"
                f"Given these CSV lines (index + tab-separated values):\n\n"
                f"{chunk_text}\n\n"
                "Do these lines contain any header row(s) for the table? If yes, identify them by their original DataFrame row indices (the first number in each line). "
                "If you find multiple header lines (like a multi-level header), return all of them in order. If no header lines are found in this chunk, return -1.\n\n"
                'Return your answer as a JSON object, for example: {"header_idx": [list_of_row_indices]} or {"header_idx": -1}.'
            )}
        ]

        response = llm.generation(messages)
        response = response.strip()

        # Attempt to parse the LLM response as JSON
        try:
            parsed = json.loads(response)
            if "header_idx" in parsed:
                if parsed["header_idx"] != -1:
                    header_lines_indices = parsed["header_idx"]
                    if isinstance(header_lines_indices, int):
                        header_lines_indices = [header_lines_indices]
                    return header_lines_indices
        except json.JSONDecodeError:
            pass

    return -1


def set_headers_in_df(df, header_lines_indices):
    """
    Given the DataFrame and the indices of the header lines, set the headers.
    Supports multiple header rows (multi-level).
    """
    if header_lines_indices == -1:
        print("No header rows identified by the LLM.")
        return df

    header_rows = df.iloc[header_lines_indices]
    df = df.drop(header_lines_indices)

    if len(header_lines_indices) > 1:
        headers_list = []
        for _, row in header_rows.iterrows():
            headers_list.append([str(item).strip() if pd.notnull(item) else "" for item in row])
        headers_transposed = list(zip(*headers_list))
        df.columns = pd.MultiIndex.from_tuples(headers_transposed)
    else:
        single_header = header_rows.iloc[0].tolist()
        single_header = [str(h).strip() for h in single_header]
        df.columns = single_header

    df = df.reset_index(drop=True)
    return df


def ask_llm_for_year_quarter_column(df, year, quarter):
    """
    Ask the LLM to identify which column corresponds to the given year and quarter.
    We provide the LLM with a list of columns and the target year/quarter,
    and ask it to return the column index as JSON.
    """
    # Convert column headers to a readable format
    columns_descriptions = []
    columns = list(df.columns)
    for i, col in enumerate(columns):
        if isinstance(col, tuple):
            col_name = " | ".join([str(c) for c in col if c])
        else:
            col_name = str(col)
        columns_descriptions.append(f"Index {i}: {col_name}")

    columns_text = "\n".join(columns_descriptions)

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": (
            "We have a DataFrame with the following columns:\n\n"
            f"{columns_text}\n\n"
            f"We are looking for the column that represents the data for year '{year}' and quarter '{quarter}'. "
            "The column headers may not exactly match the pattern. Identify which column best corresponds.\n\n"
            "Respond with only a valid JSON object like {\"column_index\": 13} and nothing else."
        )}
    ]

    response = llm.generation(messages)
    response = response.strip()
    try:
        parsed = json.loads(response)
        return parsed.get("column_index", -1)
    except json.JSONDecodeError:
        return -1


def extract_json_from_response(response_str):
    """
    Extract a JSON object from the LLM response.
    We'll use a regex to find the first JSON object in the response.
    """
    response_str = response_str.strip()
    json_match = re.search(r'\{.*?\}', response_str, flags=re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            parsed = json.loads(json_str)
            return parsed
        except json.JSONDecodeError:
            pass
    return {}


def chunk_iterable(iterable, chunk_size=5):
    """Yield successive chunk_size-sized chunks from the iterable."""
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i:i + chunk_size]


def find_metric_rows_in_chunks(df, metrics):
    """
    Use the LLM to find the rows corresponding to the given metrics.
    Instead of sending all rows at once, send them in chunks of 5 rows each.
    """
    metric_rows = {m: -1 for m in metrics}

    lines = []
    for idx, row in df.iterrows():
        line = "\t".join([str(item) if pd.notnull(item) else "" for item in row])
        lines.append((idx, line))

    for chunk in chunk_iterable(lines, 5):
        remaining_metrics = [m for m in metrics if metric_rows[m] == -1]
        if not remaining_metrics:
            break

        chunk_lines_text = "\n".join([f"{i}\t{l}" for i, l in chunk])
        metrics_list = "\n".join(remaining_metrics)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": (
                    "Below are up to 5 rows of a financial summary table (after headers). Each line starts with the row index, "
                    "followed by the row's values. We have these metrics we are looking for:\n\n"
                    f"{metrics_list}\n\n"
                    "Rows:\n" + chunk_lines_text + "\n\n"
                                                   "For each metric, determine if any of these rows describe or represent that metric. "
                                                   "If you find a match, return the row index. If no match in these rows, return -1 for that metric.\n\n"
                                                   "Respond with ONLY a JSON object mapping each metric to the row index or -1."
            )}
        ]

        response = llm.generation(messages)
        parsed = extract_json_from_response(response)

        for m in remaining_metrics:
            if m in parsed and isinstance(parsed[m], int):
                if parsed[m] != -1:
                    metric_rows[m] = parsed[m]

    return metric_rows


def get_metrics_values_from_excel(excel_file):
    if not os.path.exists(excel_file):
        print(f"Error: File '{excel_file}' does not exist.")
        return {}

    df = pd.read_excel(excel_file, sheet_name="Summary", header=None, dtype=str)
    year, quarter = llm.extract_year_quarter_from_filename(excel_file)
    if year and quarter:
        print(f"Extracted from filename - Year: {year}, Quarter: Q{quarter}")
    else:
        print("LLM failed to extract year and quarter from filename. Proceeding to extract from 'Index' sheet text.")

        # Read the "Index" sheet from the Excel file
        df_index = pd.read_excel(excel_file, sheet_name="Index", header=None, dtype=str)

        # Convert the DataFrame to a single text string
        # We join each cell in a row with a space, and then join all rows.
        # Then we strip out extra spaces and newlines.
        lines = []
        for _, row in df_index.iterrows():
            # Convert non-null cells to string and join them with a space
            row_text = " ".join([str(cell) for cell in row if pd.notnull(cell)])
            if row_text.strip():
                lines.append(row_text.strip())

        # Combine all lines into one text and remove excessive whitespace
        full_text = " ".join(lines)
        # Normalize whitespace: split on whitespace and rejoin with a single space
        full_text = " ".join(full_text.split())

        # Step 3: Split text into chunks using LangChain's RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=256,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_text(full_text)
        print(f"Text split into {len(chunks)} chunks.")

        # Step 4: Iterate through chunks to extract year and quarter from the text
        year, quarter = llm.extract_year_quarter_from_text(chunks)

        if year and quarter:
            print(f"Extracted from 'Index' sheet text - Year: {year}, Quarter: Q{quarter}")
        else:
            print("Failed to extract year and quarter from 'Index' sheet text.")
            return {}

    # Step 1: Identify header rows
    header_indices = find_header_rows(df)
    df = set_headers_in_df(df, header_indices)
    if df is None or header_indices == -1:
        print("Cannot proceed without identified headers.")
        return {}

    print("Headers have been set.")
    # Step 2: Identify column for given year and quarter
    col_index = ask_llm_for_year_quarter_column(df, year, quarter)
    if col_index != -1 and col_index < len(df.columns):
        print(f"Column representing {quarter} {year} is at index: {col_index}")
        print("Column name:", df.columns[col_index])
    else:
        print(f"Could not find a column for {quarter} {year}.")
        return {}

    # Step 3: Metrics to search for
    metrics = [
        "CET1 Capital Ratio",
        "Tangible book value per share",
        "Book value per share",
        "Net income",
        "Revenues"
    ]

    # Step 4: Find each metric row in chunks of 5 rows
    metric_rows_map = find_metric_rows_in_chunks(df, metrics)
    print("Metric rows identified by LLM in chunks:", metric_rows_map)

    # Step 5: Extract values at the found rows and the identified column
    results = {}
    for metric in metrics:
        row_idx = metric_rows_map[metric]
        if row_idx == -1 or row_idx not in df.index:
            results[metric] = None
        else:
            value = df.iat[row_idx, col_index]
            results[metric] = value

    print("Extracted metric values for the given column:")
    for metric, val in results.items():
        print(f"{metric}: {val}")
    return results
