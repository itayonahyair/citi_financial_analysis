import spacy
import re
import pandas as pd
import os
import utils as ut


def standardize_quarter(quarter_str):
    """
    Converts various quarter representations to a standardized 'Q1' to 'Q4' format.
    """
    if not quarter_str:
        return None

    quarter_str = quarter_str.lower()
    if 'q1' in quarter_str or '1' in quarter_str:
        return 'Q1'
    elif 'q2' in quarter_str or '2' in quarter_str:
        return 'Q2'
    elif 'q3' in quarter_str or '3' in quarter_str:
        return 'Q3'
    elif 'q4' in quarter_str or '4' in quarter_str:
        return 'Q4'
    else:
        return None


def split_into_sentences(text, nlp):
    """
    Splits text into sentences using spaCy.
    """
    doc = nlp(text)
    sentences = [sent.text.strip().lower() for sent in doc.sents]
    return sentences


def remove_newlines_regex(sentences):
    """
    Removes newline characters and excessive whitespace from each sentence.
    """
    cleaned_sentences = [re.sub(r'\s+', ' ', sentence).strip() for sentence in sentences]
    return cleaned_sentences


def define_metrics_patterns():
    """
    Defines the metrics and their corresponding regex patterns for value extraction.

    :return: Dictionary mapping metrics to their regex patterns and value types.
    """
    metrics_info = {
        "CET1 Capital Ratio": {
            "pattern": r'\bcet1 capital ratio\b\s*(?:of\s*)?[:\-]?\s*(\d+\.?\d*%)',
            "value_type": "percentage"
        },
        "Tangible book value per share": {
            "pattern": r'\btangible book value per share\b\s*(?:of\s*)?[:\-]?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
            "value_type": "dollar"
        },
        "Book value per share": {
            "pattern": r'(?<!tangible )\bbook value per share\b\s*(?:of\s*)?[:\-]?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
            "value_type": "dollar"
        },
        "Net income": {
            "pattern": r'\bnet income\b\s*(?:of\s*)?[:\-]?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?[MmBb]?)',
            "value_type": "millions_billions"
        },
        "Revenues": {
            "pattern": r'\brevenues\b\s*(?:of\s*)?[:\-]?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?[MmBb]?)',
            "value_type": "millions_billions"
        }
    }
    return metrics_info


def compile_regex_patterns(metrics_info):
    """
    Compiles the regex patterns for metrics and quarters.
    """
    compiled_metrics = {}
    for metric, info in metrics_info.items():
        compiled_metrics[metric] = re.compile(info["pattern"], re.IGNORECASE)

    # Quarter patterns: Q1, Q2, Q3, Q4, 1Q, 2Q, etc., 1st quarter, 2nd quarter, etc.
    quarter_pattern = r'(Q[1-4]|[1-4]Q|(?:1st|2nd|3rd|4th) quarter)\s*(?:\'?\d{2,4})?'
    compiled_quarter = re.compile(quarter_pattern, re.IGNORECASE)

    return compiled_metrics, compiled_quarter


def normalize_value(value, value_type):
    """
    Normalizes the extracted financial value based on its type.

    :param value: The extracted value as a string (e.g., '$3.2B', '$1.51', '12.5%').
    :param value_type: The type of value ('percentage', 'dollar', 'millions_billions').
    :return: Tuple of normalized numerical value and its unit (if any).
    """
    if value is None:
        return None, None

    if value_type == "percentage":
        try:
            numeric_value = float(value.replace('%', ''))
            return numeric_value, '%'
        except ValueError:
            return None, '%'

    elif value_type == "dollar":
        try:
            numeric_value = float(value.replace('$', '').replace(',', ''))
            return numeric_value, '$'
        except ValueError:
            return None, '$'

    elif value_type == "millions_billions":
        unit = None
        multiplier = 1
        if value.endswith(('M', 'm')):
            multiplier = 1e-3  # Millions to Billions
            unit = 'M'
            value = value[:-1]
        elif value.endswith(('B', 'b')):
            multiplier = 1  # Billions
            unit = 'B'
            value = value[:-1]
        try:
            numeric_value = float(value.replace('$', '').replace(',', '')) * multiplier
            return numeric_value, unit
        except ValueError:
            return None, unit

    else:
        return value, None  # If value_type is unrecognized


