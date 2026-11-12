#!/usr/bin/env python3
"""
RPG记忆系统API测试脚本
测试所有提示词版本管理API端点
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, Any

class RPGMemoryAPITester:
    """RPG记忆系统API测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8888"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_health_check(self):
        """测试健康检查"""
        print("🏥 测试健康检查...")
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ 健康检查通过: {data['status']}")
                    return True
                else:
                    print(f"   ❌ 健康检查失败: {response.status}")
                    return False
        except Exception as e:
            print(f"   ❌ 健康检查异常: {e}")
            return False
    
    async def test_get_templates(self):
        """测试获取所有模板"""
        print("\\n📋 测试获取所有RPG提示词模板...")
        
        try:
            async with self.session.get(f"{self.base_url}/api/rpg-memory-prompts/templates") as response:
                if response.status == 200:
                    templates = await response.json()
                    print(f"   ✅ 成功获取 {len(templates)} 个模板:")
                    for template in templates:
                        print(f"      • {template['template_key']}: {template['template_name']}")
                        print(f"        当前版本: {template.get('current_version', 'N/A')}, 总版本: {template['total_versions']}")
                    return templates
                else:
                    print(f"   ❌ 获取模板失败: {response.status}")
                    text = await response.text()
                    print(f"      错误详情: {text}")
                    return []
        except Exception as e:
            print(f"   ❌ 获取模板异常: {e}")
            return []
    
    async def test_get_template_detail(self, template_key: str):
        """测试获取指定模板详情"""
        print(f"\\n🔍 测试获取模板 '{template_key}' 详情...")
        
        try:
            async with self.session.get(f"{self.base_url}/api/rpg-memory-prompts/templates/{template_key}") as response:
                if response.status == 200:
                    template = await response.json()
                    print(f"   ✅ 模板详情获取成功:")
                    print(f"      名称: {template['template_name']}")
                    print(f"      类型: {template['template_type']}")
                    print(f"      描述: {template.get('description', 'N/A')}")
                    return template
                else:
                    print(f"   ❌ 获取模板详情失败: {response.status}")
                    return None
        except Exception as e:
            print(f"   ❌ 获取模板详情异常: {e}")
            return None
    
    async def test_get_versions(self, template_key: str):
        """测试获取模板的所有版本"""
        print(f"\\n📝 测试获取模板 '{template_key}' 的所有版本...")
        
        try:
            async with self.session.get(f"{self.base_url}/api/rpg-memory-prompts/templates/{template_key}/versions") as response:
                if response.status == 200:
                    versions = await response.json()
                    print(f"   ✅ 成功获取 {len(versions)} 个版本:")
                    for version in versions:
                        status_icon = "🟢" if version['is_current_published'] else "🟡" if version['status'] == 'draft' else "🔴"
                        print(f"      {status_icon} {version['version_number']}: {version.get('version_name', 'N/A')} ({version['status']})")
                    return versions
                else:
                    print(f"   ❌ 获取版本列表失败: {response.status}")
                    return []
        except Exception as e:
            print(f"   ❌ 获取版本列表异常: {e}")
            return []
    
    async def test_get_current_version(self, template_key: str):
        """测试获取当前发布版本"""
        print(f"\\n🎯 测试获取模板 '{template_key}' 的当前发布版本...")
        
        try:
            async with self.session.get(f"{self.base_url}/api/rpg-memory-prompts/templates/{template_key}/current") as response:
                if response.status == 200:
                    version = await response.json()
                    print(f"   ✅ 当前发布版本: {version['version_number']}")
                    print(f"      内容长度: {len(version['content'])} 字符")
                    print(f"      变量配置: {len(version['variables'])} 个")
                    return version
                else:
                    print(f"   ❌ 获取当前版本失败: {response.status}")
                    return None
        except Exception as e:
            print(f"   ❌ 获取当前版本异常: {e}")
            return None
    
    async def test_create_version(self, template_key: str):
        """测试创建新版本"""
        print(f"\\n➕ 测试为模板 '{template_key}' 创建新版本...")
        
        # 获取当前时间戳作为版本号
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_number = f"test_{timestamp}"
        
        # 创建测试版本数据
        create_data = {
            "version_number": version_number,
            "version_name": f"API测试版本 - {timestamp}",
            "content": "这是一个通过API创建的测试版本内容。\\n\\n测试变量: {test_variable}",
            "variables": {
                "test_variable": "测试变量值",
                "temperature": 0.5,
                "system_message": "这是测试版本的系统消息"
            },
            "change_notes": f"通过API测试脚本创建于 {datetime.now().isoformat()}",
            "created_by": "api_test_script"
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/rpg-memory-prompts/templates/{template_key}/versions",
                json=create_data
            ) as response:
                if response.status == 200:
                    version = await response.json()
                    print(f"   ✅ 版本创建成功: {version['version_number']}")
                    print(f"      版本ID: {version['id']}")
                    print(f"      状态: {version['status']}")
                    return version
                else:
                    print(f"   ❌ 创建版本失败: {response.status}")
                    text = await response.text()
                    print(f"      错误详情: {text}")
                    return None
        except Exception as e:
            print(f"   ❌ 创建版本异常: {e}")
            return None
    
    async def test_update_version(self, version_id: int):
        """测试更新版本"""
        print(f"\\n✏️ 测试更新版本 ID {version_id}...")
        
        # 创建更新数据
        update_data = {
            "version_name": f"已更新的测试版本 - {datetime.now().strftime('%H:%M:%S')}",
            "content": "这是通过API更新的测试版本内容。\\n\\n更新时间: {update_time}\\n测试变量: {test_variable}",
            "variables": {
                "test_variable": "更新后的测试变量值",
                "update_time": datetime.now().isoformat(),
                "temperature": 0.3,
                "system_message": "这是更新后的系统消息"
            },
            "change_notes": f"通过API测试脚本更新于 {datetime.now().isoformat()}"
        }
        
        try:
            async with self.session.put(
                f"{self.base_url}/api/rpg-memory-prompts/versions/{version_id}",
                json=update_data
            ) as response:
                if response.status == 200:
                    version = await response.json()
                    print(f"   ✅ 版本更新成功: {version['version_number']}")
                    print(f"      新名称: {version['version_name']}")
                    return version
                else:
                    print(f"   ❌ 更新版本失败: {response.status}")
                    text = await response.text()
                    print(f"      错误详情: {text}")
                    return None
        except Exception as e:
            print(f"   ❌ 更新版本异常: {e}")
            return None
    
    async def test_get_variables(self, template_key: str):
        """测试获取模板变量配置"""
        print(f"\\n⚙️ 测试获取模板 '{template_key}' 的变量配置...")
        
        try:
            async with self.session.get(f"{self.base_url}/api/rpg-memory-prompts/templates/{template_key}/variables") as response:
                if response.status == 200:
                    var_config = await response.json()
                    print(f"   ✅ 变量配置获取成功:")
                    print(f"      变量数量: {len(var_config['variables'])}")
                    for var_name, var_value in var_config['variables'].items():
                        desc = var_config['variable_descriptions'].get(var_name, '无描述')
                        print(f"      • {var_name}: {var_value} ({desc})")
                    return var_config
                else:
                    print(f"   ❌ 获取变量配置失败: {response.status}")
                    return None
        except Exception as e:
            print(f"   ❌ 获取变量配置异常: {e}")
            return None
    
    async def test_delete_version(self, version_id: int):
        """测试删除版本"""
        print(f"\\n🗑️ 测试删除版本 ID {version_id}...")
        
        try:
            async with self.session.delete(f"{self.base_url}/api/rpg-memory-prompts/versions/{version_id}") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 版本删除成功: {result['message']}")
                    return True
                else:
                    print(f"   ❌ 删除版本失败: {response.status}")
                    text = await response.text()
                    print(f"      错误详情: {text}")
                    return False
        except Exception as e:
            print(f"   ❌ 删除版本异常: {e}")
            return False
    
    async def test_all_current_versions(self):
        """测试获取所有当前版本概览"""
        print("\\n📊 测试获取所有当前版本概览...")
        
        try:
            async with self.session.get(f"{self.base_url}/api/rpg-memory-prompts/all-current-versions") as response:
                if response.status == 200:
                    overview = await response.json()
                    print(f"   ✅ 成功获取 {overview['total_templates']} 个模板的当前版本:")
                    for version in overview['current_versions']:
                        print(f"      • {version['template_key']}: v{version['version_number']} ({version['status']})")
                    return overview
                else:
                    print(f"   ❌ 获取版本概览失败: {response.status}")
                    return None
        except Exception as e:
            print(f"   ❌ 获取版本概览异常: {e}")
            return None
    
    async def test_clear_cache(self):
        """测试清理缓存"""
        print("\\n🧹 测试清理LLM缓存...")
        
        try:
            async with self.session.post(f"{self.base_url}/api/rpg-memory-prompts/clear-cache") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 缓存清理请求成功: {result['message']}")
                    return True
                else:
                    print(f"   ❌ 清理缓存失败: {response.status}")
                    return False
        except Exception as e:
            print(f"   ❌ 清理缓存异常: {e}")
            return False

