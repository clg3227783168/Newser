import os
import sys
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# --- 系统指令 (Prompt) ---
SYSTEM_PROMPT = """
你是一位专业的文章结构分析师和Markdown格式化专家。你的任务是接收一篇已经经过初步处理的Markdown文章，并对其进行最终的结构优化和内容清理。

请严格遵守以下规则：
1.  **优化标题结构**：
    *   文章的 `# 主标题` 和文末 `---` 分割的作者信息都已格式正确，请原样保留。
    *   你的核心任务是评估并优化正文部分的 `##` 和 `###` 副标题。如果现有副标题层级不当，请修正它。
    *   将仅由粗体文本组成的行（例如 `**这是一个标题**`）转换成合适的副标题层级（`##` 或 `###`）。
    *   在没有明确标题但逻辑上应该分段的地方，智能地提炼并添加新的副标题。

2.  **清理无效内容**：
    *   识别并彻底删除任何不属于文章内容的、源于网页或UI的残留指令，例如 `< 左右滑动 查看更多 >`。

3.  **内容保持**：除了上述的标题结构优化和UI元素清理外，绝对不能修改、删除、概括或增加任何原始文字内容。

4.  **纯净输出**：你的回答必须是且仅是优化后的Markdown全文，不要包含任何额外的解释、评论或前言。
"""

# --- LLM 初始化 ---
llm = ChatOpenAI(
    temperature=0.1, # 使用更低的温度，让模型严格遵循指令
    model="glm-4",
    openai_api_key=os.getenv("ZHIPUAI_API_KEY"),
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
)

def clean_markdown_file(file_path: str, llm_chain) -> str:
    """
    使用大语言模型清理并结构化单个Markdown文件。
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    response = llm_chain.invoke({"text_input": content})
    return response.content

def process_directory(input_dir: str, output_dir: str):
    """
    处理指定目录下的所有Markdown文件，并保存到输出目录。
    会跳过输出目录中已存在的同名文件。
    """
    if not os.path.isdir(input_dir):
        print(f"错误: 输入目录 '{input_dir}' 不存在。", file=sys.stderr)
        return

    os.makedirs(output_dir, exist_ok=True)
    print(f"源目录:      {input_dir}")
    print(f"目标目录:  {output_dir}")

    files_in_input = {f for f in os.listdir(input_dir) if f.endswith('.md')}
    files_in_output = {f for f in os.listdir(output_dir) if f.endswith('.md')}
    
    files_to_process = sorted(list(files_in_input - files_in_output))
    
    if not files_to_process:
        print("所有文件均已处理，无需操作。")
        return
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", "{text_input}")
    ])
    chain = prompt | llm

    total_to_process = len(files_to_process)
    print(f"共找到 {len(files_in_input)} 个文件，其中 {total_to_process} 个是新文件，准备处理。")

    for i, filename in enumerate(files_to_process):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        
        print(f"[{i+1}/{total_to_process}] 正在清理: {filename} ...")
        
        try:
            cleaned_content = clean_markdown_file(input_path, chain)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"  -> 已保存至: {output_path}")
        except Exception as e:
            print(f"  -> 处理文件 '{filename}' 时出错: {e}", file=sys.stderr)

if __name__ == '__main__':
    if not os.getenv("ZHIPUAI_API_KEY"):
        print("错误：环境变量 ZHIPUAI_API_KEY 未设置。请先设置API Key。", file=sys.stderr)
    else:
        source_directory = "final_data"
        destination_directory = "untra_final_data"
        
        print("开始对所有文件进行最终的清理和结构优化...")
        process_directory(source_directory, destination_directory)
        print("\n所有文件处理完毕。")
