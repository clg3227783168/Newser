
import pandas as pd

def split_text_by_paragraphs(text):
    """Splits text by double newlines, representing paragraphs."""
    # Also remove any empty strings that might result from splitting
    return [paragraph.strip() for paragraph in text.split('\n\n') if paragraph.strip()]

def main():
    """
    Reads the processed data, splits the content of each document into paragraphs,
    and saves the results to a new CSV file.
    """
    try:
        df = pd.read_csv('processed_data.csv')
    except FileNotFoundError:
        print("Error: processed_data.csv not found. Please run preprocess.py first.")
        return

    split_data = []
    for _, row in df.iterrows():
        file_name = row['file_name']
        content = row['content']
        chunks = split_text_by_paragraphs(content)
        for i, chunk in enumerate(chunks):
            split_data.append({
                'original_file': file_name,
                'chunk_id': i,
                'chunk_content': chunk
            })

    split_df = pd.DataFrame(split_data)
    split_df.to_csv('split_data.csv', index=False)
    print(f"Successfully split the data into {len(split_df)} chunks and saved to split_data.csv")

if __name__ == '__main__':
    main()
