#!/usr/bin/env python3
"""
简化的数据库提示词测试（不依赖langfuse）
"""
import os
import sys
import asyncio
import json

# 添加项目路径
sys.path.append('/home/shengchan/prodev/AIgame/rpg_memory_system')

class SimpleDatabasePromptManager:
    """简化的数据库提示词管理器，仅用于测试"""
    
    def __init__(self):
        self.prompt_cache = {}
        
    async def get_prompt_from_database(self, template_key: str):
        """从数据库获取提示词模板"""
        try:
            import aiomysql
            
            # 数据库连接配置
            config = {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': 'aigame_strong_root_password_123',
                'db': 'aigame_db',
                'charset': 'utf8mb4'
            }
            
            conn = await aiomysql.connect(**config)
            cursor = await conn.cursor(aiomysql.DictCursor)
            
            # 查询当前发布的提示词版本
            query = """
            SELECT 
                pt.template_key,
                pt.template_name,
                pt.template_type,
                pv.content,
                pv.variables,
                pv.version_number
            FROM prompt_templates pt
            JOIN prompt_versions pv ON pt.id = pv.template_id
            WHERE pt.template_key = %s 
              AND pv.is_current_published = 1
            """
            
            await cursor.execute(query, (template_key,))
            result = await cursor.fetchone()
            
            await cursor.close()
            conn.close()
            
            if result:
                # 解析variables JSON
                variables = {}
                if result['variables']:
                    try:
                        variables = json.loads(result['variables'])
                    except json.JSONDecodeError:
                        variables = {}
                
                return {
                    'template_key': result['template_key'],
                    'template_name': result['template_name'],
                    'template_type': result['template_type'],
                    'content': result['content'],
                    'variables': variables,
                    'version_number': result['version_number']
                }
            else:
                print(f"未找到提示词模板: {template_key}")
                return None
                
        except Exception as e:
            print(f"从数据库获取提示词失败 {template_key}: {e}")
            return None
    
    async def get_cached_prompt(self, template_key: str):
        """获取缓存的提示词，如果不存在则从数据库加载"""
        if template_key not in self.prompt_cache:
            prompt_data = await self.get_prompt_from_database(template_key)
            if prompt_data:
                self.prompt_cache[template_key] = prompt_data
        
        return self.prompt_cache.get(template_key)

async def test_database_connection():
    """测试数据库连接"""
    print("🔗 测试数据库连接...")
    
    try:
        import aiomysql
        
        config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': 'aigame_strong_root_password_123',
            'db': 'aigame_db',
            'charset': 'utf8mb4'
        }
        
        conn = await aiomysql.connect(**config)
        cursor = await conn.cursor()
        
        # 测试查询
        await cursor.execute("SELECT COUNT(*) FROM prompt_templates WHERE category = 'rpg_memory'")
        result = await cursor.fetchone()
        
        await cursor.close()
        conn.close()
        
        template_count = result[0] if result else 0
        print(f"✅ 数据库连接成功，找到 {template_count} 个RPG记忆提示词模板")
        return template_count == 5
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

