import os
import sys

def process_and_save_files(input_dir: str, output_dir: str):
    """
    遍历输入目录中的.md文件，添加H1标题，并保存到输出目录。
    原始文件不会被修改。

    Args:
        input_dir (str): 包含原始markdown文件的目录。
        output_dir (str): 用于保存已处理文件的目录。
    """
    # 检查输入目录是否存在
    if not os.path.isdir(input_dir):
        print(f"错误: 输入目录 '{input_input_dir}' 不存在。", file=sys.stderr)
        return

    # 创建输出目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)
    print(f"输出目录 '{output_dir}' 已准备就绪。")

    # 遍历输入目录中的所有文件
    for filename in os.listdir(input_dir):
        if filename.endswith(".md"):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            
            # 从文件名中提取标题 (去掉.md后缀)
            title = os.path.splitext(filename)[0]
            
            # 格式化H1标题行
            title_line = f"# {title}\n\n"
            
            try:
                # 读取原始文件内容
                with open(input_path, 'r', encoding='utf-8') as f_in:
                    content = f_in.read()
                
                # 准备新内容
                # 检查原始文件是否已有标题，避免重复添加
                if content.strip().startswith("# "):
                    print(f"文件 '{filename}' 在源目录中已有标题，直接拷贝。")
                    new_content = content
                else:
                    new_content = title_line + content
                
                # 写入新文件
                with open(output_path, 'w', encoding='utf-8') as f_out:
                    f_out.write(new_content)

                print(f"已处理文件 '{filename}' 并保存到 '{output_dir}'。")

            except Exception as e:
                print(f"处理文件 '{filename}' 时出错: {e}", file=sys.stderr)

if __name__ == '__main__':
    source_directory = "format_data"
    destination_directory = "add_main_title"
    
    print("开始处理文件...")
    print(f"源目录:      {source_directory}")
    print(f"目标目录:  {destination_directory}")
    
    process_and_save_files(source_directory, destination_directory)
    
    print("\n所有文件处理完毕。")