async def run_comprehensive_test():
    """运行综合API测试"""
    print("🚀 开始RPG记忆系统API综合测试\\n")
    
    async with RPGMemoryAPITester() as tester:
        # 1. 健康检查
        health_ok = await tester.test_health_check()
        if not health_ok:
            print("❌ 健康检查失败，停止测试")
            return False
        
        # 2. 获取所有模板
        templates = await tester.test_get_templates()
        if not templates:
            print("❌ 无法获取模板列表，停止测试")
            return False
        
        # 选择第一个模板进行详细测试
        test_template = templates[0]
        template_key = test_template['template_key']
        
        # 3. 获取模板详情
        await tester.test_get_template_detail(template_key)
        
        # 4. 获取版本列表
        await tester.test_get_versions(template_key)
        
        # 5. 获取当前版本
        await tester.test_get_current_version(template_key)
        
        # 6. 获取变量配置
        await tester.test_get_variables(template_key)
        
        # 7. 创建新版本
        new_version = await tester.test_create_version(template_key)
        if new_version:
            version_id = new_version['id']
            
            # 8. 更新版本
            await tester.test_update_version(version_id)
            
            # 9. 删除测试版本（清理）
            await tester.test_delete_version(version_id)
        
        # 10. 获取所有当前版本概览
        await tester.test_all_current_versions()
        
        # 11. 清理缓存
        await tester.test_clear_cache()
    
    print("\\n🎉 RPG记忆系统API测试完成！")
    return True

if __name__ == "__main__":
    # 检查是否提供了API服务器URL
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
        print(f"使用自定义API服务器URL: {base_url}")
    else:
        base_url = "http://localhost:8888"
        print(f"使用默认API服务器URL: {base_url}")
    
    # 运行测试
    try:
        success = asyncio.run(run_comprehensive_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\\n💥 测试运行异常: {e}")
        sys.exit(1)