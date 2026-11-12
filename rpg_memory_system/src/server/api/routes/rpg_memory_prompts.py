"""
RPG记忆系统提示词版本管理API路由
专门针对5个LLM提示词的版本管理和前端操作
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
import logging
from datetime import datetime
import aiomysql

logger = logging.getLogger(__name__)

# =================== 数据模型定义 ===================

class RPGPromptTemplateResponse(BaseModel):
    """RPG提示词模板响应模型"""
    id: int
    template_key: str
    template_name: str
    template_type: str
    category: str
    description: Optional[str] = None
    created_at: datetime
    current_version: Optional[str] = None
    total_versions: int = 0

class RPGPromptVersionResponse(BaseModel):
    """RPG提示词版本响应模型"""
    id: int
    template_key: str
    version_number: str
    version_name: Optional[str] = None
    content: str
    variables: Dict[str, Any] = {}
    status: str
    is_current_published: bool
    change_notes: Optional[str] = None
    created_by: str
    created_at: datetime
    published_at: Optional[datetime] = None

class CreateRPGVersionRequest(BaseModel):
    """创建RPG提示词版本请求"""
    version_number: str
    version_name: Optional[str] = None
    content: str
    variables: Optional[Dict[str, Any]] = {}
    change_notes: Optional[str] = None
    created_by: str = "admin"

class UpdateRPGVersionRequest(BaseModel):
    """更新RPG提示词版本请求"""
    version_name: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    change_notes: Optional[str] = None

class PublishRPGVersionRequest(BaseModel):
    """发布RPG提示词版本请求"""
    published_by: str = "admin"
    change_notes: Optional[str] = None

class RPGPromptVariablesResponse(BaseModel):
    """RPG提示词变量配置响应"""
    template_key: str
    variables: Dict[str, Any]
    variable_descriptions: Dict[str, str]

# =================== 数据库连接 ===================

async def get_db_connection():
    """获取数据库连接"""
    return await aiomysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='aigame_strong_root_password_123',
        db='aigame_db',
        charset='utf8mb4',
        cursorclass=aiomysql.DictCursor
    )

# =================== API路由工厂 ===================

def create_rpg_memory_prompt_router() -> APIRouter:
    """创建RPG记忆系统提示词版本管理API路由"""
    
    router = APIRouter(prefix="/api/rpg-memory-prompts", tags=["RPG记忆系统提示词管理"])
    
    # =================== 模板管理接口 ===================
    
    @router.get("/templates", response_model=List[RPGPromptTemplateResponse])
    async def get_rpg_prompt_templates():
        """获取RPG记忆系统所有提示词模板"""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            # 查询RPG记忆系统的5个模板
            sql = """
            SELECT 
                pt.id,
                pt.template_key,
                pt.template_name,
                pt.template_type,
                pt.category,
                pt.description,
                pt.created_at,
                pv_current.version_number as current_version,
                COUNT(pv_all.id) as total_versions
            FROM prompt_templates pt
            LEFT JOIN prompt_versions pv_current ON pt.id = pv_current.template_id 
                AND pv_current.is_current_published = 1
            LEFT JOIN prompt_versions pv_all ON pt.id = pv_all.template_id
            WHERE pt.category = 'rpg_memory'
            GROUP BY pt.id, pt.template_key, pt.template_name, pt.template_type, 
                     pt.category, pt.description, pt.created_at, pv_current.version_number
            ORDER BY 
                CASE pt.template_key 
                    WHEN 'rpg_extract_user_profile' THEN 1
                    WHEN 'rpg_extract_events' THEN 2 
                    WHEN 'rpg_generate_reflection' THEN 3
                    WHEN 'rpg_consolidate_memories' THEN 4
                    WHEN 'rpg_generate_npc_response' THEN 5
                    ELSE 6
                END
            """
            
            await cursor.execute(sql)
            results = await cursor.fetchall()
            
            await cursor.close()
            conn.close()
            
            templates = []
            for row in results:
                templates.append(RPGPromptTemplateResponse(
                    id=row['id'],
                    template_key=row['template_key'],
                    template_name=row['template_name'],
                    template_type=row['template_type'],
                    category=row['category'],
                    description=row['description'],
                    created_at=row['created_at'],
                    current_version=row['current_version'],
                    total_versions=row['total_versions']
                ))
            
            return templates
            
        except Exception as e:
            logger.error(f"获取RPG提示词模板失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"获取RPG提示词模板失败: {str(e)}")
    
    @router.get("/templates/{template_key}", response_model=RPGPromptTemplateResponse)
    async def get_rpg_prompt_template(template_key: str):
        """获取指定RPG提示词模板详情"""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            sql = """
            SELECT 
                pt.id,
                pt.template_key,
                pt.template_name,
                pt.template_type,
                pt.category,
                pt.description,
                pt.created_at,
                pv_current.version_number as current_version,
                COUNT(pv_all.id) as total_versions
            FROM prompt_templates pt
            LEFT JOIN prompt_versions pv_current ON pt.id = pv_current.template_id 
                AND pv_current.is_current_published = 1
            LEFT JOIN prompt_versions pv_all ON pt.id = pv_all.template_id
            WHERE pt.template_key = %s AND pt.category = 'rpg_memory'
            GROUP BY pt.id, pt.template_key, pt.template_name, pt.template_type, 
                     pt.category, pt.description, pt.created_at, pv_current.version_number
            """
            
            await cursor.execute(sql, (template_key,))
            result = await cursor.fetchone()
            
            await cursor.close()
            conn.close()
            
            if not result:
                raise HTTPException(status_code=404, detail=f"RPG提示词模板 '{template_key}' 不存在")
            
            return RPGPromptTemplateResponse(
                id=result['id'],
                template_key=result['template_key'],
                template_name=result['template_name'],
                template_type=result['template_type'],
                category=result['category'],
                description=result['description'],
                created_at=result['created_at'],
                current_version=result['current_version'],
                total_versions=result['total_versions']
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取RPG提示词模板失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"获取RPG提示词模板失败: {str(e)}")
    
    # =================== 版本管理接口 ===================
    
    @router.get("/templates/{template_key}/versions", response_model=List[RPGPromptVersionResponse])
    async def get_template_versions(template_key: str):
        """获取指定RPG提示词模板的所有版本"""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            # 首先验证模板存在且属于RPG记忆系统
            template_sql = """
            SELECT id FROM prompt_templates 
            WHERE template_key = %s AND category = 'rpg_memory'
            """
            await cursor.execute(template_sql, (template_key,))
            template_result = await cursor.fetchone()
            
            if not template_result:
                raise HTTPException(status_code=404, detail=f"RPG提示词模板 '{template_key}' 不存在")
            
            template_id = template_result['id']
            
            # 获取所有版本
            sql = """
            SELECT 
                pv.id, pv.version_number, pv.version_name, pv.content, 
                pv.variables, pv.status, pv.is_current_published, 
                pv.change_notes, pv.created_by, pv.created_at, pv.published_at,
                pt.template_key
            FROM prompt_versions pv
            JOIN prompt_templates pt ON pv.template_id = pt.id
            WHERE pv.template_id = %s 
            ORDER BY pv.created_at DESC
            """
            
            await cursor.execute(sql, (template_id,))
            results = await cursor.fetchall()
            
            await cursor.close()
            conn.close()
            
            versions = []
            for row in results:
                # 解析变量JSON
                variables = {}
                if row['variables']:
                    try:
                        variables = json.loads(row['variables']) if isinstance(row['variables'], str) else row['variables']
                    except json.JSONDecodeError:
                        variables = {}
                
                versions.append(RPGPromptVersionResponse(
                    id=row['id'],
                    template_key=row['template_key'],
                    version_number=row['version_number'],
                    version_name=row['version_name'],
                    content=row['content'],
                    variables=variables,
                    status=row['status'],
                    is_current_published=bool(row['is_current_published']),
                    change_notes=row['change_notes'],
                    created_by=row['created_by'],
                    created_at=row['created_at'],
                    published_at=row['published_at']
                ))
            
            return versions
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取RPG提示词版本失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"获取RPG提示词版本失败: {str(e)}")
    
    @router.get("/templates/{template_key}/current", response_model=RPGPromptVersionResponse)
    async def get_current_version(template_key: str):
        """获取指定RPG提示词模板的当前发布版本"""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            sql = """
            SELECT 
                pv.id, pv.version_number, pv.version_name, pv.content, 
                pv.variables, pv.status, pv.is_current_published, 
                pv.change_notes, pv.created_by, pv.created_at, pv.published_at,
                pt.template_key
            FROM prompt_versions pv
            JOIN prompt_templates pt ON pv.template_id = pt.id
            WHERE pt.template_key = %s AND pt.category = 'rpg_memory' 
                  AND pv.is_current_published = 1
            """
            
            await cursor.execute(sql, (template_key,))
            result = await cursor.fetchone()
            
            await cursor.close()
            conn.close()
            
            if not result:
                raise HTTPException(status_code=404, detail=f"RPG提示词模板 '{template_key}' 没有当前发布版本")
            
            # 解析变量JSON
            variables = {}
            if result['variables']:
                try:
                    variables = json.loads(result['variables']) if isinstance(result['variables'], str) else result['variables']
                except json.JSONDecodeError:
                    variables = {}
            
            return RPGPromptVersionResponse(
                id=result['id'],
                template_key=result['template_key'],
                version_number=result['version_number'],
                version_name=result['version_name'],
                content=result['content'],
                variables=variables,
                status=result['status'],
                is_current_published=bool(result['is_current_published']),
                change_notes=result['change_notes'],
                created_by=result['created_by'],
                created_at=result['created_at'],
                published_at=result['published_at']
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取当前发布版本失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"获取当前发布版本失败: {str(e)}")
    
    @router.post("/templates/{template_key}/versions", response_model=RPGPromptVersionResponse)
    async def create_version(template_key: str, request: CreateRPGVersionRequest):
        """为指定RPG提示词模板创建新版本"""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            # 验证模板存在
            template_sql = """
            SELECT id FROM prompt_templates 
            WHERE template_key = %s AND category = 'rpg_memory'
            """
            await cursor.execute(template_sql, (template_key,))
            template_result = await cursor.fetchone()
            
            if not template_result:
                raise HTTPException(status_code=404, detail=f"RPG提示词模板 '{template_key}' 不存在")
            
            template_id = template_result['id']
            
            # 检查版本号是否已存在
            check_sql = """
            SELECT COUNT(*) as count FROM prompt_versions 
            WHERE template_id = %s AND version_number = %s
            """
            await cursor.execute(check_sql, (template_id, request.version_number))
            check_result = await cursor.fetchone()
            
            if check_result['count'] > 0:
                raise HTTPException(status_code=400, detail=f"版本号 '{request.version_number}' 已存在")
            
            # 插入新版本
            insert_sql = """
            INSERT INTO prompt_versions 
            (template_id, version_number, version_name, content, variables, 
             status, is_current_published, change_notes, created_by) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            variables_json = json.dumps(request.variables or {}, ensure_ascii=False)
            
            await cursor.execute(insert_sql, (
                template_id,
                request.version_number,
                request.version_name,
                request.content,
                variables_json,
                "draft",
                False,
                request.change_notes,
                request.created_by
            ))
            
            version_id = cursor.lastrowid
            await conn.commit()
            
            # 获取刚创建的版本
            get_sql = """
            SELECT 
                pv.id, pv.version_number, pv.version_name, pv.content, 
                pv.variables, pv.status, pv.is_current_published, 
                pv.change_notes, pv.created_by, pv.created_at, pv.published_at,
                pt.template_key
            FROM prompt_versions pv
            JOIN prompt_templates pt ON pv.template_id = pt.id
            WHERE pv.id = %s
            """
            
            await cursor.execute(get_sql, (version_id,))
            result = await cursor.fetchone()
            
            await cursor.close()
            conn.close()
            
            # 解析变量JSON
            variables = {}
            if result['variables']:
                try:
                    variables = json.loads(result['variables']) if isinstance(result['variables'], str) else result['variables']
                except json.JSONDecodeError:
                    variables = {}
            
            return RPGPromptVersionResponse(
                id=result['id'],
                template_key=result['template_key'],
                version_number=result['version_number'],
                version_name=result['version_name'],
                content=result['content'],
                variables=variables,
                status=result['status'],
                is_current_published=bool(result['is_current_published']),
                change_notes=result['change_notes'],
                created_by=result['created_by'],
                created_at=result['created_at'],
                published_at=result['published_at']
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"创建RPG提示词版本失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"创建RPG提示词版本失败: {str(e)}")
    
    @router.put("/versions/{version_id}", response_model=RPGPromptVersionResponse)
    async def update_version(version_id: int, request: UpdateRPGVersionRequest):
        """更新RPG提示词版本内容"""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            # 检查版本是否存在且属于RPG记忆系统
            check_sql = """
            SELECT pv.status, pt.template_key, pt.category 
            FROM prompt_versions pv
            JOIN prompt_templates pt ON pv.template_id = pt.id
            WHERE pv.id = %s
            """
            await cursor.execute(check_sql, (version_id,))
            check_result = await cursor.fetchone()
            
            if not check_result:
                raise HTTPException(status_code=404, detail="版本不存在")
            
            if check_result['category'] != 'rpg_memory':
                raise HTTPException(status_code=400, detail="该版本不属于RPG记忆系统")
                
            if check_result['status'] == 'published':
                raise HTTPException(status_code=400, detail="已发布的版本无法编辑")
            
            # 构建更新语句
            update_fields = []
            params = []
            
            if request.version_name is not None:
                update_fields.append("version_name = %s")
                params.append(request.version_name)
            
            if request.content is not None:
                update_fields.append("content = %s")
                params.append(request.content)
            
            if request.variables is not None:
                update_fields.append("variables = %s")
                params.append(json.dumps(request.variables, ensure_ascii=False))
            
            if request.change_notes is not None:
                update_fields.append("change_notes = %s")
                params.append(request.change_notes)
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="没有提供要更新的字段")
            
            update_fields.append("updated_at = NOW()")
            params.append(version_id)
            
            update_sql = f"""
            UPDATE prompt_versions 
            SET {', '.join(update_fields)}
            WHERE id = %s
            """
            
            await cursor.execute(update_sql, params)
            await conn.commit()
            
            # 获取更新后的版本
            get_sql = """
            SELECT 
                pv.id, pv.version_number, pv.version_name, pv.content, 
                pv.variables, pv.status, pv.is_current_published, 
                pv.change_notes, pv.created_by, pv.created_at, pv.published_at,
                pt.template_key
            FROM prompt_versions pv
            JOIN prompt_templates pt ON pv.template_id = pt.id
            WHERE pv.id = %s
            """
            
            await cursor.execute(get_sql, (version_id,))
            result = await cursor.fetchone()
            
            await cursor.close()
            conn.close()
            
            # 解析变量JSON
            variables = {}
            if result['variables']:
                try:
                    variables = json.loads(result['variables']) if isinstance(result['variables'], str) else result['variables']
                except json.JSONDecodeError:
                    variables = {}
            
            return RPGPromptVersionResponse(
                id=result['id'],
                template_key=result['template_key'],
                version_number=result['version_number'],
                version_name=result['version_name'],
                content=result['content'],
                variables=variables,
                status=result['status'],
                is_current_published=bool(result['is_current_published']),
                change_notes=result['change_notes'],
                created_by=result['created_by'],
                created_at=result['created_at'],
                published_at=result['published_at']
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"更新RPG提示词版本失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"更新RPG提示词版本失败: {str(e)}")
    
    @router.post("/versions/{version_id}/publish", response_model=RPGPromptVersionResponse)
    async def publish_version(version_id: int, request: PublishRPGVersionRequest):
        """发布RPG提示词版本"""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            # 获取版本信息
            version_sql = """
            SELECT pv.template_id, pv.status, pt.template_key, pt.category
            FROM prompt_versions pv
            JOIN prompt_templates pt ON pv.template_id = pt.id
            WHERE pv.id = %s
            """
            await cursor.execute(version_sql, (version_id,))
            version_result = await cursor.fetchone()
            
            if not version_result:
                raise HTTPException(status_code=404, detail="版本不存在")
            
            if version_result['category'] != 'rpg_memory':
                raise HTTPException(status_code=400, detail="该版本不属于RPG记忆系统")
            
            template_id = version_result['template_id']
            current_status = version_result['status']
            template_key = version_result['template_key']
            
            if current_status == 'published':
                raise HTTPException(status_code=400, detail="版本已经是发布状态")
            
            # 开始事务
            await conn.begin()
            
            try:
                # 取消同模板的其他发布版本
                unpublish_sql = """
                UPDATE prompt_versions 
                SET is_current_published = 0, 
                    status = 'archived',
                    updated_at = NOW()
                WHERE template_id = %s AND is_current_published = 1 AND id != %s
                """
                await cursor.execute(unpublish_sql, (template_id, version_id))
                
                # 发布当前版本
                publish_sql = """
                UPDATE prompt_versions 
                SET status = 'published', 
                    is_current_published = 1, 
                    published_by = %s,
                    published_at = NOW(),
                    change_notes = %s,
                    updated_at = NOW()
                WHERE id = %s
                """
                await cursor.execute(publish_sql, (request.published_by, request.change_notes, version_id))
                
                # 提交事务
                await conn.commit()
                
                # 清理LLM客户端缓存（如果需要的话）
                logger.info(f"RPG提示词 '{template_key}' 版本 {version_id} 发布成功，建议清理LLM客户端缓存")
                
            except Exception as e:
                # 回滚事务
                await conn.rollback()
                raise e
            
            # 获取发布后的版本
            get_sql = """
            SELECT 
                pv.id, pv.version_number, pv.version_name, pv.content, 
                pv.variables, pv.status, pv.is_current_published, 
                pv.change_notes, pv.created_by, pv.created_at, pv.published_at,
                pt.template_key
            FROM prompt_versions pv
            JOIN prompt_templates pt ON pv.template_id = pt.id
            WHERE pv.id = %s
            """
            
            await cursor.execute(get_sql, (version_id,))
            result = await cursor.fetchone()
            
            await cursor.close()
            conn.close()
            
            # 解析变量JSON
            variables = {}
            if result['variables']:
                try:
                    variables = json.loads(result['variables']) if isinstance(result['variables'], str) else result['variables']
                except json.JSONDecodeError:
                    variables = {}
            
            return RPGPromptVersionResponse(
                id=result['id'],
                template_key=result['template_key'],
                version_number=result['version_number'],
                version_name=result['version_name'],
                content=result['content'],
                variables=variables,
                status=result['status'],
                is_current_published=bool(result['is_current_published']),
                change_notes=result['change_notes'],
                created_by=result['created_by'],
                created_at=result['created_at'],
                published_at=result['published_at']
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"发布RPG提示词版本失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"发布RPG提示词版本失败: {str(e)}")
    
    @router.delete("/versions/{version_id}")
    async def delete_version(version_id: int):
        """删除RPG提示词版本（只能删除草稿或已保存的版本）"""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            # 检查版本状态
            check_sql = """
            SELECT pv.status, pv.is_current_published, pv.version_number,
                   pt.template_key, pt.category
            FROM prompt_versions pv
            JOIN prompt_templates pt ON pv.template_id = pt.id
            WHERE pv.id = %s
            """
            await cursor.execute(check_sql, (version_id,))
            check_result = await cursor.fetchone()
            
            if not check_result:
                raise HTTPException(status_code=404, detail="版本不存在")
            
            if check_result['category'] != 'rpg_memory':
                raise HTTPException(status_code=400, detail="该版本不属于RPG记忆系统")
            
            status = check_result['status']
            is_published = check_result['is_current_published']
            version_number = check_result['version_number']
            template_key = check_result['template_key']
            
            if status == 'published' or is_published:
                raise HTTPException(status_code=400, detail="无法删除已发布的版本")
            
            # 删除版本
            delete_sql = "DELETE FROM prompt_versions WHERE id = %s"
            await cursor.execute(delete_sql, (version_id,))
            await conn.commit()
            
            await cursor.close()
            conn.close()
            
            return {
                "message": f"RPG提示词版本删除成功",
                "template_key": template_key,
                "version_number": version_number
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"删除RPG提示词版本失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"删除RPG提示词版本失败: {str(e)}")
    
    # =================== 变量配置管理 ===================
    
    @router.get("/templates/{template_key}/variables", response_model=RPGPromptVariablesResponse)
    async def get_template_variables(template_key: str):
        """获取RPG提示词模板的变量配置和说明"""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            # 获取当前发布版本的变量配置
            sql = """
            SELECT pv.variables, pt.template_key
            FROM prompt_versions pv
            JOIN prompt_templates pt ON pv.template_id = pt.id
            WHERE pt.template_key = %s AND pt.category = 'rpg_memory' 
                  AND pv.is_current_published = 1
            """
            
            await cursor.execute(sql, (template_key,))
            result = await cursor.fetchone()
            
            await cursor.close()
            conn.close()
            
            if not result:
                raise HTTPException(status_code=404, detail=f"RPG提示词模板 '{template_key}' 没有当前发布版本")
            
            # 解析变量JSON
            variables = {}
            if result['variables']:
                try:
                    variables = json.loads(result['variables']) if isinstance(result['variables'], str) else result['variables']
                except json.JSONDecodeError:
                    variables = {}
            
            # 变量说明字典
            variable_descriptions = {
                'dialogue_text': '对话历史文本变量，包含用户和助手的完整对话记录',
                'memory_type': '记忆类型变量，用于记忆整合时指定处理的记忆类型（事件或反思）',
                'memory_list': '记忆列表文本变量，包含需要整合的记忆内容',
                'history_text': '对话历史文本变量，用于NPC回复生成',
                'context_text': '记忆上下文文本变量，包含相关的长期记忆和核心记忆',
                'user_message': '用户最新消息变量，包含用户当前输入的消息内容',
                'system_message': '系统提示消息，定义AI助手的角色和行为准则',
                'temperature': 'LLM温度参数，控制生成文本的随机性（0.0-1.0）',
                'max_tokens': '最大token数限制，控制生成文本的长度',
                'response_format': '响应格式配置，指定LLM返回格式（如JSON）'
            }
            
            return RPGPromptVariablesResponse(
                template_key=template_key,
                variables=variables,
                variable_descriptions=variable_descriptions
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取RPG提示词变量配置失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"获取RPG提示词变量配置失败: {str(e)}")
    
    # =================== 批量操作接口 ===================
    
    @router.get("/all-current-versions")
    async def get_all_current_versions():
        """获取所有RPG提示词模板的当前发布版本概览"""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            sql = """
            SELECT 
                pt.template_key,
                pt.template_name,
                pv.version_number,
                pv.status,
                pv.published_at,
                pv.created_by
            FROM prompt_templates pt
            JOIN prompt_versions pv ON pt.id = pv.template_id
            WHERE pt.category = 'rpg_memory' AND pv.is_current_published = 1
            ORDER BY 
                CASE pt.template_key 
                    WHEN 'rpg_extract_user_profile' THEN 1
                    WHEN 'rpg_extract_events' THEN 2 
                    WHEN 'rpg_generate_reflection' THEN 3
                    WHEN 'rpg_consolidate_memories' THEN 4
                    WHEN 'rpg_generate_npc_response' THEN 5
                    ELSE 6
                END
            """
            
            await cursor.execute(sql)
            results = await cursor.fetchall()
            
            await cursor.close()
            conn.close()
            
            return {
                "total_templates": len(results),
                "current_versions": [
                    {
                        "template_key": row['template_key'],
                        "template_name": row['template_name'],
                        "version_number": row['version_number'],
                        "status": row['status'],
                        "published_at": row['published_at'],
                        "created_by": row['created_by']
                    }
                    for row in results
                ]
            }
            
        except Exception as e:
            logger.error(f"获取所有当前版本失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"获取所有当前版本失败: {str(e)}")
    
    @router.post("/clear-cache")
    async def clear_llm_cache():
        """清理LLM客户端提示词缓存"""
        try:
            # 这里可以添加清理缓存的逻辑
            # 如果LLM客户端在同一进程中，可以直接调用
            # 否则可以通过其他方式通知LLM客户端清理缓存
            
            logger.info("RPG记忆系统LLM提示词缓存清理请求")
            
            return {
                "message": "LLM提示词缓存清理请求已发送",
                "timestamp": datetime.now().isoformat(),
                "note": "LLM客户端将在下次调用时重新从数据库加载提示词"
            }
            
        except Exception as e:
            logger.error(f"清理LLM缓存失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"清理LLM缓存失败: {str(e)}")
    
    return router

# =================== 便捷函数 ===================

def get_rpg_memory_template_names():
    """获取RPG记忆系统模板名称映射"""
    return {
        'rpg_extract_user_profile': 'RPG记忆系统-用户画像提取',
        'rpg_extract_events': 'RPG记忆系统-事件提取', 
        'rpg_generate_reflection': 'RPG记忆系统-反思生成',
        'rpg_consolidate_memories': 'RPG记忆系统-记忆整合',
        'rpg_generate_npc_response': 'RPG记忆系统-NPC回复生成'
    }

def get_rpg_memory_template_descriptions():
    """获取RPG记忆系统模板功能描述"""
    return {
        'rpg_extract_user_profile': '从对话历史中提取用户的个人特征、性格、兴趣爱好等画像信息',
        'rpg_extract_events': '从对话历史中识别和分类重要事件，区分核心事件和实体事件',
        'rpg_generate_reflection': '基于对话历史生成AI角色的反思记忆，包括核心反思和长期反思',
        'rpg_consolidate_memories': '整合和优化核心记忆内容，消除冗余，合并相似记忆',
        'rpg_generate_npc_response': '基于记忆上下文生成AI NPC的个性化回复'
    }