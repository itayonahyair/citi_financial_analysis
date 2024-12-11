from rapidfuzz.distance import Levenshtein
import re
import PyPDF2
from nltk.tokenize import word_tokenize


def is_loosely_contained_nltk_no_punctuation(substr, text):
    # Placeholder for your existing function
    text_nopunct = re.sub(r'[^\w\s]', '', text)
    substr_nopunct = re.sub(r'[^\w\s]', '', substr)
    return substr_nopunct in text_nopunct


def get_edit_distance_score(str1, str2):
    dist = Levenshtein.distance(str1, str2)
    max_len = max(len(str1), len(str2))
    if max_len == 0:
        return 100.0 if dist == 0 else 0.0
    return 100.0 * (1 - (dist / max_len))


def strip_trailing_numbers(text):
    # Split by whitespace
    parts = text.split()

    # Define a function to check if a token is numeric
    # We'll try converting to float. If it fails, it's not numeric.
    def is_numeric_token(token):
        try:
            float(token)
            return True
        except ValueError:
            return False

    # Iterate from the end and remove tokens as long as they are numeric
    while parts and is_numeric_token(parts[-1]):
        parts.pop()

    # Join back the remaining parts
    return " ".join(parts)


def find_quarter_year_from_filename(filename: str):
    """
    Extracts the quarter and year from a filename using multiple regex patterns.

    :param filename: The filename string to extract quarter and year from.
    :return: Tuple containing the extracted quarter (e.g., 'Q3') and year (e.g., '2024'). Returns (None, None) if not found.
    """
    # Define multiple regex patterns to cover various filename formats
    patterns = [
        # Pattern 1: Year first, then anything, then 'qtr' or 'q', then quarter number (e.g., "2024pr-qtr3rslt")
        r'(?P<year>\d{4}).*?[qQ][tT]?[rR]?[-_]?(?P<q>[1-4])',

        # Pattern 2: 'FY' followed by year and quarter (e.g., "FY2024Q3")
        r'[fF][yY].*?(?P<year>\d{4}).*?[qQ][tT]?[rR]?[-_]?(?P<q>[1-4])',

        # Pattern 3: Quarter first, then anything, then year (e.g., "q3-2024")
        r'[qQ][tT]?[rR]?[-_]?(?P<q>[1-4]).*?(?P<year>\d{4})',

        # Pattern 4: 'Quarter' word followed by number and year (e.g., "Quarter 3 2024")
        r'(?:quarter|qtr|q)\s*(?P<q>[1-4]).*?(?P<year>\d{4})',

        # Pattern 5: Year first, then 'Q' and quarter number (e.g., "2024Q3")
        r'(?P<year>\d{4}).*?[qQ].*?(?P<q>[1-4])',

        # Pattern 6: 'Q' followed by quarter number and year (e.g., "Q3-2024")
        r'[qQ].*?(?P<q>[1-4]).*?(?P<year>\d{4})',

        # Pattern 7: Quarter number followed by 'QTR' and two-digit year (e.g., "3QTR24")
        r'(?P<q>[1-4])[qQ][tT][rR].*?(?P<year2>\d{2})',

        # Pattern 8: Year followed by 'QTR' and quarter number (e.g., "2024QTR3")
        r'(?P<year>\d{4})[qQ][tT][rR].*?(?P<q>[1-4])',

        # Pattern 9 (new): Quarter number followed by 'Q' and two-digit year (e.g., "3Q24")
        r'(?P<q>[1-4])[qQ](?P<year2>\d{2})',
    ]

    for idx, pattern in enumerate(patterns, 1):
        regex = re.compile(pattern, re.IGNORECASE)
        match = regex.search(filename)
        if match:
            quarter_num = match.group('q')
            quarter = f"Q{quarter_num}"

            # Handle 2-digit and 4-digit years
            if 'year2' in match.groupdict() and match.group('year2'):
                year = match.group('year2')
                # Assume 21st century for 2-digit years (modify if needed)
                year = f"20{year}"
            elif 'year' in match.groupdict() and match.group('year'):
                year = match.group('year')
            else:
                year = None

            # Validate quarter
            if quarter_num not in ['1', '2', '3', '4']:
                print(f"Pattern {idx} matched but with invalid quarter number: {quarter_num}")
                continue  # Invalid quarter, skip

            print(f"Pattern {idx} matched. Extracted Quarter: {quarter}, Year: {year}")
            return quarter, year

    # If no patterns matched, return None
    print("No patterns matched.")
    return None, None


def extract_text_pypdf2(pdf_path):
    """
    Extracts text from a PDF file using PyPDF2.

    :param pdf_path: Path to the PDF file.
    :return: Extracted text as a single string.
    """
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            print(f"Number of pages: {num_pages}")
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    print(f"Warning: No text found on page {page_num + 1}")
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text
