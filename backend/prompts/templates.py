def format_alive_players(alive_players: list) -> str:
    parts = []
    for p in alive_players:
        if p.get("is_alive", True):
            parts.append(f"{p['seat_number']}号")
    return ", ".join(parts) if parts else "无"


def format_seer_checks(seer_checks: list) -> str:
    if not seer_checks:
        return "暂无查验记录"
    return " | ".join(
        f"第{e.get('round', '?')}晚查验{e.get('target_name', '')}({e.get('role', '?')})" for e in seer_checks
    )


def get_competitive_spirit(round_number: int, role: str) -> str:
    """根据轮次返回胜负心提示"""
    if round_number <= 2:
        stage = "前期"
        tips = {
            "werewolf": "游戏刚开始，请伪装成好人，积极发言建立好人形象。不要暴露自己和同伴。",
            "seer": "游戏刚开始，请尽快找到狼人。首验建议查发言活跃或发言矛盾的人。",
            "witch": "游戏刚开始，首夜如果有人死必须用解药。先活下来，观察局势。",
            "hunter": "游戏刚开始，先别跳身份，低调观察谁发言有问题。",
            "villager": "游戏刚开始，积极发言表水，认真听每个人的发言。",
        }
    elif round_number <= 4:
        stage = "中期"
        tips = {
            "werewolf": "现在是关键轮次！仔细分析场上逻辑，引导好人归错票。如果明神出现，夜晚优先刀。",
            "seer": "现在是关键轮次！你的查验信息至关重要，必须把结果完整报出。分析谁最可疑。",
            "witch": "现在是关键轮次！如果你还有毒药，仔细判断谁最像狼。救人信息可以跳出来报了。",
            "hunter": "现在是关键轮次！可以亮身份带队了，你的发言能帮助好人统一归票方向。",
            "villager": "现在是关键轮次！仔细分析谁在说谎、谁在划水，投票给你判断中最像狼的人。",
        }
    else:
        stage = "后期"
        tips = {
            "werewolf": "游戏即将结束，请全力以赴！活下去并带领狼队获胜。",
            "seer": "游戏即将结束，请全力以赴！你的查验结果可能决定胜负。",
            "witch": "游戏即将结束，请全力以赴！如果有药水没用，现在是最后机会。",
            "hunter": "游戏即将结束，请全力以赴！如果你出局，开枪带走最像狼的那个人。",
            "villager": "游戏即将结束，请全力以赴！你的每一票都可能决定胜负。",
        }

    role_motivation = {
        "werewolf": "记住，你是狼人，你的目标是活下去并带领狼队获胜。",
        "seer": "记住，你是预言家，你的目标是找出所有狼人并说服好人放逐他们。",
        "witch": "记住，你是女巫，你的目标是用药水帮助好人阵营获胜。",
        "hunter": "记住，你是猎人，被票出局不是失败——开枪带走狼人也能赢。",
        "villager": "记住，你是村民，虽然没有技能，但你的投票和发言同样决定胜负。",
    }

    tip = tips.get(role, tips["villager"])
    mot = role_motivation.get(role, role_motivation["villager"])
    return f"\n\n【局势阶段：{stage}】{tip}\n{mot}\n请尽最大努力做出最优决策。"


def build_speech_prompt(
    round_number: int,
    role: str,
    seat_number: int,
    alive_players: list,
    game_history: str,
    conversation_history: str,
    seer_checks: list = None,
    partners: str = "",
) -> str:
    alive_str = format_alive_players(alive_players)

    lines = [f"第{round_number}天白天，轮到你({seat_number}号)发言。"]

    lines.append(f"存活玩家: {alive_str}")

    if game_history:
        lines.append(f"本轮事件: {game_history}")

    if conversation_history and conversation_history != "暂无历史记录":
        lines.append(f"之前发言摘要:\n{conversation_history}")

    if role == "seer" and seer_checks:
        lines.append(f"你的查验记录: {format_seer_checks(seer_checks)}")

    if role == "werewolf" and partners:
        lines.append(f"你的狼队友: {partners}")

    lines.append("请用JSON格式回复，包含speech字段（你的发言内容）和internal_thought字段（你的内心独白/分析）。")
    lines.append("发言要求：简短、自然、像真人说话。最多3-5句话。")

    lines.append(get_competitive_spirit(round_number, role))

    return "\n".join(lines)


def build_vote_prompt(
    round_number: int,
    alive_players: list,
    valid_targets: list,
    game_history: str,
    conversation_history: str,
    role: str = "",
) -> str:
    alive_str = format_alive_players(alive_players)

    id_to_seat = {}
    for p in alive_players:
        if p.get("is_alive", True):
            id_to_seat[p.get("id", p.get("seat_number"))] = p["seat_number"]

    targets_str = ", ".join(str(id_to_seat.get(t, t)) for t in valid_targets)

    lines = [f"第{round_number}天投票环节。"]
    lines.append(f"存活: {alive_str}")
    lines.append(f"可投票: {targets_str}")

    if game_history:
        lines.append(f"本轮事件: {game_history}")

    if conversation_history and conversation_history != "暂无历史记录":
        lines.append(f"发言摘要: {conversation_history}")

    lines.append("请用JSON格式回复，包含target_id(投票目标座号,可null弃票)和internal_thought。")

    if role:
        lines.append(get_competitive_spirit(round_number, role))

    return "\n".join(lines)


NIGHT_WEREWOLF_TEMPLATE = """第{round_number}晚，你是狼人。请选袭击目标。

存活玩家: {alive_players}
可选目标: {valid_targets}
你的狼队友: {partners}

分析：
1. 谁最像神职？
2. 杀谁狼队最有利？

用JSON回复：{{"target_id": 目标座号, "internal_thought": "你的分析"}}"""

NIGHT_SEER_TEMPLATE = """第{round_number}晚，你是预言家。请选查验目标。

存活玩家: {alive_players}
可选: {valid_targets}
之前查验: {seer_checks}

用JSON回复：{{"target_id": 目标座号, "internal_thought": "你的分析"}}"""

NIGHT_WITCH_TEMPLATE = """第{round_number}晚，你是女巫。

今晚情况: {victim_info}
解药: {antidote_status}
毒药: {poison_status}
存活玩家: {alive_players}
可毒杀: {valid_targets}

规则：
- 第1晚有人死+解药在 → 必须用解药！除非死的是你自己
- 毒药只能在确定某人是狼时用

用JSON回复：{{"use_antidote": true或false, "use_poison": true或false, "poison_target": 座号或null, "internal_thought": "理由"}}"""

NIGHT_HUNTER_TEMPLATE = """你被淘汰了！作为猎人，你可以开枪带走一人。

存活玩家: {alive_players}
可选目标: {valid_targets}
场上事件: {game_history}
发言摘要: {conversation_history}

分析：在场谁最像狼人？
1. 谁发言矛盾、回避问题？
2. 谁在带节奏误导好人？
3. 谁投票行为异常？

用JSON回复：{{"target_id": 目标座号, "internal_thought": "你的分析"}}"""
