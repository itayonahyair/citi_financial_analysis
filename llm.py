from openai import OpenAI
from dotenv import load_dotenv
import os
import re

load_dotenv()

OpenRouter_API_Base_URL = os.getenv('OpenRouter_API_Base_URL')
Open_Router_API_KEY = os.getenv('Open_Router_API_KEY')
llm = OpenAI(base_url=OpenRouter_API_Base_URL, api_key=Open_Router_API_KEY)


def generation(messages, max_tokens=4000):
    try:
        response = llm.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.0,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error during LLM call: {e}")
        return ""


def extract_year_quarter_from_filename(filename):
    """
    Extracts the year and quarter from the filename using the LLM.

    :param filename: The name of the PDF file.
    :return: A tuple of (year, quarter) if found, else (None, None).
    """
    prompt = f"Extract the year and quarter from the following filename: '{filename}'. Return them in the format 'year: XXXX, quarter: QX'. If you cannot find them, respond with 'Not found'."
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
    response = generation(messages)
    # Parse the response to extract year and quarter
    match = re.search(r'year\s*:\s*(\d{4}),\s*quarter\s*:\s*Q(\d)', response, re.IGNORECASE)
    if match:
        year = int(match.group(1))
        quarter = int(match.group(2))
        return year, quarter
    else:
        return None, None


def extract_year_quarter_from_text(chunks):
    """
    Recursively attempts to extract the year and quarter from text chunks using the LLM.

    :param chunks: List of text chunks.
    :return: A tuple of (year, quarter) if found, else (None, None).
    """
    for idx, chunk in enumerate(chunks):
        prompt = f"Based on the following text, identify the current year and quarter. Respond in the format 'year: XXXX, quarter: QX'. If not found, respond with 'Not found'.\n\nText: {chunk}"
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
        response = generation(messages)
        # Parse the response
        match = re.search(r'year\s*:\s*(\d{4}),\s*quarter\s*:\s*Q(\d)', response, re.IGNORECASE)
        if match:
            year = int(match.group(1))
            quarter = int(match.group(2))
            print(f"Extracted from text chunk {idx + 1} - Year: {year}, Quarter: {quarter}")
            return year, quarter
    return None, None
