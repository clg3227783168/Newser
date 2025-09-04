# This code is based on or derived from code obtained from:
# https://github.com/InternLM/HuixiangDou/blob/main/LICENSE
#
# Original License:
# BSD 3-Clause License


import yaml # ���� yaml ��
import re # ���� re ��
import copy # ���� copy ��
from typing import (Dict, List, Optional, Tuple, TypedDict, Callable, Union) # ��� Union
from dataclasses import dataclass, field


# --- ���ݽṹ�����Ͷ��� ---

@dataclass
class Chunk:
    """���ڴ洢�ı�Ƭ�μ����Ԫ���ݵ��ࡣ"""
    content: str = ''
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        """��д __str__ ������ʹ������� content �� metadata��"""
        if self.metadata:
            return f"content='{self.content}' metadata={self.metadata}"
        else:
            return f"content='{self.content}'"

    def __repr__(self) -> str:
        return self.__str__()

    def to_markdown(self, return_all: bool = False) -> str:
        """����ת��Ϊ Markdown ��ʽ��

        Args:
            return_all: ���Ϊ True����������ǰ���� YAML ��ʽ��Ԫ���ݡ�

        Returns:
            Markdown ��ʽ���ַ�����
        """
        md_string = ""
        if return_all and self.metadata:
            # ʹ�� yaml.dump ��Ԫ���ݸ�ʽ��Ϊ YAML �ַ���
            # allow_unicode=True ȷ�������ַ���ȷ��ʾ
            # sort_keys=False ����ԭʼ˳��
            metadata_yaml = yaml.dump(self.metadata, allow_unicode=True, sort_keys=False)
            md_string += f"---\n{metadata_yaml}---\n\n"
        md_string += self.content
        return md_string

class LineType(TypedDict):
    """�����ͣ�ʹ�������ֵ䶨�塣"""
    metadata: Dict[str, str] # Ԫ�����ֵ�
    content: str # ������

class HeaderType(TypedDict):
    """�������ͣ�ʹ�������ֵ䶨�塣"""
    level: int # ���⼶��
    name: str # �������� (����, 'Header 1')
    data: str # �����ı�����

