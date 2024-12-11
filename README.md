# Metrics Extraction and Comparison Tool

## Overview
This project provides a tool to extract and compare key financial metrics from a PDF and an Excel file. The tool supports two modes of operation: with or without leveraging an LLM (Large Language Model). The results are presented in a structured comparison table for the specified metrics and quarters.

## Installation and Setup

### Prerequisites
- Python 3.8+
- Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running the Tool

The main entry point for the tool is the `main.py` file. Run the tool using the following command:

```bash
python main.py <pdf_file_path> <excel_file_path> [--llm]
```

#### Arguments:
- `<pdf_file_path>`: Path to the PDF file containing the metrics.
- `<excel_file_path>`: Path to the Excel file containing the metrics.
- `--llm` (optional): Enables the LLM-assisted mode for extracting metrics.

#### Example:
```bash
python main.py ./data/sample.pdf ./data/sample.xlsx --llm
```

If the `--llm` flag is not provided, the tool will default to the no-LLM approach for extracting and comparing metrics.

### Additional Setup
- **OpenRouter API Key**: Obtain an API key from the [OpenRouter website](https://openrouter.ai/) and add it to the `.env` file under the key `Open_Router_API_KEY`.

## Extracted Metrics
The following metrics are extracted and compared between the PDF and Excel files:

- **CET1 Capital Ratio**
- **Tangible Book Value Per Share**
- **Book Value Per Share**
- **Net Income**
- **Revenues**

## Results
The tool compares values for these metrics for both Q2 and Q3. The results are presented in two separate tables:

### Table Structure
Each table contains the following columns:

1. **Metric Name**: The name of the metric being compared.
2. **PDF QX**: The value of the metric for a specific quarter extracted from the PDF, including its unit.
3. **Excel QX**: The value of the metric for a specific quarter extracted from the Excel file.
4. **Match (QX)**: Indicates whether the values from the PDF and Excel match within a defined tolerance.

### Example Table

| Metric                        | PDF     | Excel | Match             |
|-------------------------------|---------|-------|-------------------|
| CET1 Capital Ratio            | ...     | ...   | Match / Not Match |
| Tangible Book Value Per Share | ...     | ...   | Match / Not Match |
| Book Value Per Share          | ...     | ...   | Match / Not Match |
| Net Income                    | ...     | ...   | Match / Not Match |
| Revenues                      | ...     | ...   | Match / Not Match |

### Quarter 2 Results

#### Without LLM:
| Metric                         | PDF      | Excel   | Match |
|--------------------------------|----------|---------|-------|
| CET1 Capital Ratio             | 13.6%    | 0.136   | Match |
| Tangible book value per share  | 87.53$   | 87.53   | Match |
| Book value per share           | 99.7$    | 99.7    | Match |
| Net income                     | 3.2B     | 3217    | Match |
| Revenues                       | 20.1B    | 20139   | Match |

#### With LLM:
| Metric                         | PDF      | Excel   | Match |
|--------------------------------|----------|---------|-------|
| CET1 Capital Ratio             | 13.6%    | 0.136   | Match |
| Tangible book value per share  | 87.53    | 87.53   | Match |
| Book value per share           | 99.7     | 99.7    | Match |
| Net income                     | 3.2B     | 3217.0  | Match |
| Revenues                       | 20.1B    | 20139.0 | Match |

### Quarter 3 Results

#### Without LLM:
| Metric                         | PDF      | Excel   | Match |
|--------------------------------|----------|---------|-------|
| CET1 Capital Ratio             | 13.7%    | 0.137   | Match |
| Tangible book value per share  | 89.67$   | 89.67   | Match |
| Book value per share           | 101.91$  | 101.91  | Match |
| Net income                     | 3.2B     | 3238    | Match |
| Revenues                       | 20.3B    | 20315   | Match |

#### With LLM:
| Metric                         | PDF      | Excel   | Match |
|--------------------------------|----------|---------|-------|
| CET1 Capital Ratio             | 13.7%    | 0.137   | Match |
| Tangible book value per share  | 89.67    | 89.67   | Match |
| Book value per share           | 101.91   | 101.91  | Match |
| Net income                     | 3.2B     | 3238.0  | Match |
| Revenues                       | 20.3B    | 20315.0 | Match |


## Summary of the Approach

### LLM-Based Approach

#### Excel Extraction
1. **Header Detection**: The tool scans the "Summary" sheet of the Excel file to locate the index of the header row.
2. **Column Index Identification**: It identifies the column index corresponding to the specified year and quarter.
3. **Metric Row Identification**: It scans rows below the header to locate the indices for each metric.
4. **Value Extraction**: Values are extracted using the identified row and column indices.

#### PDF Extraction
1. **Chunking and Embedding**: The PDF is split into chunks and embedded using the `e5-small` model. The chunks are stored in a vector database.
2. **Metric Querying**: For each metric, the tool embeds a query such as `"What is the {metric}?"`.
3. **Candidate Selection**: The top-k candidates are retrieved from the vector database, and the LLM is used to extract the value.

### No-LLM Approach

#### Excel Extraction
1. **Header and Column Detection**: The tool uses regex patterns (e.g., `\dQ|Q\d`) to locate the header row and year/quarter columns.
2. **Metric Row Matching**: It searches for rows matching the metric name and selects the best match based on minimum edit distance.
3. **Value Extraction**: Values are extracted using the identified indices.

#### PDF Extraction
1. **Pattern-Based Extraction**: Regex patterns are defined for each metric.
2. **Sentence Splitting**: The PDF text is split into sentences using SpaCy.
3. **Field Extraction**: The tool extracts fields such as `metric`, `value`, `unit`, and `quarter` using regex.
4. **Filtering and Normalization**: Values are filtered to retain only those matching the specified quarter.
5. **Frequency Analysis**: The most frequently occurring value for each metric is selected.

### Final Comparison
1. **Scaling and Normalization**: The tool handles discrepancies in representation (e.g., billions vs. millions, percentages vs. decimals).
2. **Tolerance**: A 5% tolerance is applied to account for minor rounding differences.

## Observations and Challenges
1. **Excel Table Alignment**: The Excel table's header and data are not aligned with the first row and column, requiring advanced logic to identify headers and data.
2. **Metric Row Identification**: For the no-LLM approach, identifying metric rows required careful consideration of substring matches and edit distances.
3. **Unit Differences**: Reconciling values in different units (e.g., billions vs. millions, percentages vs. decimals) required additional scaling logic.
