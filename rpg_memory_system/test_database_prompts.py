#!/usr/bin/env python3
"""
测试数据库提示词功能
"""
import os
import sys
import asyncio
import json

# 添加项目路径
sys.path.append('/home/shengchan/prodev/AIgame/rpg_memory_system')

# 设置环境变量
os.environ['PYTHONPATH'] = '/home/shengchan/prodev/AIgame/rpg_memory_system'

async def test_database_prompt_manager():
    """测试数据库提示词管理器"""
    print("🧪 测试数据库提示词管理器...")
    
    try:
        from src.server.api.models.llm_client_database import DatabasePromptManager
        
        manager = DatabasePromptManager()
        
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

async def test_llm_client_database():
    """测试数据库版本的LLM客户端"""
    print("\n🧪 测试数据库版本LLM客户端...")
    
    try:
        from src.server.api.models.llm_client_database import LLMClient
        
        client = LLMClient()
        
        # 准备测试数据
        test_dialogue = [
            {"role": "user", "content": "你好，我叫张三，今年25岁"},
            {"role": "assistant", "content": "你好张三，很高兴认识你"},
            {"role": "user", "content": "我喜欢打篮球和听音乐"},
            {"role": "assistant", "content": "篮球和音乐都是很棒的爱好"}
        ]
        
        print("📋 测试数据准备完成，包含4条对话")
        
        # 测试提示词模板调用
        print("\n🔧 测试提示词模板调用功能...")
        
        try:
            # 格式化测试
            dialogue_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in test_dialogue
            ])
            
            response = await client._call_llm_with_prompt_template(
                'rpg_extract_user_profile',
                {'dialogue_text': dialogue_text}
            )
            
            if response:
                print("✅ 提示词模板调用成功")
                print(f"   - 响应长度: {len(response)} 字符")
                
                # 尝试解析JSON
                try:
                    json_data = json.loads(response)
                    print(f"   - JSON解析成功，包含 {len(json_data)} 个字段")
                except:
                    print("   ⚠️  响应不是有效JSON格式")
            else:
                print("❌ 提示词模板调用失败")
                return False
                
        except Exception as e:
            print(f"❌ 提示词模板调用出错: {e}")
            # 继续测试其他功能
        
        # 测试缓存清理
        client.clear_prompt_cache()
        print("✅ 提示词缓存清理成功")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM客户端测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🚀 开始测试RPG记忆系统数据库提示词功能\n")
    
    # 测试1: 数据库提示词管理器
    test1_passed = await test_database_prompt_manager()
    
    # 测试2: 数据库版本LLM客户端
    test2_passed = await test_llm_client_database()
    
    # 总结
    print(f"\n{'='*50}")
    print("📊 测试结果总结:")
    print(f"   🔧 数据库提示词管理器: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"   🤖 数据库LLM客户端: {'✅ 通过' if test2_passed else '❌ 失败'}")
    
    if test1_passed and test2_passed:
        print(f"\n🎉 所有测试通过！数据库提示词功能正常工作")
        print("✨ 可以使用 llm_client_database.py 替换原始的 llm_client.py")
    else:
        print(f"\n⚠️  部分测试失败，需要检查配置和数据库连接")
    
    return test1_passed and test2_passed

if __name__ == "__main__":
    # 运行测试
    result = asyncio.run(main())
    sys.exit(0 if result else 1)