class MarkdownHeaderTextSplitter:
    """����ָ���ı���ָ� Markdown �ļ�������ѡ�ظ��� chunk_size ��һ��ϸ�֡�"""

    def __init__(
        self,
        headers_to_split_on: List[Tuple[str, str]] = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
            ("#####", "h5"),
            ("######", "h6"),
        ],
        strip_headers: bool = False,
        chunk_size: Optional[int] = None, # ��� chunk_size ����
        length_function: Callable[[str], int] = len, # ��� length_function ����
        separators: Optional[List[str]] = None, # ��� separators ����
        is_separator_regex: bool = False, # ��� is_separator_regex ����
    ):
        """����һ���µ� MarkdownHeaderTextSplitter��

        Args:
            headers_to_split_on: ���ڷָ�ı��⼶�������Ԫ���б�
            strip_headers: �Ƿ�ӿ��������Ƴ������С�
            chunk_size: ������Ǵ������ݳ��ȡ�������ã�����һ���ָ���Ŀ顣
            length_function: ���ڼ����ı����ȵĺ�����
            separators: ���ڷָ�ķָ����б����ȼ��Ӹߵ��͡�
            is_separator_regex: �Ƿ񽫷ָ�����Ϊ������ʽ��
        """
        if chunk_size is not None and chunk_size <= 0:
            raise ValueError("chunk_size �������������� None��")

        self.headers_to_split_on = sorted(
            headers_to_split_on, key=lambda split: len(split[0]), reverse=True
        )
        self.strip_headers = strip_headers
        self._chunk_size = chunk_size
        self._length_function = length_function
        # ����Ĭ�Ϸָ��������ȶ��䣬��λ���
        self._separators = separators or [
            "\n\n",  # ����
            "\n",    # ��
            "��|��|��",  # ���ľ�ĩ���
            "\.\s|\!\s|\?\s", # Ӣ�ľ�ĩ���ӿո�
            "��|;\s",  # �ֺ�
            "��|,\s"   # ����
        ]
        self._is_separator_regex = is_separator_regex
        # Ԥ����������ʽ�������Ҫ��
        self._compiled_separators = None
        if self._is_separator_regex:
            self._compiled_separators = [re.compile(s) for s in self._separators]

    def _calculate_length_excluding_code(self, text: str) -> int:
        """�����ı����ȣ���������������ݡ�"""
        total_length = 0
        last_end = 0
        # ������ʽ���� ```...``` �� ~~~...~~~ �����
        # ʹ�÷�̰��ƥ�� .*?
        for match in re.finditer(r"(?:```|~~~).*?\n(?:.*?)(?:```|~~~)", text, re.DOTALL | re.MULTILINE):
            start, end = match.span()
            # ��Ӵ˴����֮ǰ���ı�����
            total_length += self._length_function(text[last_end:start])
            last_end = end
        # ������һ�������֮����ı�����
        total_length += self._length_function(text[last_end:])
        return total_length

    def _find_best_split_point(self, lines: List[str]) -> int:
        """�����б��в�����ѷָ�㣨��������

        ����Ѱ�Ҷ���ָ����������������з���������ǵ������з���
        �Ӻ���ǰ���ң����طָ�� *֮��* ����һ��������
        ����Ҳ������ʵķָ��㣨����ֻ��һ�У������� -1��
        """
        if len(lines) <= 1:
            return -1

        # ���Ȳ��Ҷ���ָ��� "\n\n"
        # ���Ӧ��һ������
        for i in range(len(lines) - 2, 0, -1): # �ӵ����ڶ�����ǰ�ҵ��ڶ���
            if not lines[i].strip() and lines[i+1].strip(): # ��ǰ���ǿ��У���һ�в���
                 # ���ǰһ��Ҳ���ǿ��У�ȷ���Ƕ����ķָ�
                 if i > 0 and lines[i-1].strip():
                     return i + 1 # �ڿ���֮��ָ�

        # ���û���ҵ�����ָ������������һ�����з����ָ�
        # �����ڵ����ڶ���֮��ָ
        if len(lines) > 1:
             return len(lines) - 1 # �ڵ����ڶ���֮��ָ���������һ�и���һ���飩

        return -1 # �������������>1�ܻ��ҵ����з�������Ϊ����

    def _split_chunk_by_size(self, chunk: Chunk) -> List[Chunk]:
        """������ chunk_size �Ŀ�ָ�ɸ�С�Ŀ飬����ʹ�÷ָ�����"""
        if self._chunk_size is None: # ���δ���� chunk_size���򲻷ָ�
             return [chunk]

        sub_chunks = []
        current_lines = []
        current_non_code_len = 0
        in_code = False
        code_fence = None
        lines = chunk.content.split('\n')

        for line_idx, line in enumerate(lines):
            stripped_line = line.strip()
            is_entering_code = False
            is_exiting_code = False

            # --- �����߽��� ---
            if not in_code:
                if stripped_line.startswith("```") and stripped_line.count("```") == 1:
                    is_entering_code = True; code_fence = "```"
                elif stripped_line.startswith("~~~") and stripped_line.count("~~~") == 1:
                    is_entering_code = True; code_fence = "~~~"
            elif in_code and code_fence is not None and stripped_line.startswith(code_fence):
                is_exiting_code = True
            # --- �����߽������ ---

            # --- �����г��ȹ��� ---
            line_len_contribution = 0
            if not in_code and not is_entering_code:
                line_len_contribution = self._length_function(line) + 1 # +1 for newline
            elif is_exiting_code:
                line_len_contribution = self._length_function(line) + 1
            # --- �����г��ȹ��׽��� ---

            # --- ����Ƿ���Ҫ�ָ� ---
            split_needed = (
                line_len_contribution > 0 and
                current_non_code_len + line_len_contribution > self._chunk_size and
                current_lines # �����������ݲ��ָܷ�
            )

            if split_needed:
                # �����ҵ���ѷָ��
                split_line_idx = self._find_best_split_point(current_lines)

                if split_line_idx != -1 and split_line_idx > 0: # ȷ�������ڵ�һ�оͷָ�
                    lines_to_chunk = current_lines[:split_line_idx]
                    remaining_lines = current_lines[split_line_idx:]

                    # �����������һ���ӿ�
                    content = "\n".join(lines_to_chunk)
                    sub_chunks.append(Chunk(content=content, metadata=chunk.metadata.copy()))

                    # ��ʼ�µ��ӿ飬����ʣ���к͵�ǰ��
                    current_lines = remaining_lines + [line]
                    # ���¼����� current_lines �ķǴ��볤��
                    current_non_code_len = self._calculate_length_excluding_code("\n".join(current_lines))

                else: # �Ҳ����õķָ��� current_lines ̫�̣�ִ��Ӳ�ָ�
                    content = "\n".join(current_lines)
                    sub_chunks.append(Chunk(content=content, metadata=chunk.metadata.copy()))
                    current_lines = [line]
                    current_non_code_len = line_len_contribution if not is_entering_code else 0

            else: # ����Ҫ�ָ������ӵ���ǰ�ӿ�
                current_lines.append(line)
                if line_len_contribution > 0:
                    current_non_code_len += line_len_contribution
            # --- ����Ƿ���Ҫ�ָ���� ---


            # --- ���´����״̬ ---
            if is_entering_code: in_code = True
            elif is_exiting_code: in_code = False; code_fence = None
            # --- ���´����״̬���� ---

        # ������һ���ӿ�
        if current_lines:
            content = "\n".join(current_lines)
            # �����һ��������Ƿ񳬳�������ֻ��һ��Ԫ�ص�������
            final_non_code_len = self._calculate_length_excluding_code(content)
            if final_non_code_len > self._chunk_size and len(sub_chunks) > 0:
                 # ������һ���鳬�������Ҳ���Ψһ�Ŀ飬������Ҫ��������⴦��
                 # ����򵥵����������ʹ������
                 pass # logger.warning(f"Final chunk exceeds chunk_size: {final_non_code_len} > {self._chunk_size}")
            sub_chunks.append(Chunk(content=content, metadata=chunk.metadata.copy()))

        return sub_chunks if sub_chunks else [chunk]


    def _aggregate_lines_to_chunks(self, lines: List[LineType],
                                   base_meta: dict) -> List[Chunk]:
        """�����й�ͬԪ���ݵ��кϲ��ɿ顣"""
        aggregated_chunks: List[LineType] = []

        for line in lines:
            if aggregated_chunks and aggregated_chunks[-1]["metadata"] == line["metadata"]:
                # ׷�����ݣ��������з�
                aggregated_chunks[-1]["content"] += "\n" + line["content"]
            else:
                # �����µľۺϿ飬ʹ�� copy ��ֹ�����޸�Ӱ��
                aggregated_chunks.append(copy.deepcopy(line))

        final_chunks = []
        for chunk_data in aggregated_chunks:
            final_metadata = base_meta.copy()
            final_metadata.update(chunk_data['metadata'])
            # �������Ƴ� strip()����Ϊ������ _split_chunk_by_size ��Ҫԭʼ���з�
            final_chunks.append(
                Chunk(content=chunk_data["content"], # �Ƴ� .strip()
                      metadata=final_metadata)
            )
        return final_chunks


    def split_text(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        """���ڱ���ָ� Markdown �ı��������� chunk_size ��һ��ϸ�֡�"""
        base_metadata = metadata or {}
        lines = text.split("\n")
        lines_with_metadata: List[LineType] = []
        current_content: List[str] = []
        current_metadata: Dict[str, str] = {}
        header_stack: List[HeaderType] = []

        in_code_block = False
        opening_fence = ""

        for line_num, line in enumerate(lines):
            stripped_line = line.strip()

            # --- ����鴦���߼���ʼ ---
            # ����Ƿ��Ǵ���鿪ʼ��������
            is_code_fence = False
            if not in_code_block:
                 if stripped_line.startswith("```") and stripped_line.count("```") == 1:
                     in_code_block = True
                     opening_fence = "```"
                     is_code_fence = True
                 elif stripped_line.startswith("~~~") and stripped_line.count("~~~") == 1:
                     in_code_block = True
                     opening_fence = "~~~"
                     is_code_fence = True
            # ����Ƿ���ƥ��Ľ������
            elif in_code_block and opening_fence is not None and stripped_line.startswith(opening_fence):
                 in_code_block = False
                 opening_fence = ""
                 is_code_fence = True
            # --- ����鴦���߼����� ---


            # ����ڴ�����ڣ������߽��У���ֱ����ӵ���ǰ����
            if in_code_block or is_code_fence:
                current_content.append(line)
                continue # ������һ�У���������

            # --- ���⴦���߼���ʼ (���ڴ������ִ��) ---
            found_header = False
            for sep, name in self.headers_to_split_on:
                if stripped_line.startswith(sep) and (
                    len(stripped_line) == len(sep) or stripped_line[len(sep)] == " "
                ):
                    found_header = True
                    header_level = sep.count("#")
                    header_data = stripped_line[len(sep):].strip()

                    # ����ҵ��±��⣬�ҵ�ǰ�����ݣ���֮ǰ�����ݾۺ�
                    if current_content:
                        lines_with_metadata.append({
                            "content": "\n".join(current_content),
                            "metadata": current_metadata.copy(),
                        })
                        current_content = [] # ��������

                    # ���±���ջ
                    while header_stack and header_stack[-1]["level"] >= header_level:
                        header_stack.pop()
                    new_header: HeaderType = {"level": header_level, "name": name, "data": header_data}
                    header_stack.append(new_header)
                    current_metadata = {h["name"]: h["data"] for h in header_stack}

                    # �����������⣬�򽫱�������ӵ������ݵĿ�ʼ
                    if not self.strip_headers:
                        current_content.append(line)

                    break # �ҵ�ƥ�����߼������ֹͣ���
            # --- ���⴦���߼����� ---

            # ������Ǳ������Ҳ��ڴ������
            if not found_header:
                 # ֻ�е��в�Ϊ�ջ�ǰ��������ʱ����ӣ���������ĵ���ͷ�Ŀ��У�
                 # ���߱���������ά�ָ�ʽ
                 if line.strip() or current_content:
                    current_content.append(line)

        # �����ĵ�ĩβʣ�������
        if current_content:
            lines_with_metadata.append({
                "content": "\n".join(current_content),
                "metadata": current_metadata.copy(),
            })

        # ��һ�������ڱ���ۺϿ�
        aggregated_chunks = self._aggregate_lines_to_chunks(lines_with_metadata, base_meta=base_metadata)

        # �ڶ�������������� chunk_size�����һ��ϸ�ֿ�
        if self._chunk_size is None:
            return aggregated_chunks # ���û�� chunk_size��ֱ�ӷ��ؾۺϿ�
        else:
            final_chunks = []
            for chunk in aggregated_chunks:
                # ����ķǴ������ݳ���
                non_code_len = self._calculate_length_excluding_code(chunk.content)

                if non_code_len > self._chunk_size:
                    # ���������С�������ϸ��
                    split_sub_chunks = self._split_chunk_by_size(chunk)
                    final_chunks.extend(split_sub_chunks)
                else:
                    # ���δ������С��ֱ�����
                    final_chunks.append(chunk)
            return final_chunks


# --- ��Ҫִ�� / ���Կ� ---
if __name__ == '__main__':
    # ���Դ����
    try:
        # ���� article.md �ļ������ڽű�ͬĿ¼��
        with open("article.md", "r", encoding="utf-8") as f:
            text = f.read()

        # ���� 1: �����ڱ���ָ� (������ chunk_size)
        # Ч��: ���ɵĿ��������٣�ÿ�����Ӧһ����ͼ���ı�����䡣
        #       ��Ĵ�С���ܷǳ������ȣ���Щ����ܷǳ���
        #       �����ʼ�հ��������������ı�������ڡ�
        print("--- Splitting without chunk_size limit (Header-based only) ---")
        splitter_no_limit = MarkdownHeaderTextSplitter()
        chunks_no_limit = splitter_no_limit.split_text(text)
        print(f"Total chunks: {len(chunks_no_limit)}")
        # ȡ��ע���Բ鿴��ϸ���
        # for chunk in chunks_no_limit:
        #     print(chunk.to_markdown(return_all=True))
        #     print("=" * 40)

        print("\n" + "===" * 20 + "\n")

        # ���� 2: ���ڱ���ָȻ����� chunk_size �ͷָ�����һ��ϸ��
        # Ч��: ���Ȱ�����ָȻ����ڳ��� chunk_size �Ŀ飬
        #       �᳢���ڸ���Ȼ�ı߽磨����� `\n\n` �����/�� `\n`���Լ�������㣩���зָ
        #       Ŀ����ʹ��ķǴ������ݳ��Ƚӽ��������� chunk_size��
        #       ����鱣�����������������ݲ����� chunk_size ���㡣
        #       ��ͨ���ܲ�����С�����ȡ����ʺϺ��������� RAG���Ŀ顣
        print("--- Splitting with chunk_size = 150 (Header-based + Size/Separator-based refinement) ---")
        # ʹ��Ĭ�Ϸָ���: ["\n\n", "\n", "��", "��", "��", ". ", "! ", "? ", "��", "; ", "��", ", "]
        # ������ is_separator_regex=True �Դ������ı���
        splitter_with_limit = MarkdownHeaderTextSplitter(chunk_size=150, is_separator_regex=True) # ע����� is_separator_regex=True ��ʹ��Ĭ�����ķָ���
        chunks_with_limit = splitter_with_limit.split_text(text)
        print(f"Total chunks: {len(chunks_with_limit)}")
        for i, chunk in enumerate(chunks_with_limit):
            print(f"--- Chunk {i+1} ---")
            non_code_len = splitter_with_limit._calculate_length_excluding_code(chunk.content)
            print(f"Content Length (Total): {len(chunk.content)}")
            print(f"Content Length (Non-Code): {non_code_len}") # ���Ǵ��볤���Ƿ�ӽ� chunk_size
            print(f"Metadata: {chunk.metadata}")
            # print("\n--- Markdown (Content Only) ---")
            # print(chunk.to_markdown())
            print("\n--- Markdown (With Metadata) ---")
            print(chunk.to_markdown(return_all=True))
            print("====" * 20) # ���̷ָ����Ա�鿴�����

    except FileNotFoundError:
        print("Error: article.md not found. Please create the file for testing.")