import sys
import pdf_reader_llm
import excel_reader_llm
import pandas as pd
import re
import pdf_reader_no_llm
import excel_reader_no_llm


def compare_values(pdf_metric_dict, excel_metric_dict, relative_tolerance=0.05):
    """
    Compare PDF and Excel metrics using relative tolerance with dynamic scaling.

    :param pdf_metric_dict: Dictionary from PDF with metric as key and {'value': float, 'unit': str} as value
    :param excel_metric_dict: Dictionary from Excel with metric as key and float as value
    :param relative_tolerance: Relative tolerance as a decimal (e.g., 0.05 for 5%)
    :return: List of comparison results
    """
    results = []
    for metric, pdf_info in pdf_metric_dict.items():
        if metric not in excel_metric_dict:
            # Metric not found in Excel
            results.append([metric, f"{pdf_info['value']}{pdf_info['unit']}", None, "No Match"])
            continue

        pdf_value = pdf_info['value']
        pdf_unit = pdf_info['unit']
        excel_value = excel_metric_dict[metric]

        match_status = "No Match"  # Default status

        # Define a helper function for comparison
        def is_within_tolerance(a, b, tol):
            if b == 0:
                return a == 0
            ratio = a / b
            return 1 - tol <= ratio <= 1 + tol

        # Initial comparison without scaling
        if pdf_unit == '%':
            # Convert percentages to fractions
            pdf_adj = pdf_value / 100.0
            excel_adj = excel_value / 100.0 if excel_value > 1 else excel_value
            if is_within_tolerance(pdf_adj, excel_adj, relative_tolerance):
                match_status = "Match"
        else:
            # For monetary units or others
            if is_within_tolerance(pdf_value, excel_value, relative_tolerance):
                match_status = "Match"

        # If not matched, attempt scaling Excel value by 1000
        if match_status == "No Match" and pdf_unit != '%':
            scaled_excel = excel_value * 1000.0
            if is_within_tolerance(pdf_value, scaled_excel, relative_tolerance):
                match_status = "Match"

        # If still not matched, attempt scaling Excel value by 0.001
        if match_status == "No Match" and pdf_unit != '%':
            scaled_excel = excel_value / 1000.0
            if is_within_tolerance(pdf_value, scaled_excel, relative_tolerance):
                match_status = "Match"
        # Format displayed values with original units
        pdf_display = f"{pdf_info['value']}{pdf_unit}" if pdf_unit else f"{pdf_info['value']}"
        excel_display = f"{excel_value}"  # Excel has no unit

        results.append([metric, pdf_display, excel_display, match_status])

    # Check for metrics present in Excel but not in PDF
    for metric in excel_metric_dict:
        if metric not in pdf_metric_dict:
            # Metric not found in PDF
            results.append([metric, None, excel_metric_dict[metric], "No Match"])

    return results


def parse_pdf_metric(value_str):
    """
    Parses the PDF metric string to extract numeric value and unit.

    :param value_str: String representing the metric value from PDF (e.g., '13.6%', '$87.53', '3.2 billion')
    :return: Tuple (float_value, unit)
    """
    value_str = value_str.strip().lower()

    # Regex patterns for different units
    patterns = [
        (r'^(\d+\.?\d*)\s*%$', '%'),  # Percentage e.g., '13.6%'
        (r'^\$(\d+\.?\d*)$', '$'),  # Dollar e.g., '$87.53'
        (r'^(\d+\.?\d*)\s*(billion|million)$', lambda x: 'B' if x == 'billion' else 'M'),  # Billion/Million
        (r'^(\d+\.?\d*)$', '')  # No unit e.g., '99.70'
    ]

    for pattern, unit in patterns:
        match = re.match(pattern, value_str)
        if match:
            if callable(unit):
                numeric_value = float(match.group(1))
                extracted_unit = unit(match.group(2))
                return numeric_value, extracted_unit
            else:
                numeric_value = float(match.group(1))
                return numeric_value, unit
    # If no pattern matches
    return None, None


def parse_excel_metric(value_str):
    """
    Parses the Excel metric string to convert it into a float.

    :param value_str: String representing the metric value from Excel (e.g., '0.136', '3217')
    :return: Float value or None if parsing fails
    """
    try:
        return float(value_str.replace(',', '').strip())
    except ValueError:
        return None


def prepare_parsed_data(pdf_data, excel_data):
    """
    Prepares parsed data dictionaries from raw PDF and Excel data.

    :param pdf_data: Dictionary from PDF with metric names as keys and value strings as values
    :param excel_data: Dictionary from Excel with metric names as keys and value strings as values
    :return: Tuple of two dictionaries:
             - parsed_pdf: {metric: {'value': float, 'unit': str}}
             - parsed_excel: {metric: float}
    """
    parsed_pdf = {}
    for metric, value_str in pdf_data.items():
        numeric_value, unit = parse_pdf_metric(value_str)
        if numeric_value is not None:
            parsed_pdf[metric] = {'value': numeric_value, 'unit': unit}
        else:
            print(f"Warning: Could not parse PDF metric '{metric}' with value '{value_str}'")

    parsed_excel = {}
    for metric, value_str in excel_data.items():
        numeric_value = parse_excel_metric(value_str)
        if numeric_value is not None:
            parsed_excel[metric] = numeric_value
        else:
            print(f"Warning: Could not parse Excel metric '{metric}' with value '{value_str}'")

    return parsed_pdf, parsed_excel


def main():
    if len(sys.argv) != 4:
        if len(sys.argv) != 3:
            print("Usage: python compare_metrics.py <pdf_file> <excel_file>")
            sys.exit(1)
        approach = "no llm"
    else:
        approach = sys.argv[3]
    pdf_file = sys.argv[1]
    excel_file = sys.argv[2]
    if approach.lower() == "llm":
        pdf_metric_dict = pdf_reader_llm.get_metrics_values_from_pdf(pdf_file)
        excel_metric_dict = excel_reader_llm.get_metrics_values_from_excel(excel_file)
        pdf_metric_dict, excel_metric_dict = prepare_parsed_data(pdf_metric_dict, excel_metric_dict)
    else:
        pdf_metrics = pdf_reader_no_llm.get_metrics_values_from_pdf(pdf_file)
        pdf_metric_dict = {m['metric']: {"value": m['value'], "unit": m['unit']} for m in pdf_metrics}
        excel_metric_dict = excel_reader_no_llm.get_metrics_values_from_excel(excel_file)

    results = compare_values(pdf_metric_dict, excel_metric_dict)

    # Create a DataFrame for display
    df = pd.DataFrame(results, columns=["Metric", "PDF", "Excel", "Match"])
    print(df)


if __name__ == "__main__":
    main()
