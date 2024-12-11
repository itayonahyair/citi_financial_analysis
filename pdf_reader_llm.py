import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
import llm
import utils as ut


def extract_metrics_from_text(full_text):
    # Split text into chunks for embedding
    print("Splitting text into chunks for embedding...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=256,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )
    embedding_chunks = text_splitter.split_text(full_text)
    print(f"Text split into {len(embedding_chunks)} chunks for embedding.")

    # Encode the chunks into vectors using e5-small
    print("Encoding chunks into vectors using Huggingface Embeddings (e5-large)...")
    try:
        embeddings = HuggingFaceEmbeddings(model_name="intfloat/e5-small")
    except Exception as e:
        print(f"Error initializing embeddings: {e}")
        return {}

    try:
        vector_store = FAISS.from_texts(embedding_chunks, embeddings)
        print("Chunks encoded and stored in vector database.")
    except Exception as e:
        print(f"Error creating vector store: {e}")
        return {}

    # Define metrics and query the vector db
    metrics = [
        "CET1 Capital Ratio",
        "Tangible book value per share",
        "Book value per share",
        "Net income",
        "Revenues"
    ]

    results = {}

    for metric in metrics:
        print(f"\nQuerying for metric: {metric}")
        try:
            # Query the vector store for top-5 similar chunks
            metric_query = f"what is the {metric}?"
            docs = vector_store.similarity_search(metric_query, k=10)
            context = "\n".join([doc.page_content for doc in docs])
        except Exception as e:
            print(f"Error during similarity search for '{metric}': {e}")
            results[metric] = "Error retrieving data"
            continue

        # Define prompt to get the metric value
        prompt = f"The following context is from financial report. Based on the following context, provide the value " \
                 f"for '{metric}':\n\nContext:\n{context}\n\nProvide the value only."

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]

        answer = llm.generation(messages)
        results[metric] = answer if answer else "No data found"
    return results


def get_metrics_values_from_pdf(pdf_file):
    if not os.path.exists(pdf_file):
        print(f"Error: File '{pdf_file}' does not exist.")
        return {}

    # Extract text from PDF
    print("Extracting text from PDF...")
    full_text = ut.extract_text_pypdf2(pdf_file)

    if not full_text.strip():
        print("No text extracted from the PDF.")
        return {}

    # Extract year and quarter from filename via LLM
    filename = os.path.basename(pdf_file)
    year, quarter = llm.extract_year_quarter_from_filename(filename)

    if year and quarter:
        print(f"Extracted from filename - Year: {year}, Quarter: Q{quarter}")
    else:
        print("LLM failed to extract year and quarter from filename. Proceeding to extract from text.")

        # Split text into chunks using LangChain's RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=256,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_text(full_text)
        print(f"Text split into {len(chunks)} chunks.")

        # Step 4: Iterate through chunks to extract year and quarter
        year, quarter = llm.extract_year_quarter_from_text(chunks)

        if not year or not quarter:
            print("Failed to extract year and quarter from PDF text.")
            return {}

    results = extract_metrics_from_text(full_text)
    # Print the results
    print("\nExtracted Metrics:")
    for metric, value in results.items():
        print(f"{metric}: {value}")
    return results
