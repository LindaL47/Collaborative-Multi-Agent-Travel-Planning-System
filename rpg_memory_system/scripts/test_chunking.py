# -*- coding: utf-8 -*-
import os
import re

def clean_text(text):
    """清理文本中的HTML标签和格式标记"""
    text = re.sub(r'<[^>]+>', '', text)  # 移除HTML标签
    text = re.sub(r'\*\*', '', text)  # 移除加粗标记
    text = re.sub(r'\*', '', text)  # 移除斜体标记
    return text.strip()

def extract_detailed_chunks(content):
    """提取细化的文档块"""
    chunks = []
    lines = content.split('\n')
    
    current_h2 = ""
    current_h3 = ""
    current_h4 = ""
    current_chunk = ""
    current_title = ""
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        original_line = lines[i]
        
        # 处理二级标题
        if line.startswith('## ') and not line.startswith('### '):
            # 保存之前的块
            if current_chunk and current_title:
                chunks.append({
                    "story_name": current_title,
                    "content": current_chunk.strip()
                })
            
            current_h2 = clean_text(line.replace('##', '').strip())
            current_h3 = ""
            current_h4 = ""
            current_title = current_h2
            current_chunk = clean_text(original_line)
        
        # 处理三级标题
        elif line.startswith('### '):
            # 保存之前的块
            if current_chunk and current_title:
                chunks.append({
                    "story_name": current_title,
                    "content": current_chunk.strip()
                })
            
            current_h3 = clean_text(line.replace('###', '').strip())
            current_h4 = ""
            current_title = f"{current_h2} - {current_h3}" if current_h2 else current_h3
            current_chunk = clean_text(original_line)
        
        # 处理四级标题或加粗项目
        elif line.startswith('#### ') or (line.startswith('+ **') and line.endswith('**')) or (line.startswith('- **') and line.endswith('**')) or re.match(r'^\d+\.\s*\*\*.*\*\*', line):
            # 保存之前的块
            if current_chunk and current_title and len(current_chunk.strip()) > 50:
                chunks.append({
                    "story_name": current_title,
                    "content": current_chunk.strip()
                })
            
            # 提取四级标题或项目标题
            if line.startswith('#### '):
                current_h4 = clean_text(line.replace('####', '').strip())
            else:
                # 提取加粗的项目标题
                bold_match = re.search(r'\*\*(.*?)\*\*', line)
                if bold_match:
                    current_h4 = clean_text(bold_match.group(1))
            
            # 构建新的标题
            title_parts = [part for part in [current_h2, current_h3, current_h4] if part]
            current_title = " - ".join(title_parts)
            current_chunk = clean_text(original_line)
            
            # 收集该项目下的所有内容
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                next_original = lines[j]
                
                # 如果遇到新的标题或项目，停止
                if (next_line.startswith('##') or 
                    next_line.startswith('###') or 
                    next_line.startswith('####') or
                    (next_line.startswith('+ **') and next_line.endswith('**')) or
                    (next_line.startswith('- **') and next_line.endswith('**')) or
                    re.match(r'^\d+\.\s*\*\*.*\*\*', next_line)):
                    break
                
                # 添加内容行
                if next_line:
                    current_chunk += "\n" + clean_text(next_original)
                else:
                    current_chunk += "\n"
                j += 1
            
            # 如果收集到足够内容，保存为一个块
            if len(current_chunk.strip()) > 80:
                chunks.append({
                    "story_name": current_title,
                    "content": current_chunk.strip()
                })
                current_chunk = ""
            
            i = j - 1  # 调整索引
        
        # 处理列表项（细化处理）
        elif (line.startswith('- ') or line.startswith('+ ') or line.startswith('* ') or re.match(r'^\d+\.', line)) and len(line) > 20:
            # 对于长列表项，单独作为一个块
            list_content = clean_text(original_line)
            
            # 收集多行列表项内容
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                next_original = lines[j]
                
                # 如果是缩进内容或子列表项，继续收集
                if (next_line.startswith('    ') or next_line.startswith('\t') or 
                    next_line.startswith('        ') or
                    (next_line.startswith('* ') and not next_line.startswith('**'))):
                    list_content += "\n" + clean_text(next_original)
                    j += 1
                else:
                    break
            
            # 如果列表项内容足够长，作为独立块
            if len(list_content.strip()) > 60:
                list_title_parts = [part for part in [current_h2, current_h3] if part]
                # 提取列表项的关键词作为标题的一部分
                list_key = list_content[:50].replace('\n', ' ').strip()
                if list_key.endswith('：') or list_key.endswith(':'):
                    list_key = list_key[:-1]
                list_title = " - ".join(list_title_parts + [list_key])
                
                chunks.append({
                    "story_name": list_title,
                    "content": list_content.strip()
                })
            else:
                # 内容较短，添加到当前块
                current_chunk += "\n" + clean_text(original_line)
            
            i = j - 1  # 调整索引
        
        # 处理普通内容行
        else:
            if line:  # 非空行
                current_chunk += "\n" + clean_text(original_line)
            else:
                current_chunk += "\n"
        
        i += 1
    
    # 添加最后一个块
    if current_chunk and current_title:
        chunks.append({
            "story_name": current_title,
            "content": current_chunk.strip()
        })
    
    return chunks

def test_chunking():
    """测试切片功能"""
    # 读取Aliya长期记忆.md文件
    md_file_path = os.path.join(os.path.dirname(__file__), '..', 'Aliya长期记忆.md')
    
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("开始测试细化切片功能...")
    
    # 使用细化切片函数
    chunks = extract_detailed_chunks(content)
    
    # 过滤掉过短的内容
    chunks = [chunk for chunk in chunks if len(chunk["content"]) > 20]
    
    print(f"\n总共提取到 {len(chunks)} 个文档块\n")
    
    # 统计信息
    content_lengths = [len(chunk['content']) for chunk in chunks]
    print(f"=== 统计信息 ===")
    print(f"总块数: {len(chunks)}")
    print(f"平均内容长度: {sum(content_lengths) / len(content_lengths):.1f} 字符")
    print(f"最短内容: {min(content_lengths)} 字符")
    print(f"最长内容: {max(content_lengths)} 字符")
    
    # 按长度分类统计
    short_chunks = [c for c in chunks if len(c['content']) < 100]
    medium_chunks = [c for c in chunks if 100 <= len(c['content']) < 300]
    long_chunks = [c for c in chunks if len(c['content']) >= 300]
    
    print(f"\n=== 长度分布 ===")
    print(f"短块 (<100字符): {len(short_chunks)} 个")
    print(f"中块 (100-300字符): {len(medium_chunks)} 个")
    print(f"长块 (>=300字符): {len(long_chunks)} 个")
    
    # 显示一些具体的细节块示例
    print(f"\n=== 细节块示例 (短块) ===")
    for i, chunk in enumerate(short_chunks[:3]):
        print(f"标题: {chunk['story_name']}")
        print(f"内容: {chunk['content']}")
        print("-" * 50)
    
    print(f"\n=== 中等块示例 ===")
    for i, chunk in enumerate(medium_chunks[:3]):
        print(f"标题: {chunk['story_name']}")
        print(f"内容: {chunk['content'][:150]}...")
        print("-" * 50)
        
    # 显示所有块的标题
    print(f"\n=== 所有块标题 ===")
    for i, chunk in enumerate(chunks):
        print(f"{i+1:2d}. {chunk['story_name']} ({len(chunk['content'])}字符)")

if __name__ == "__main__":
    test_chunking()