#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆合并功能专项测试
测试240轮对话触发核心记忆合并功能
"""

import asyncio
import sys
import os
from typing import Dict, Any

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
api_path = os.path.join(current_dir, 'src', 'server', 'api')
sys.path.insert(0, src_path)
sys.path.insert(0, api_path)

# 设置环境变量以支持相对导入
os.environ['PYTHONPATH'] = api_path

# 直接导入模块
from server.api.memory_interface import (
    initialize_user_memory,
    add_dialogue_to_memory,
    get_memory_context_for_chat
)

class MemoryConsolidationTest:
    def __init__(self):
        self.user_id = "test_user_consolidation121"
        self.project_id = "test_project_consolidation121"
        
    def print_separator(self, title: str):
        """打印分隔符"""
        print("\n" + "="*80)
        print(f"[{title}]")
        print("="*80)
    
    async def test_memory_consolidation(self):
        """测试记忆合并功能"""
        self.print_separator("记忆合并功能测试")
        
        try:
            # 1. 初始化用户
            print("[STEP 1] 初始化用户...")
            init_result = await initialize_user_memory(self.user_id, self.project_id)
            if init_result.get('status') != 'success':
                print(f"[ERROR] 用户初始化失败: {init_result.get('message')}")
                return False
            print("[OK] 用户初始化成功")
            
            # 2. 添加240+轮对话以触发记忆合并
            print("\n[STEP 2] 开始添加对话，目标: 触发240轮记忆合并...")
            
            dialogue_count = 0
            consolidation_triggered = False
            
            # 使用test_memory_interface.py中的250轮对话数据
            test_dialogues = [
                ("user", "你好，我是一个新的冒险者"),
                ("assistant", "欢迎来到这个奇幻世界！我是艾莉亚，很高兴认识你。"),
                ("user", "这个世界有什么有趣的地方吗？"),
                ("assistant", "这里有古老的魔法森林、神秘的地下城和传说中的龙族。你想先去哪里探险呢？"),
                ("user", "我想了解一下魔法的历史"),
                ("assistant", "魔法的历史可以追溯到远古时代，当时的法师们发现了操控元素的秘密。"),
                ("user", "那魔法森林里有什么危险吗？"),
                ("assistant", "魔法森林中栖息着各种魔法生物，有友善的精灵，也有危险的魔兽。"),
                ("user", "我应该准备什么装备？"),
                ("assistant", "建议你准备一把好剑、一些治疗药水，还有防护法袍。"),
                ("user", "治疗药水在哪里可以买到？"),
                ("assistant", "城镇的炼金术师那里有卖，或者你也可以学习制作。"),
                ("user", "学习炼金术需要什么条件？"),
                ("assistant", "需要一定的魔法天赋和耐心，还要收集各种草药材料。"),
                ("user", "草药在森林里能找到吗？"),
                ("assistant", "是的，但要小心那些有毒的植物，建议带上识别指南。"),
                ("user", "有没有经验丰富的向导？"),
                ("assistant", "老猎人马克斯很熟悉森林，不过他的费用不便宜。"),
                ("user", "大概需要多少金币？"),
                ("assistant", "通常是每天50金币，包括他的保护和向导服务。"),
                ("user", "我现在只有30金币怎么办？"),
                ("assistant", "你可以先做一些简单的任务赚钱，比如帮商人运货。"),
                ("user", "什么样的任务比较安全？"),
                ("assistant", "城内的清洁工作、信件投递，或者帮助铁匠整理工具。"),
                ("user", "铁匠那里有什么好装备吗？"),
                ("assistant", "有一些基础的剑和盔甲，质量不错但价格公道。"),
                ("user", "我想先看看装备再决定"),
                ("assistant", "好主意，铁匠铺就在市场广场旁边，很容易找到。"),
                ("user", "市场上还有什么其他有用的东西？"),
                ("assistant", "有食物、绳索、火把等冒险必需品，还有一些魔法卷轴。"),
                ("user", "魔法卷轴是做什么用的？"),
                ("assistant", "可以释放一次性的魔法效果，即使不会魔法的人也能使用。"),
                ("user", "有推荐的卷轴类型吗？"),
                ("assistant", "治疗卷轴和照明卷轴对新手很有用，还有传送卷轴以防紧急情况。"),
                ("user", "传送卷轴能传送到哪里？"),
                ("assistant", "通常只能传送到你去过的安全地点，比如城镇或者旅店。"),
                ("user", "如果在森林里迷路了怎么办？"),
                ("assistant", "可以寻找河流，顺流而下通常能找到人类聚居地。"),
                ("user", "森林里的河水能直接喝吗？"),
                ("assistant", "最好先用净化药剂处理，或者煮沸后再喝。"),
                ("user", "净化药剂也是炼金术制品吗？"),
                ("assistant", "是的，不过也有一些天然的净化植物可以使用。"),
                ("user", "你能教我识别这些植物吗？"),
                ("assistant", "银叶草有净化作用，叶子呈银白色，通常长在清澈的水边。"),
                ("user", "还有其他有用的植物吗？"),
                ("assistant", "红果藤的果实可以快速恢复体力，但要避免绿色的未成熟果实。"),
                ("user", "如果不小心吃了有毒的东西怎么办？"),
                ("assistant", "立即服用解毒剂，如果没有就尽快找到牧师或治疗师。"),
                ("user", "牧师通常在哪里能找到？"),
                ("assistant", "每个城镇都有神庙，那里会有牧师提供治疗服务。"),
                ("user", "神庙的治疗需要付费吗？"),
                ("assistant", "基础治疗通常是免费的，但复杂的治疗可能需要捐献。"),
                ("user", "什么情况下需要复杂治疗？"),
                ("assistant", "严重的诅咒、疾病，或者复活术等高级神术。"),
                ("user", "诅咒是怎么产生的？"),
                ("assistant", "通常来自邪恶法师、被诅咒的物品，或者触怒了某些魔法生物。"),
                ("user", "怎么避免被诅咒？"),
                ("assistant", "不要随意触碰未知的魔法物品，保持对陌生法师的警惕。"),
                ("user", "如果遇到邪恶法师该怎么办？"),
                ("assistant", "如果实力不够就尽快逃跑，或者寻求当地守卫的帮助。"),
                ("user", "守卫的实力如何？"),
                ("assistant", "城镇守卫通常训练有素，配备精良装备，能对付一般威胁。"),
                ("user", "我什么时候能达到守卫的水平？"),
                ("assistant", "通过不断的训练和实战经验，大概需要几个月到一年时间。"),
                ("user", "有什么好的训练方法吗？"),
                ("assistant", "可以在训练场练习剑术，或者参加冒险者公会的任务。"),
                ("user", "冒险者公会是什么？"),
                ("assistant", "一个为冒险者提供任务和支持的组织，新手可以从简单任务开始。"),
                ("user", "加入公会需要什么条件？"),
                ("assistant", "通常只需要登记个人信息和通过基础的能力测试。"),
                ("user", "能力测试包括什么内容？"),
                ("assistant", "基本的战斗技能、体能测试，以及对冒险常识的了解。"),
                ("user", "如果测试失败了怎么办？"),
                ("assistant", "可以继续训练后重新测试，公会鼓励大家不断进步。"),
                ("user", "公会里的其他冒险者友善吗？"),
                ("assistant", "大多数都很友善，经验丰富的冒险者通常愿意指导新人。"),
                ("user", "我可以和他们组队吗？"),
                ("assistant", "当然可以，团队合作在冒险中非常重要，能提高成功率和安全性。"),
                ("user", "组队时如何分配收益？"),
                ("assistant", "通常按贡献度分配，或者事先约定分配方式，诚信很重要。"),
                ("user", "如果队友背叛了怎么办？"),
                ("assistant", "这种情况很少见，但如果发生可以向公会举报，他们会处理此类纠纷。"),
                ("user", "公会的声誉系统是怎样的？"),
                ("assistant", "根据完成任务的质量和数量来评级，声誉高的冒险者能接到更好的任务。"),
                ("user", "最高级别的冒险者有什么特权？"),
                ("assistant", "可以接受传奇级任务，获得稀有装备，甚至被贵族招募为私人护卫。"),
                ("user", "传奇级任务都有哪些类型？"),
                ("assistant", "包括屠龙任务、封印邪恶法师、寻找失落的神器等极其危险的挑战。"),
                ("user", "神器有什么特殊能力？"),
                ("assistant", "神器拥有强大的魔法力量，有些能控制天气，有些能复活死者。"),
                ("user", "复活死者不是很危险吗？"),
                ("assistant", "确实，滥用复活术可能会扰乱生死平衡，所以使用需要极其谨慎。"),
                ("user", "有什么限制吗？"),
                ("assistant", "复活术只能在死亡后短时间内使用，而且需要消耗巨大的魔法能量。"),
                ("user", "魔法能量是如何获得的？"),
                ("assistant", "通过冥想、魔法水晶充能，或者从魔法节点汲取能量。"),
                ("user", "魔法节点在哪里能找到？"),
                ("assistant", "通常在古老的遗迹、魔法森林深处，或者龙族的巢穴附近。"),
                ("user", "龙族友善吗？"),
                ("assistant", "这取决于龙的种类，金龙通常善良，而红龙则非常危险。"),
                ("user", "如何区分不同种类的龙？"),
                ("assistant", "主要看鳞片颜色和体型，金龙鳞片闪闪发光，红龙则散发着炽热的气息。"),
                ("user", "遇到红龙该怎么办？"),
                ("assistant", "立即逃跑是最明智的选择，除非你有传奇级的实力和装备。"),
                ("user", "传奇级装备从哪里获得？"),
                ("assistant", "通常是完成传奇任务的奖励，或者在古老的宝库中发现。"),
                ("user", "古老的宝库有什么危险？"),
                ("assistant", "充满了致命的陷阱、守护者，还有可能被诅咒。"),
                ("user", "陷阱都有哪些类型？"),
                ("assistant", "毒箭陷阱、落石陷阱、魔法封印，还有幻象迷宫等。"),
                ("user", "如何破解幻象迷宫？"),
                ("assistant", "需要强大的精神力和识破幻象的能力，或者使用真实之眼药剂。"),
                ("user", "真实之眼药剂怎么制作？"),
                ("assistant", "需要独角兽的角粉、精灵的眼泪和月光石粉末。"),
                ("user", "独角兽在哪里能找到？"),
                ("assistant", "它们生活在最纯净的森林深处，只有心地善良的人才能接近。"),
                ("user", "如何证明自己心地善良？"),
                ("assistant", "通过帮助他人、保护弱者的行为，独角兽能感知到你的内心。"),
                ("user", "精灵的眼泪又如何获得？"),
                ("assistant", "这需要与精灵建立深厚的友谊，让他们自愿分享。"),
                ("user", "精灵住在哪里？"),
                ("assistant", "在魔法森林的树屋中，他们的村落隐藏在古老的橡树之间。"),
                ("user", "如何找到精灵村落？"),
                ("assistant", "跟随萤火虫的光芒，它们会在夜晚指引善良的旅者。"),
                ("user", "萤火虫只在夜晚出现吗？"),
                ("assistant", "是的，而且只在月圆之夜最为活跃，那时它们的光芒最亮。"),
                ("user", "月圆之夜还有什么特殊之处？"),
                ("assistant", "魔法力量会增强，某些魔法生物也会变得更加活跃。"),
                ("user", "狼人也会在月圆之夜变身吗？"),
                ("assistant", "是的，狼人在满月时会失去理智，变得极其危险。"),
                ("user", "如何对付狼人？"),
                ("assistant", "银制武器最有效，或者等到天亮它们恢复人形。"),
                ("user", "银制武器很贵吗？"),
                ("assistant", "比普通武器贵很多，但对付不死生物和某些魔法生物必不可少。"),
                ("user", "不死生物都有哪些？"),
                ("assistant", "僵尸、骷髅、幽灵、吸血鬼等，它们都害怕圣水和阳光。"),
                ("user", "圣水从哪里获得？"),
                ("assistant", "神庙的牧师可以制作圣水，需要用特殊的仪式祝福普通水。"),
                ("user", "仪式需要多长时间？"),
                ("assistant", "通常需要一整夜的祈祷和冥想，在黎明时分完成。"),
                ("user", "黎明时分有什么特殊意义？"),
                ("assistant", "那是光明战胜黑暗的时刻，神圣力量最为纯净。"),
                ("user", "邪恶力量在什么时候最强？"),
                ("assistant", "午夜时分，特别是在新月之夜，黑暗魔法达到顶峰。"),
                ("user", "新月之夜要注意什么？"),
                ("assistant", "避免独自外出，邪恶法师和恶魔在这时最为活跃。"),
                ("user", "恶魔从哪里来？"),
                ("assistant", "它们来自地狱位面，通过邪恶仪式或破损的封印进入我们的世界。"),
                ("user", "如何修复破损的封印？"),
                ("assistant", "需要强大的法师团队合作，使用古老的封印法术。"),
                ("user", "封印法术很难学吗？"),
                ("assistant", "极其困难，需要数十年的学习和实践，还要有天赋。"),
                ("user", "魔法天赋如何测试？"),
                ("assistant", "通过魔法水晶的反应，有天赋的人能让水晶发光。"),
                ("user", "水晶不发光就没有天赋吗？"),
                ("assistant", "不一定，有些人的天赋需要特殊的触发条件才能觉醒。"),
                ("user", "什么样的触发条件？"),
                ("assistant", "生死危机、强烈的情感波动，或者接触到特殊的魔法物品。"),
                ("user", "魔法物品都有哪些类型？"),
                ("assistant", "法杖、魔法戒指、护身符、魔法书籍等，各有不同的功能。"),
                ("user", "魔法书籍记录什么内容？"),
                ("assistant", "法术公式、魔法理论、炼金配方，还有古老的传说。"),
                ("user", "古老的传说都讲什么？"),
                ("assistant", "创世神话、英雄史诗、失落的文明，还有预言。"),
                ("user", "预言准确吗？"),
                ("assistant", "有些预言确实应验了，但解读往往很困难，容易误解。"),
                ("user", "谁能正确解读预言？"),
                ("assistant", "通常是智慧极高的贤者、先知，或者拥有预言天赋的人。"),
                ("user", "先知住在哪里？"),
                ("assistant", "他们通常隐居在偏远的山洞或古老的神庙中。"),
                ("user", "如何找到先知？"),
                ("assistant", "这需要缘分，先知会在合适的时机主动出现。"),
                ("user", "什么是合适的时机？"),
                ("assistant", "当世界面临重大危机，或者有人真心寻求智慧指引时。"),
                ("user", "世界曾经面临过什么危机？"),
                ("assistant", "古代的魔神入侵、不死军团的崛起，还有元素失衡的灾难。"),
                ("user", "元素失衡会造成什么后果？"),
                ("assistant", "火元素过盛会引发干旱，水元素泛滥会导致洪水。"),
                ("user", "如何维持元素平衡？"),
                ("assistant", "需要元素法师的协调，还要保护好元素圣地。"),
                ("user", "元素圣地在哪里？"),
                ("assistant", "火之圣地在活火山中，水之圣地在深海底部。"),
                ("user", "普通人能到达这些地方吗？"),
                ("assistant", "非常困难，需要特殊的保护装备和强大的魔法支持。"),
                ("user", "保护装备包括什么？"),
                ("assistant", "抗火护甲、水下呼吸器、抗压法袍等专门的魔法装备。"),
                ("user", "这些装备如何制作？"),
                ("assistant", "需要稀有材料和高级工匠，制作过程极其复杂。"),
                ("user", "稀有材料从哪里获得？"),
                ("assistant", "龙鳞、凤凰羽毛、深海珍珠等，都需要冒险获取。"),
                ("user", "凤凰真的存在吗？"),
                ("assistant", "是的，它们是不死鸟，能够浴火重生，极其稀少。"),
                ("user", "凤凰住在哪里？"),
                ("assistant", "在最高的山峰上，那里接近太阳，火元素最为纯净。"),
                ("user", "如何接近凤凰？"),
                ("assistant", "需要证明你的纯洁之心，凤凰只信任真正善良的人。"),
                ("user", "深海珍珠有什么特殊能力？"),
                ("assistant", "能够净化污染，治愈疾病，还能平息海洋的怒火。"),
                ("user", "海洋为什么会愤怒？"),
                ("assistant", "通常是因为人类的污染或者对海洋生物的伤害。"),
                ("user", "海洋生物都有哪些？"),
                ("assistant", "海龙、美人鱼、海妖，还有巨大的海怪。"),
                ("user", "美人鱼友善吗？"),
                ("assistant", "大多数美人鱼很友善，但她们很少与陆地人接触。"),
                ("user", "如何与美人鱼交流？"),
                ("assistant", "需要学会海洋语言，或者使用翻译魔法。"),
                ("user", "海洋语言难学吗？"),
                ("assistant", "对陆地人来说很困难，因为包含很多水下的声音。"),
                ("user", "翻译魔法更容易吗？"),
                ("assistant", "是的，但需要消耗魔法能量，而且效果有时间限制。"),
                ("user", "魔法能量会耗尽吗？"),
                ("assistant", "会的，就像体力一样，需要休息和冥想来恢复。"),
                ("user", "冥想有什么技巧？"),
                ("assistant", "找一个安静的地方，清空思绪，专注于呼吸和魔法流动。"),
                ("user", "魔法流动是什么感觉？"),
                ("assistant", "像温暖的溪流在体内流淌，有经验的法师能清楚感知。"),
                ("user", "新手如何培养这种感知？"),
                ("assistant", "从简单的魔法练习开始，比如点燃蜡烛或移动小物体。"),
                ("user", "点燃蜡烛需要什么咒语？"),
                ("assistant", "'伊格尼斯'是最基础的点火咒语，配合手势使用。"),
                ("user", "手势很重要吗？"),
                ("assistant", "非常重要，正确的手势能引导魔法能量的流向。"),
                ("user", "如果手势错误会怎样？"),
                ("assistant", "轻则魔法失效，重则可能造成魔法反噬。"),
                ("user", "魔法反噬有多危险？"),
                ("assistant", "可能导致魔法能量紊乱，严重时会伤害施法者。"),
                ("user", "如何避免魔法反噬？"),
                ("assistant", "认真学习基础理论，在导师指导下练习，不要急于求成。"),
                ("user", "好的导师去哪里找？"),
                ("assistant", "魔法学院、贤者塔，或者有经验的冒险者法师。"),
                ("user", "魔法学院的学费贵吗？"),
                ("assistant", "确实不便宜，但有些学院提供奖学金给有天赋的学生。"),
                ("user", "奖学金的条件是什么？"),
                ("assistant", "通常需要展示出色的魔法天赋和学习能力。"),
                ("user", "学习能力如何证明？"),
                ("assistant", "通过入学考试，包括理论知识和实践操作。"),
                ("user", "考试内容都有什么？"),
                ("assistant", "魔法历史、元素理论、基础咒语，还有魔法安全知识。"),
                ("user", "魔法安全知识包括什么？"),
                ("assistant", "如何处理魔法事故、防护措施、急救方法等。"),
                ("user", "魔法事故常见吗？"),
                ("assistant", "在学习阶段比较常见，但大多数都是轻微的。"),
                ("user", "轻微事故有哪些？"),
                ("assistant", "头发变色、暂时失声、小范围的元素泄露等。"),
                ("user", "这些问题如何解决？"),
                ("assistant", "通常会自然恢复，或者用简单的解除咒语。"),
                ("user", "解除咒语难学吗？"),
                ("assistant", "是基础课程之一，每个法师都必须掌握。"),
                ("user", "除了解除咒语还要学什么？"),
                ("assistant", "防护法术、治疗魔法、元素操控等核心技能。"),
                ("user", "治疗魔法和牧师的治疗有区别吗？"),
                ("assistant", "法师的治疗更注重技术，牧师的治疗依靠神圣力量。"),
                ("user", "哪种治疗效果更好？"),
                ("assistant", "各有优势，牧师治疗更温和，法师治疗更精确。"),
                ("user", "我应该选择哪条道路？"),
                ("assistant", "这取决于你的性格和天赋，可以先尝试不同的方向。"),
                ("user", "可以同时学习魔法和神术吗？"),
                ("assistant", "理论上可以，但需要极高的天赋和大量的时间投入。"),
                ("user", "有人成功过吗？"),
                ("assistant", "历史上有几位传奇人物做到了，但他们都是千年难遇的天才。"),
                ("user", "我怎么知道自己有没有这样的天赋？"),
                ("assistant", "通过不断的学习和实践，天赋会逐渐显现出来。"),
                ("user", "学习过程中会遇到什么困难？"),
                ("assistant", "理论复杂、实践危险、需要大量时间，还要克服挫折感。"),
                ("user", "如何克服挫折感？"),
                ("assistant", "保持耐心，寻求同伴支持，记住每个大师都曾是初学者。"),
                ("user", "同伴的支持很重要吗？"),
                ("assistant", "非常重要，互相鼓励和交流经验能让学习更有效率。"),
                ("user", "如何找到志同道合的同伴？"),
                ("assistant", "参加学习小组、加入法师协会，或者在冒险中结识。"),
                ("user", "法师协会是什么组织？"),
                ("assistant", "法师们的专业组织，提供学术交流和资源共享。"),
                ("user", "加入协会有什么好处？"),
                ("assistant", "可以获得珍贵的魔法书籍、实验设备，还有导师指导。"),
                ("user", "协会有等级制度吗？"),
                ("assistant", "是的，从学徒到大法师，每个等级都有相应的权限和责任。")
            ]
            
            for i, (role, content) in enumerate(test_dialogues):
                 # 添加对话
                result = await add_dialogue_to_memory(
                    self.user_id, self.project_id, role, content
                )
                
                if result.get('status') == 'success':
                    dialogue_count = result.get('dialogue_count', 0)
                    should_process = result.get('should_process_memory', False)
                    
                    # 每10轮显示进度
                    if (i + 1) % 10 == 0:
                        print(f"[PROGRESS] 已添加 {i+1} 轮对话，当前对话数: {dialogue_count}")
                    
                    # 检查是否触发记忆处理
                    if should_process:
                        print(f"\n[TRIGGER] 第{i+1}轮触发记忆处理！当前对话数: {dialogue_count}")
                        
                        if 'memory_processing' in result:
                            memory_result = result['memory_processing']
                            print(f"[MEMORY] 记忆处理结果: {memory_result.get('status')}")
                            
                            # 检查是否触发了记忆合并
                            if memory_result.get('consolidation_triggered', False):
                                consolidation_triggered = True
                                print("[CONSOLIDATION] 🎉 记忆合并功能已触发！")
                                
                                if 'consolidation_result' in memory_result:
                                    consolidation_result = memory_result['consolidation_result']
                                    print(f"[CONSOLIDATION] 合并结果状态: {consolidation_result.get('status')}")
                                    print(f"[CONSOLIDATION] 合并前核心事件数: {consolidation_result.get('events_before_consolidation', 'N/A')}")
                                    print(f"[CONSOLIDATION] 合并后核心事件数: {consolidation_result.get('events_after_consolidation', 'N/A')}")
                                    print(f"[CONSOLIDATION] 合并前核心反思数: {consolidation_result.get('reflections_before_consolidation', 'N/A')}")
                                    print(f"[CONSOLIDATION] 合并后核心反思数: {consolidation_result.get('reflections_after_consolidation', 'N/A')}")
                                
                                if memory_result.get('consolidation_failed', False):
                                    print(f"[CONSOLIDATION] ❌ 记忆合并失败: {memory_result.get('consolidation_error', '未知错误')}")
                                
                                break
                else:
                    print(f"[ERROR] 第{i+1}轮对话添加失败: {result.get('message')}")
                    return False
                
                # 每50轮暂停一下
                if (i + 1) % 50 == 0:
                    await asyncio.sleep(0.5)
            
            # 3. 总结测试结果
            print(f"\n[STEP 3] 测试总结")
            print(f"[SUMMARY] 总共添加对话轮数: {i+1}")
            print(f"[SUMMARY] 最终对话计数: {dialogue_count}")
            print(f"[SUMMARY] 记忆合并是否触发: {'是' if consolidation_triggered else '否'}")
            
            if consolidation_triggered:
                print("[SUCCESS] ✅ 记忆合并功能测试成功！")
                
                # 4. 验证合并后的记忆状态
                print("\n[STEP 4] 验证合并后的记忆状态...")
                context_result = await get_memory_context_for_chat(
                    self.user_id, self.project_id, "告诉我关于魔法的知识"
                )
                
                if context_result.get('status') == 'success':
                    core_memory = context_result.get('core_memory', {})
                    core_events = core_memory.get('core_events', [])
                    core_reflections = core_memory.get('core_reflections', [])
                    
                    print(f"[VERIFY] 当前核心事件数量: {len(core_events)}")
                    print(f"[VERIFY] 当前核心反思数量: {len(core_reflections)}")
                    
                    if len(core_events) <= 40 and len(core_reflections) <= 40:
                        print("[VERIFY] ✅ 记忆合并效果验证成功，核心记忆数量在合理范围内")
                    else:
                        print("[VERIFY] ⚠️ 记忆合并效果需要检查，核心记忆数量可能过多")
                
                return True
            else:
                print("[WARNING] ⚠️ 记忆合并功能未触发，可能需要检查触发条件")
                return False
                
        except Exception as e:
            print(f"[ERROR] 测试过程中发生异常: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """主函数"""
    print("记忆合并功能专项测试")
    print("目标: 测试240轮对话触发核心记忆合并功能")
    
    test = MemoryConsolidationTest()
    
    try:
        success = await test.test_memory_consolidation()
        if success:
            print("\n[FINAL] 🎉 记忆合并功能测试完全成功！")
        else:
            print("\n[FINAL] ❌ 记忆合并功能测试失败，请检查相关代码")
    except KeyboardInterrupt:
        print("\n[INTERRUPT] 测试被用户中断")
    except Exception as e:
        print(f"\n[ERROR] 测试运行异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())