import os
import re
import sys

def format_metadata_with_regex(input_dir: str, output_dir: str):
    """
    使用正则表达式查找并格式化文件末尾的元数据（如来源、作者）。

    Args:
        input_dir (str): 输入目录的路径。
        output_dir (str): 输出目录的路径。
    """
    if not os.path.isdir(input_dir):
        print(f"错误: 输入目录 '{input_dir}' 不存在。", file=sys.stderr)
        return

    os.makedirs(output_dir, exist_ok=True)
    print(f"源目录:      {input_dir}")
    print(f"目标目录:  {output_dir}")

    # 正则表达式，匹配常见的元数据行
    # 关键词: 来源, 撰稿, 作者, 编辑, 摄影, 校对等
    # `\s*` 匹配任意空白符, `[:：]` 匹配中英文冒号
    METADATA_PATTERN = re.compile(r"^\s*[\*\-]?\s*(资料来源|信息来源|来源|撰稿人|撰稿|作者|编辑|摄影|校对|投稿人)\s*[:：].*$")

    files = [f for f in os.listdir(input_dir) if f.endswith('.md')]
    total_files = len(files)
    print(f"共找到 {total_files} 个文件待处理。")

    for i, filename in enumerate(files):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)

        print(f"[{i+1}/{total_files}] 正在处理: {filename} ...")

        if os.path.exists(output_path):
            print("  -> 文件已存在，跳过。")
            continue

        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        metadata_lines_indices = []
        # 从后往前遍历，查找末尾连续的元数据行
        for j in range(len(lines) - 1, -1, -1):
            line_content = lines[j].strip()
            # 先净化，再匹配
            cleaned_line = line_content.strip('*- _')
            if METADATA_PATTERN.match(cleaned_line):
                metadata_lines_indices.insert(0, j)
            # 如果遇到了非元数据行，且不是空行，就停止查找
            elif line_content and not metadata_lines_indices:
                break # 已经不在末尾的元数据块了
            elif not line_content and metadata_lines_indices:
                # 如果是空行，且已经找到了元数据，也认为是元数据块的一部分
                 metadata_lines_indices.insert(0, j)
            elif line_content and metadata_lines_indices:
                # 如果是实体行，且已经找到了元数据，说明元数据块结束
                break


        if metadata_lines_indices:
            # 分离正文和元数据
            first_meta_index = metadata_lines_indices[0]
            content_lines = lines[:first_meta_index]
            metadata_lines = lines[first_meta_index:]

            # 格式化元数据
            formatted_metadata = [f"> {line.strip().strip('*- ')}\n" for line in metadata_lines if line.strip()]
            
            # 重新组合内容
            final_content = "".join(content_lines).rstrip() + "\n\n---" + "".join(formatted_metadata)
        else:
            # 没有找到元数据，内容保持不变
            final_content = "".join(lines)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print(f"  -> 已保存至: {output_path}")

if __name__ == '__main__':
    source_directory = "add_main_title"
    destination_directory = "final_data" # 使用新的输出目录
    
    print("开始使用正则表达式格式化文末信息...")
    format_metadata_with_regex(source_directory, destination_directory)
    print("\n所有文件处理完毕。")