def extract_metrics(sentences, metrics_info, compiled_metrics, compiled_quarter):
    """
    Extracts specified metrics, their values, and associated quarters from sentences.

    :param sentences: List of sentences extracted from the PDF.
    :param metrics_info: Dictionary mapping metrics to their regex patterns and value types.
    :param compiled_metrics: Dictionary of compiled regex patterns for metrics.
    :param compiled_quarter: Compiled regex pattern for quarters.
    :return: List of dictionaries with extracted data.
    """
    extracted_data = []

    for sentence in sentences:
        # Iterate through each metric
        for metric, info in metrics_info.items():
            pattern = compiled_metrics[metric]
            match = pattern.search(sentence)
            if match:
                raw_value = match.group(1)
                normalized_value, unit = normalize_value(raw_value, info["value_type"])

                # Only proceed if a valid value is extracted
                if normalized_value is None:
                    continue  # Skip metrics without valid values

                # Find quarter in the sentence
                quarter_match = compiled_quarter.search(sentence)
                quarter = quarter_match.group(1) if quarter_match else None

                # Standardize quarter
                standardized_quarter = standardize_quarter(quarter)

                # Only include valid quarters or allow quarter to be None
                if standardized_quarter is None and quarter is not None:
                    # Skip invalid quarter representations but allow quarter=None
                    continue  # Skip invalid quarter representations

                # Append the extracted information
                extracted_data.append({
                    'metric': metric,
                    'value': normalized_value,
                    'unit': unit,
                    'quarter': standardized_quarter,  # Can be None
                    'sentence': sentence
                })

    return extracted_data


def get_metrics_values_from_pdf(pdf_file):
    if not os.path.exists(pdf_file):
        print(f"Error: File '{pdf_file}' does not exist.")
        return {}
    # Step 1: Extract quarter from filename
    base_filename = os.path.splitext(os.path.basename(pdf_file))[0]
    quarter, year = ut.find_quarter_year_from_filename(base_filename)
    if not quarter or not year:
        print("Didn't find quarter and year")
        return {}
    print(f"\nExtracted Quarter from Filename: {quarter}, Year: {year}")
    # Step 2: Extract text from PDF
    print("Extracting text from PDF...")
    full_text = ut.extract_text_pypdf2(pdf_file)

    if not full_text.strip():
        print("No text extracted from the PDF.")
        return {}

    # Step 3: Load spaCy model
    print("Loading spaCy model...")
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("Model 'en_core_web_sm' not found. Installing now...")
        os.system("python -m spacy download en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")

    # Step 4: Split text into sentences
    print("Splitting text into sentences...")
    sentences = split_into_sentences(full_text, nlp)
    sentences = remove_newlines_regex(sentences)
    print(f"Total sentences extracted: {len(sentences)}")

    # Step 5: Define metrics and patterns
    metrics_info = define_metrics_patterns()

    # Step 5: Compile regex patterns
    compiled_metrics, compiled_quarter = compile_regex_patterns(metrics_info)

    # Step 6: Extract metrics
    print("Extracting metrics, values, and quarters...")
    extracted_data = extract_metrics(sentences, metrics_info, compiled_metrics, compiled_quarter)

    if not extracted_data:
        print("No metrics found in the extracted sentences.")
        return {}
    df = pd.DataFrame(extracted_data)

    # Step 7: Filter DataFrame based on extracted quarter
    print(f"Filtering metrics to keep only quarter '{quarter}' or None.")
    # Keep rows where quarter matches extracted quarter OR quarter is None
    df_filtered = df[(df['quarter'] == quarter) | (df['quarter'].isnull())]

    # Step 8: Determine the most frequent value per metric, ignoring quarter
    print("\nDetermining the most frequent value per metric...")

    # Group by metric, value, and unit only (exclude 'quarter') to prioritize value frequency
    df_grouped = df_filtered.groupby(['metric', 'value', 'unit']).size().reset_index(name='counts')

    # Sort each metric by counts descending to identify the most frequent value
    df_grouped_sorted = df_grouped.sort_values(['metric', 'counts'], ascending=[True, False])

    # For each metric, select the row with the highest count (most frequent value)
    final_selection = df_grouped_sorted.groupby('metric').first().reset_index()

    # Now, to get the 'quarter' associated with each (metric, value, unit), merge back with the original df_filtered
    final_selection = pd.merge(final_selection, df_filtered[['metric', 'value', 'unit', 'quarter']],
                               on=['metric', 'value', 'unit'], how='left')

    # For each metric, find the most frequent quarter associated with the selected value
    final_selection['quarter'] = final_selection.groupby('metric')['quarter'].transform(
        lambda x: x.mode().iloc[0] if not x.mode().empty else None
    )

    # Drop duplicates to ensure only one row per metric
    final_selection = final_selection.drop_duplicates(subset=['metric'])

    # Step 11: Assign priority to metrics based on a predefined list
    # Define priority based on the order in the metrics list
    metrics_priority = [
        "CET1 Capital Ratio",
        "Tangible book value per share",
        "Book value per share",
        "Net income",
        "Revenues"
    ]

    # Create a DataFrame for priority
    priority_df = pd.DataFrame({
        'metric': metrics_priority,
        'priority': range(1, len(metrics_priority) + 1)
    })

    # Merge the final_selection with priority_df to assign global priority
    final_df = pd.merge(priority_df, final_selection, on='metric', how='left')

    # Sort the final DataFrame based on priority
    final_df = final_df.sort_values('priority')

    # Select relevant columns, including 'quarter' to indicate the quarter of the selected value
    final_df = final_df[['metric', 'value', 'unit']]
    final_df['value'] = final_df['value'].astype(float)
    final_df['unit'] = final_df['unit'].astype(str)
    metrics_list = final_df.to_dict('records')
    return metrics_list
