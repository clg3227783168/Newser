import os
import re

# For performance, pre-compile regexes that are used in a loop
TITLE_SETEXT_PATTERN = re.compile(r"^(.+)\n=+\n+", flags=re.MULTILINE)
TITLE_H1_PATTERN = re.compile(r"^# .+\n+", flags=re.MULTILINE)
PROMO_PATTERN = re.compile("|".join(map(re.escape, [
    "拿起手机，搜索微信公众号“长宁房管”，住房相关政策，重点信息一手掌握，赶紧动动手指关注我们吧！",
    "拿起手机，搜索微信公众号“长宁房管”，住房保障重要政策，重点信息一手掌握，赶紧动动手指关注我们吧！",
    "房友们，点上方蓝色**“长宁房管”**关注我们，点文末**“在看”、“赞”**提高阅读优先权，及时了解住房相关政策，掌握一手重点信息。快来关注我们吧！",
    "[长宁房管](javascript:void\(0\);)",
    "[阅读原文](javascript:;)",
    "**扫描二维码 下载查看**",
    "修改于",
    "点击照片查看更多"
])))
NEWLINE_PATTERN = re.compile(r'\n(\s*\n)+')


def extract_metadata(content):
    metadata = {}
    all_authors = []
    author_keys = ["撰稿人", "投稿人", "信息来源"]

    for key in author_keys:
        search_key = f"{key}："
        for line in content.splitlines():
            if line.startswith(search_key):
                authors_text = line.replace(search_key, "").strip()
                authors = [author.strip() for author in authors_text.split('、')]
                all_authors.extend(authors)
    
    if all_authors:
        # Remove duplicates and store
        metadata['authors'] = sorted(list(set(all_authors)))
        
    return metadata

def clean_content(content):
    # Remove title (these patterns are anchored to the start of lines)
    # We run them with count=1 to only remove the first occurrence found.
    content = TITLE_SETEXT_PATTERN.sub("", content, 1)
    content = TITLE_H1_PATTERN.sub("", content, 1)

    # Remove markdown image links efficiently if at the start of the content
    if content.startswith("![cover_image]"):
        pos = content.find('\n')
        content = content[pos+1:] if pos != -1 else ""

    # Remove any line containing "阅读原文"
    lines = content.splitlines()
    filtered_lines = [line for line in lines if "阅读原文" not in line]
    content = "\n".join(filtered_lines)

    # Remove all occurrences of promotional sentences
    content = PROMO_PATTERN.sub("", content)

    # Remove all asterisks
    content = content.replace('*', '')
    content = content.replace('〓', '')
    content = content.replace('▼', '')

    # Collapse multiple newlines into one
    content = NEWLINE_PATTERN.sub('\n', content)

    # Remove any leading whitespace/blank lines that may have been left by replacements
    content = content.lstrip()
    content = content.rstrip()
    
    return content

def process_all_files_in_directory(input_dir, processed_dir):
    for filename in os.listdir(input_dir):
        input_file_path = os.path.join(input_dir, filename)
        processed_md_path = os.path.join(processed_dir, filename)

        with open(input_file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        metadata = extract_metadata(raw_content)
        cleaned_content = clean_content(raw_content)

        if len(cleaned_content) < 100:
            continue

        # Write the cleaned markdown file
        with open(processed_md_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)

        structured_data = {
            'file_name': filename,
            'title': filename.replace('.md', ''),
            'cleaned_content': cleaned_content,
            'raw_content': raw_content,
            **metadata
        }

if __name__ == "__main__":
    data_directory = "data"
    processed_data_directory = "processed_data"
    process_all_files_in_directory(data_directory, processed_data_directory)
