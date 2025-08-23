
import os
import pandas as pd
import re
from markdown_it import MarkdownIt

def clean_content(text):
    """Cleans the text by removing specific patterns."""
    # Remove the specific string
    text = text.replace("[长宁房管](javascript:void(0);)", "")
    # Remove image links starting with ![cover_image]
    text = re.sub(r'!\[cover_image\]\(https?://[^\)]+\)', '', text)
    # Remove author information
    text = re.sub(r'撰稿人:\s*\S+', '', text)
    return text

def extract_text_from_md(file_path):
    """Reads a markdown file, cleans it, and returns its text content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
            # Clean the content
            cleaned_content = clean_content(md_content)
            md = MarkdownIt()
            # The parse method returns a list of tokens, but for now, we'll just use the raw text.
            return cleaned_content
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ""

def main():
    """
    Walks through the data directory, processes all markdown files,
    and saves the content to a CSV file.
    """
    data_dir = 'data'
    processed_data = []

    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                text_content = extract_text_from_md(file_path)
                if text_content:
                    processed_data.append({'file_name': file, 'content': text_content})

    df = pd.DataFrame(processed_data)
    df.to_csv('processed_data.csv', index=False)
    print(f"Successfully processed {len(df)} files and saved to processed_data.csv")

if __name__ == '__main__':
    main()
