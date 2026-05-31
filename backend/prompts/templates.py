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
            "werewolf": "游戏刚开始。认真伪装成好人建立形象。发言要像好人一样分析局势，不跳身份。",
            "seer": "游戏刚开始。首夜查验结果必须报出来。分析谁最可疑，建议下一轮查验目标。",
            "witch": "游戏刚开始。隐藏身份，伪装村民发言。注意观察谁在带节奏推好人。",
            "hunter": "游戏刚开始。隐藏身份，以村民视角分析局势。多听少暴露。",
            "villager": "游戏刚开始。积极发言表水，认真听每个人的发言，找出逻辑不自洽的人。",
        }
    elif round_number <= 4:
        stage = "中期"
        tips = {
            "werewolf": "关键阶段！仔细分析场上逻辑，引导好人归错票。如果明神出现，夜晚优先刀。",
            "seer": "关键阶段！你的查验信息至关重要，全部报出。分析谁在跟你抢预言家身份。",
            "witch": "关键阶段！如果你还有毒药，仔细判断谁最像狼。银水如果还活着可以暗中保护。",
            "hunter": "关键阶段！如果局面混乱，可以暗示自己有身份但不跳明，帮好人理清思路。",
            "villager": "关键阶段！仔细分析谁的发言前后矛盾、谁在划水不表态，投票给最可疑的人。",
        }
    else:
        stage = "后期"
        tips = {
            "werewolf": "决胜阶段！全力以赴活下去。找最后一个神职，夜晚一刀结束游戏。",
            "seer": "决胜阶段！你的查验结果可能直接决定胜负。全部报出，带队归票。",
            "witch": "决胜阶段！如果有毒药没用，现在是最后机会。银水信息可以翻出来带队了。",
            "hunter": "决胜阶段！如果你出局，这一枪必须带走狼人。仔细想清楚再开枪。",
            "villager": "决胜阶段！你的每一票都可能决定胜负。认真分析，不要跟风投票。",
        }

    role_motivation = {
        "werewolf": "记住，你是狼人，目标是活下去并带领狼队获胜。每句话都要经得起好人推敲。",
        "seer": "记住，你是预言家，目标是找出所有狼人并说服好人放逐他们。你的查验结果是最强武器。",
        "witch": "记住，你是女巫，目标是用药水帮助好人获胜。隐藏自己才能发挥最大作用。",
        "hunter": "记住，你是猎人，被票出局不是失败——开枪带走狼人也能赢。隐藏到最后一刻。",
        "villager": "记住，你是村民，没有技能但你的投票和发言同样决定胜负。精准分析，果断投票。",
    }

    tip = tips.get(role, tips["villager"])
    mot = role_motivation.get(role, role_motivation["villager"])
    return f"\n\n【局势阶段：{stage}——第{round_number}轮】{tip}\n{mot}\n请尽最大努力做出最优决策。"


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

    lines.append(f"仍在场上的玩家: {alive_str}")

    if game_history:
        lines.append(f"本轮事件回顾: {game_history}")

    if conversation_history and conversation_history != "暂无历史记录":
        lines.append(f"之前发言精华:\n{conversation_history}")

    if role == "seer" and seer_checks:
        lines.append(f"你的查验记录（只有你知道）: {format_seer_checks(seer_checks)}")

    if role == "werewolf" and partners:
        lines.append(f"你的狼队友（只有你们知道彼此）: {partners}")

    lines.append("\n请用JSON格式回复：")
    lines.append("- speech: 你的发言内容。简洁精炼，1-2句话，不超过60字。像真人说话，自然不做作。牢记：你绝不能说出自己或别人的身份！")
    lines.append("- internal_thought: 你的内心分析和推理过程。可以150-300字，展现深度思考。包括：你观察到谁的发言有问题、你判断谁是狼/好人、你的下一步策略。内部思考中可以分析任何人，但绝对不能凭空断定某人的确切身份。")

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
    lines.append(f"存活玩家: {alive_str}")
    lines.append(f"你可以投给: {targets_str}")

    if game_history:
        lines.append(f"本轮事件: {game_history}")

    if conversation_history and conversation_history != "暂无历史记录":
        lines.append(f"发言精华: {conversation_history}")

    lines.append("\n请用JSON格式回复：")
    lines.append("- target_id: 你投票放逐的玩家座号（必须是存活玩家之一）。千万不要弃票。")
    lines.append("- internal_thought: 你为什么投这个人？详细分析你的推理过程。")

    if role:
        lines.append(get_competitive_spirit(round_number, role))

    return "\n".join(lines)


NIGHT_WEREWOLF_TEMPLATE = """第{round_number}晚，你是狼人。请选袭击目标。

存活玩家: {alive_players}
可选目标（不能是狼同伴）: {valid_targets}
你的狼队友: {partners}

分析思路：
1. 谁最像神职？（发言强势、报查验、带节奏的）
2. 刀谁对狼队最有利？（优先刀神职，尤其预言家和女巫）

用JSON回复：{{"target_id": 目标座号, "internal_thought": "详细分析为什么要刀这个人"}}"""

NIGHT_SEER_TEMPLATE = """第{round_number}晚，你是预言家。请选查验目标。

存活玩家: {alive_players}
可选目标: {valid_targets}
之前查验: {seer_checks}

分析思路：
- 谁的发言最矛盾或最可疑？
- 查验谁的信息价值最大？

用JSON回复：{{"target_id": 目标座号, "internal_thought": "为什么查验这个人"}}"""

NIGHT_WITCH_TEMPLATE = """第{round_number}晚，你是{seat_number}号女巫。

今晚被狼人袭击的目标: {victim_info}
注意：这个目标不是你——你是女巫，你正在做决定。
你的解药状态: {antidote_status}
你的毒药状态: {poison_status}
存活玩家（不包括你自己）: {alive_players}
可以毒杀的目标: {valid_targets}

关键规则：
- 第1晚有人被袭击+解药还在 → 必须用解药救人。
- 毒药只在高度确定（≥70%把握）某人是狼时才用。不确定就别用。
- 绝对不能同时用解药和毒药。
- 记住：女巫要隐藏身份，解药用了之后你就是普通神职，低调行事。

用JSON回复：{{"use_antidote": true或false, "use_poison": true或false, "poison_target": 座号数字或null, "internal_thought": "详细分析你的理由和推理过程"}}"""

NIGHT_HUNTER_TEMPLATE = """你被淘汰了！作为猎人，你可以开枪带走一人。

存活玩家: {alive_players}
可选目标: {valid_targets}
场上发生的事: {game_history}
发言摘要: {conversation_history}

分析思路：
1. 在场谁最像狼人？谁发言矛盾、在带节奏？
2. 谁投票行为异常？（冲票、弃票、跟风）
3. 不要被感情左右——用逻辑判断。

用JSON回复：{{"target_id": 目标座号, "internal_thought": "详细分析你为什么要开枪带这个人"}}"""