async def test_database_prompt_manager():
    """测试数据库提示词管理器"""
    print("\n🧪 测试数据库提示词管理器...")
    
    try:
        manager = SimpleDatabasePromptManager()
        
        # 测试获取用户画像提取提示词
        prompt_data = await manager.get_prompt_from_database('rpg_extract_user_profile')
        
        if prompt_data:
            print("✅ 成功从数据库获取用户画像提取提示词")
            print(f"   - 模板名称: {prompt_data['template_name']}")
            print(f"   - 版本号: {prompt_data['version_number']}")
            print(f"   - 变量配置: {prompt_data['variables']}")
            print(f"   - 内容长度: {len(prompt_data['content'])} 字符")
        else:
            print("❌ 未能从数据库获取提示词")
            return False
            
        # 测试缓存功能
        cached_data = await manager.get_cached_prompt('rpg_extract_user_profile')
        if cached_data:
            print("✅ 缓存功能正常")
        
        # 测试获取所有5个提示词
        template_keys = [
            'rpg_extract_user_profile',
            'rpg_extract_events', 
            'rpg_generate_reflection',
            'rpg_consolidate_memories',
            'rpg_generate_npc_response'
        ]
        
        print(f"\n🔍 测试获取所有 {len(template_keys)} 个提示词...")
        success_count = 0
        
        for key in template_keys:
            data = await manager.get_cached_prompt(key)
            if data:
                print(f"   ✅ {key}: {data['template_name']}")
                success_count += 1
            else:
                print(f"   ❌ {key}: 获取失败")
        
        print(f"\n📊 成功获取 {success_count}/{len(template_keys)} 个提示词")
        return success_count == len(template_keys)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_prompt_template_formatting():
    """测试提示词模板格式化功能"""
    print("\n🔧 测试提示词模板格式化...")
    
    try:
        manager = SimpleDatabasePromptManager()
        
        # 获取用户画像提取提示词
        prompt_data = await manager.get_cached_prompt('rpg_extract_user_profile')
        
        if not prompt_data:
            print("❌ 无法获取提示词模板")
            return False
        
        # 测试变量替换
        test_dialogue = "user: 你好，我叫张三\\nassistant: 你好张三"
        
        prompt_content = prompt_data['content']
        formatted_content = prompt_content.replace('{dialogue_text}', test_dialogue)
        
        if '{dialogue_text}' not in formatted_content and test_dialogue in formatted_content:
            print("✅ 提示词变量替换功能正常")
            print(f"   - 原始模板长度: {len(prompt_content)} 字符")
            print(f"   - 格式化后长度: {len(formatted_content)} 字符")
            return True
        else:
            print("❌ 提示词变量替换失败")
            return False
            
    except Exception as e:
        print(f"❌ 格式化测试失败: {e}")
        return False

async def test_view_functionality():
    """测试便捷视图功能"""
    print("\n👁️  测试便捷视图功能...")
    
    try:
        import aiomysql
        
        config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': 'aigame_strong_root_password_123',
            'db': 'aigame_db',
            'charset': 'utf8mb4'
        }
        
        conn = await aiomysql.connect(**config)
        cursor = await conn.cursor(aiomysql.DictCursor)
        
        # 测试视图查询
        await cursor.execute("SELECT * FROM rpg_memory_prompts")
        results = await cursor.fetchall()
        
        await cursor.close()
        conn.close()
        
        if results:
            print(f"✅ 便捷视图功能正常，返回 {len(results)} 条记录")
            for result in results:
                print(f"   - {result['template_key']}: {result['template_name']}")
            return len(results) == 5
        else:
            print("❌ 便捷视图无数据")
            return False
            
    except Exception as e:
        print(f"❌ 视图测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始测试RPG记忆系统数据库提示词功能\n")
    
    # 测试1: 数据库连接
    test1_passed = await test_database_connection()
    
    # 测试2: 数据库提示词管理器
    test2_passed = await test_database_prompt_manager()
    
    # 测试3: 提示词格式化
    test3_passed = await test_prompt_template_formatting()
    
    # 测试4: 便捷视图
    test4_passed = await test_view_functionality()
    
    # 总结
    print(f"\n{'='*50}")
    print("📊 测试结果总结:")
    print(f"   🔗 数据库连接: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"   🔧 提示词管理器: {'✅ 通过' if test2_passed else '❌ 失败'}")
    print(f"   📝 模板格式化: {'✅ 通过' if test3_passed else '❌ 失败'}")
    print(f"   👁️  便捷视图: {'✅ 通过' if test4_passed else '❌ 失败'}")
    
    all_passed = all([test1_passed, test2_passed, test3_passed, test4_passed])
    
    if all_passed:
        print(f"\n🎉 所有测试通过！数据库提示词功能正常工作")
        print("✨ SQL迁移成功，数据库版本的LLM客户端可以正常使用")
        print("\n📋 后续步骤:")
        print("   1. 安装langfuse依赖: pip install langfuse")
        print("   2. 备份原始文件: cp llm_client.py llm_client_backup.py")
        print("   3. 替换客户端: cp llm_client_database.py llm_client.py")
    else:
        print(f"\n⚠️  部分测试失败，需要检查配置和数据库")
    
    return all_passed

if __name__ == "__main__":
    # 运行测试
    result = asyncio.run(main())
    sys.exit(0 if result else 1)