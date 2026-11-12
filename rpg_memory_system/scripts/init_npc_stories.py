# -*- coding: utf-8 -*-
import asyncio
import sys
import os
import re
import argparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# 加载MySQL环境变量
load_dotenv('.env.mysql')

from src.server.api.models.mysql_database import NpcStory, Base
from src.server.api.models.llm_client import llm_client

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

async def init_aliya_stories(force_reinit=False):
    """初始化Aliya的NPC故事记忆"""
    try:
        # 读取Aliya长期记忆.md文件
        md_file_path = os.path.join(os.path.dirname(__file__), '..', 'Aliya长期记忆.md')
        
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("开始初始化Aliya NPC故事记忆...")
        
        # 创建异步数据库引擎
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("未找到DATABASE_URL环境变量")
        
        engine = create_async_engine(database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # 检查是否已经初始化过
            from sqlalchemy import select, func, delete
            result = await session.execute(select(func.count(NpcStory.id)))
            existing_count = result.scalar()
            
            if existing_count > 0 and not force_reinit:
                print(f"数据库中已存在 {existing_count} 条NPC故事记忆，跳过初始化")
                print("如需重新初始化，请使用 --force 参数")
                return
            elif existing_count > 0 and force_reinit:
                print(f"强制重新初始化：删除现有的 {existing_count} 条记录")
                await session.execute(delete(NpcStory))
                await session.commit()
            
            # 使用细化切片策略解析markdown内容
            chunks = extract_detailed_chunks(content)
            print(f"提取到 {len(chunks)} 个细化文档块")
            
            # 使用细化切片函数
            aliya_stories = extract_detailed_chunks(content)
            
            # 过滤掉过短的内容，但降低阈值以保留更多细节
            aliya_stories = [story for story in aliya_stories if len(story["content"]) > 20]
            
            print(f"从Aliya长期记忆.md中提取到 {len(aliya_stories)} 条故事内容")
            
            # 为每个故事生成嵌入向量并存储
            for i, story in enumerate(aliya_stories):
                print(f"处理故事 {i+1}/{len(aliya_stories)}: {story['story_name']}")
                
                # 生成嵌入向量
                embedding = await llm_client.generate_embedding(story['content'])
                
                if embedding:
                    # 创建NPC故事记录
                    npc_story = NpcStory(
                        story_name=story['story_name'],
                        content=story['content'],
                        embedding=embedding
                    )
                    
                    session.add(npc_story)
                else:
                    print(f"警告：故事 '{story['story_name']}' 的嵌入向量生成失败")
            
            # 提交到数据库
            await session.commit()
            print(f"成功初始化 {len(aliya_stories)} 条Aliya NPC故事记忆")
            
    except Exception as e:
        print(f"[ERROR] 初始化Aliya故事记忆失败: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='初始化Aliya NPC故事记忆')
    parser.add_argument('--force', action='store_true', help='强制重新初始化，删除现有数据')
    args = parser.parse_args()
    
    asyncio.run(init_aliya_stories(force_reinit=args.force))