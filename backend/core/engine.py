import asyncio
import random
import traceback
import time
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from core.agent_manager import AgentManager
from memory.memory_manager import MemoryManager, Memory
from models.game import Game
from models.game_player import GamePlayer
from models.game_event import GameEvent
from config import Config
from db.database import async_session


class StatsTracker:
    def __init__(self):
        self.player_stats: dict[int, dict] = {}
        self.vote_records: list[dict] = []
        self.role_recognitions: list[dict] = []
        self.ability_uses: list[dict] = []
        self.speech_counts: dict[int, int] = {}

    def init_player(self, player_id: int, role: str):
        self.player_stats[player_id] = {
            "role": role,
            "score": 0,
            "votes_correct": 0,
            "votes_total": 0,
            "speeches": 0,
            "skill_uses": 0,
            "survived_rounds": 0,
        }
        self.speech_counts[player_id] = 0

    def record_speech(self, player_id: int):
        if player_id in self.player_stats:
            self.player_stats[player_id]["speeches"] += 1
        self.speech_counts[player_id] = self.speech_counts.get(player_id, 0) + 1

    def record_vote(self, voter_id: int, target_id: int | None, target_role: str | None, voter_role: str):
        is_correct = False
        if target_role:
            if voter_role == "werewolf" and target_role != "werewolf":
                is_correct = True
            elif voter_role != "werewolf" and target_role == "werewolf":
                is_correct = True
        self.vote_records.append({
            "voter_id": voter_id,
            "target_id": target_id,
            "target_role": target_role,
            "voter_role": voter_role,
            "is_correct": is_correct,
        })
        if voter_id in self.player_stats:
            self.player_stats[voter_id]["votes_total"] += 1
            if is_correct:
                self.player_stats[voter_id]["votes_correct"] += 1

    def record_ability_use(self, player_id: int, ability: str):
        self.ability_uses.append({"player_id": player_id, "ability": ability, "target_id": None, "success": True})
        if player_id in self.player_stats:
            self.player_stats[player_id]["skill_uses"] += 1

    def record_survival(self, player_id: int):
        if player_id in self.player_stats:
            self.player_stats[player_id]["survived_rounds"] += 1

    def calc_mvp_svp(self, winner: str) -> tuple[dict | None, dict | None]:
        if winner == "draw":
            return None, None

        for pid, stats in self.player_stats.items():
            score = 0
            role = stats["role"]
            is_winner = (winner == "werewolves" and role == "werewolf") or \
                        (winner == "villagers" and role != "werewolf")

            if is_winner:
                score += 20
            if stats["votes_total"] > 0:
                accuracy = stats["votes_correct"] / stats["votes_total"]
                score += int(accuracy * 10)

            score += min(stats["skill_uses"] * 4, 12)
            score += min(stats["speeches"], 5)
            stats["score"] = score

        winners = [(pid, s) for pid, s in self.player_stats.items()
                    if (winner == "werewolves" and s["role"] == "werewolf") or
                       (winner == "villagers" and s["role"] != "werewolf")]
        losers = [(pid, s) for pid, s in self.player_stats.items() if (pid, s) not in winners]

        mvp = max(winners, key=lambda x: x[1]["score"]) if winners else None
        svp = max(losers, key=lambda x: x[1]["score"]) if losers else None

        return mvp, svp


class GameEngine:
    def __init__(self, game: Game, players: list[GamePlayer], agent_manager: AgentManager):
        self.game = game
        self.players = players
        self.agent_manager = agent_manager
        self.round = 1
        self.phase = "night_werewolf"
        self.winner = None
        self.witch_has_antidote = True
        self.witch_has_poison = True
        self.hunter_can_shoot = True
        self.memory = Memory()
        self.stats = StatsTracker()
        self._event_callbacks = []
        self._log: list[str] = []

        for p in players:
            self.stats.init_player(p.id, p.role)

    def on_event(self, callback):
        self._event_callbacks.append(callback)

    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self._log.append(line)
        print(line, flush=True)

    def _log_god_view_start(self):
        werewolves = [p for p in self.players if p.role == "werewolf" and p.is_alive]
        seer = next((p for p in self.players if p.role == "seer" and p.is_alive), None)
        witch = next((p for p in self.players if p.role == "witch" and p.is_alive), None)
        hunter = next((p for p in self.players if p.role == "hunter" and p.is_alive), None)
        villagers = [p for p in self.players if p.role == "villager" and p.is_alive]

        alive_w = [f"{w.seat_number}号{w.player_name}" for w in werewolves]
        self.log(f"🐺 狼人({len(alive_w)}): {', '.join(alive_w)}" if alive_w else "🐺 狼人: 全灭")
        if seer:
            self.log(f"🔮 预言家: {seer.seat_number}号{seer.player_name}")
        if witch:
            antidote = "解药✓" if self.witch_has_antidote else "解药✗"
            poison = "毒药✓" if self.witch_has_poison else "毒药✗"
            self.log(f"🧪 女巫: {witch.seat_number}号{witch.player_name} ({antidote} {poison})")
        if hunter:
            self.log(f"🏹 猎人: {hunter.seat_number}号{hunter.player_name} (可开枪: {'是' if self.hunter_can_shoot else '否'})")
        alive_v = [f"{v.seat_number}号{v.player_name}" for v in villagers]
        self.log(f"👤 村民({len(alive_v)}): {', '.join(alive_v)}" if alive_v else "👤 村民: 全灭")
        self.log("")

    async def emit_event(self, event: GameEvent):
        async with async_session() as db:
            db.add(event)
            await db.commit()
            await db.refresh(event)
        for cb in self._event_callbacks:
            try:
                await cb(event)
            except Exception as e:
                self.log(f"事件回调异常: {e}")

    async def run(self):
        self.log("===== 游戏引擎启动 =====")
        async with async_session() as db:
            existing = await db.get(Game, self.game.id)
            if existing:
                existing.started_at = datetime.now(timezone.utc)
                await db.commit()
            else:
                self.log("警告: 数据库中找不到Game记录")

        await self.emit_event(GameEvent(
            game_id=self.game.id,
            round_number=0,
            phase="game_start",
            event_type="phase_change",
            public_content="游戏开始！身份已分配。9人标准局：3狼+1预+1巫+1猎+3民。",
        ))
        self.log(f"玩家: {[(p.id, p.player_name, p.role, p.seat_number) for p in self.players]}")

        try:
            while self.winner is None and self.round <= Config.MAX_ROUNDS:
                self.log(f"--- 第{self.round}轮 夜晚阶段 ---")
                try:
                    await self.night_phase()
                except Exception as e:
                    self.log(f"夜晚阶段异常: {e}")
                    traceback.print_exc()
                    break

                if self.winner:
                    self.log(f"胜负已定: {self.winner}")
                    break

                self.log(f"--- 第{self.round}轮 白天阶段 ---")
                try:
                    await self.day_phase()
                except Exception as e:
                    self.log(f"白天阶段异常: {e}")
                    traceback.print_exc()
                    break

            if self.winner is None:
                self.winner = "draw"

        except Exception as e:
            self.log(f"游戏主循环致命错误: {e}")
            traceback.print_exc()
            self.winner = "draw"
        finally:
            self.log(f"游戏结束: {self.winner}")
            async with async_session() as db:
                existing = await db.get(Game, self.game.id)
                if existing:
                    existing.winner = self.winner
                    existing.total_rounds = self.round
                    existing.ended_at = datetime.now(timezone.utc)
                    await db.commit()

            end_message = (
                "狼人阵营获胜" if self.winner == "werewolves"
                else "好人阵营获胜" if self.winner == "villagers"
                else "平局"
            )

            mvp, svp = self.stats.calc_mvp_svp(self.winner)
            mvp_str = ""
            if mvp:
                mvp_player = next((p for p in self.players if p.id == mvp[0]), None)
                if mvp_player:
                    mvp_str = f" | MVP：{mvp_player.seat_number}号 {mvp_player.player_name}({mvp_player.role}) 得分{mvp[1]['score']}"
            if svp:
                svp_player = next((p for p in self.players if p.id == svp[0]), None)
                if svp_player:
                    mvp_str += f" | SVP：{svp_player.seat_number}号 {svp_player.player_name}({svp_player.role}) 得分{svp[1]['score']}"

            end_event = GameEvent(
                game_id=self.game.id,
                round_number=self.round,
                phase="game_over",
                event_type="game_over",
                public_content=f"游戏结束，{end_message}。{mvp_str}",
            )
            self.memory.add_conversation(self.round, "game_over", "系统", f"游戏结束，{end_message}。", "game_over")
            await self.emit_event(end_event)

    async def night_phase(self):
        # 天黑请闭眼 — 上帝视角：显示各特殊玩家状态
        self.log("")
        self.log("┌──────────────────────────────────────────┐")
        self.log("│ 🌙 上 帝 视 角 · 夜 间 行 动 │")
        self.log("└──────────────────────────────────────────┘")
        self._log_god_view_start()

        await self.emit_event(GameEvent(
            game_id=self.game.id,
            round_number=self.round,
            phase="night_werewolf",
            event_type="phase_change",
            public_content="🌙 夜晚降临，狼人请行动。",
        ))
        await asyncio.sleep(1.5)
        wolf_target_id = await self._wolf_action()

        await self.emit_event(GameEvent(
            game_id=self.game.id,
            round_number=self.round,
            phase="night_seer",
            event_type="phase_change",
            public_content="🔮 预言家请查验身份。",
        ))
        await asyncio.sleep(1.5)
        seer_check = await self._seer_action()

        await self.emit_event(GameEvent(
            game_id=self.game.id,
            round_number=self.round,
            phase="night_witch",
            event_type="phase_change",
            public_content="🧪 女巫请使用药水。",
        ))
        await asyncio.sleep(1.5)
        witch_decision = await self._witch_action(wolf_target_id)
        if witch_decision.use_antidote and witch_decision.use_poison:
            witch_decision.use_poison = False

        deaths = self._resolve_night_deaths(wolf_target_id, witch_decision)
        await self._apply_deaths(deaths)
        self.log(f"死亡: {deaths}")

        # 上帝视角：夜晚行动总结
        night_summary_parts = []
        if wolf_target_id:
            try:
                wolf_victim = next((p for p in self.players if p.id == int(wolf_target_id)), None)
                if wolf_victim:
                    night_summary_parts.append(f"🐺 狼人袭击了 {wolf_victim.seat_number}号")
            except (ValueError, TypeError):
                pass
        if witch_decision.use_antidote:
            night_summary_parts.append("💚 女巫使用了解药救人")
        if witch_decision.use_poison and witch_decision.poison_target:
            try:
                poison_victim = next((p for p in self.players if p.id == int(witch_decision.poison_target)), None)
                if poison_victim:
                    night_summary_parts.append(f"☠️ 女巫毒杀了 {poison_victim.seat_number}号")
            except (ValueError, TypeError):
                pass
        if seer_check:
            night_summary_parts.append(f"🔮 预言家完成了查验")
        if deaths:
            night_summary_parts.append(f"💀 死亡: {', '.join(str(d) for d in deaths)}号")
        else:
            night_summary_parts.append("✨ 无人死亡")
        if night_summary_parts:
            await self.emit_event(GameEvent(
                game_id=self.game.id, round_number=self.round, phase="night_summary",
                event_type="night_summary", public_content=" | ".join(night_summary_parts),
            ))

        hunter_died = any(
            pid for pid in deaths
            if next((p for p in self.players if p.id == pid), None) and
            next((p for p in self.players if p.id == pid), None).role == "hunter" and
            self.hunter_can_shoot
        )
        if hunter_died:
            await self._trigger_hunter_shoot(deaths, "night")

        for p in self.players:
            if p.is_alive:
                self.stats.record_survival(p.id)

        self.round += 1
        await self._announce_deaths(deaths)
        self.winner = self._check_winner()

    async def _wolf_action(self) -> int | None:
        wolf_players = [p for p in self.players if p.role == "werewolf" and p.is_alive]
        if not wolf_players:
            self.log("狼人全灭，跳过")
            return None

        self.log(f"🐺 狼人团队: {[(w.seat_number, w.player_name) for w in wolf_players]}")

        async with async_session() as db:
            memory_manager = MemoryManager(db, self.game.id, self.memory)
            contexts = {}
            for wp in wolf_players:
                game_state = {"phase": "night_werewolf", "round_number": self.round}
                ctx = await memory_manager.build_context(wp.id, wp.role, wp.personality or "", game_state)
                ctx.conversation_history = self.memory.get_all_conversations()
                contexts[wp.id] = ctx

        wolf_ids = [wp.id for wp in wolf_players]
        self.log(f"🔪 狼人正在商议刀人... (并发控制: Semaphore(3), 超时{Config.LLM_TIMEOUT}s)")
        for wp in wolf_players:
            await self.emit_event(GameEvent(game_id=self.game.id, round_number=self.round, phase="night_werewolf", player_id=wp.id, event_type="agent_thinking", public_content=f"{wp.seat_number}号正在思考..."))
        target_id, decisions = await self.agent_manager.ask_wolves(wolf_ids, contexts)
        for wp in wolf_players:
            await self.emit_event(GameEvent(game_id=self.game.id, round_number=self.round, phase="night_werewolf", player_id=wp.id, event_type="thinking_clear", public_content=""))

        # 上帝视角日志：显示每个狼人的决定
        for i, decision in enumerate(decisions):
            if i < len(wolf_ids):
                wp = wolf_players[i]
                self.log(f"   狼{wp.seat_number}号({wp.player_name})选择刀 → {decision.target_id}号")
                self.stats.record_ability_use(wolf_ids[i], "kill")

        if target_id is None:
            alive_non_wolves = [p for p in self.players if p.is_alive and p.role != "werewolf"]
            if alive_non_wolves:
                target_id = str(random.choice(alive_non_wolves).id)
                self.log(f"狼人未抉择，随机选择: {target_id}")

        for i, decision in enumerate(decisions):
            if i < len(wolf_ids):
                await self.emit_event(GameEvent(
                    game_id=self.game.id,
                    round_number=self.round,
                    phase="night_werewolf",
                    player_id=wolf_ids[i],
                    event_type="action",
                    private_content=f"狼人选择击杀玩家 {decision.target_id}",
                    internal_thought=decision.internal_thought,
                    reasoning_content=decision.reasoning,
                ))

        try:
            return int(target_id) if target_id else None
        except (ValueError, TypeError):
            return None

    async def _seer_action(self) -> dict:
        seer_player = next((p for p in self.players if p.role == "seer" and p.is_alive), None)
        if not seer_player:
            return {}

        async with async_session() as db:
            memory_manager = MemoryManager(db, self.game.id, self.memory)
            game_state = {"phase": "night_seer", "round_number": self.round}
            ctx = await memory_manager.build_context(seer_player.id, seer_player.role, seer_player.personality or "", game_state)
            ctx.conversation_history = self.memory.get_all_conversations()

        self.log(f"🔮 预言家 {seer_player.seat_number}号({seer_player.player_name}) 正在查验...")
        await self.emit_event(GameEvent(game_id=self.game.id, round_number=self.round, phase="night_seer", player_id=seer_player.id, event_type="agent_thinking", public_content=f"{seer_player.seat_number}号正在思考..."))
        decision = await self.agent_manager.ask_seer(seer_player.id, ctx)
        await self.emit_event(GameEvent(game_id=self.game.id, round_number=self.round, phase="night_seer", player_id=seer_player.id, event_type="thinking_clear", public_content=""))
        self.stats.record_ability_use(seer_player.id, "check")

        result = {}
        private_content = ""
        if decision.target_id:
            try:
                target_id = int(decision.target_id)
                target_player = next((p for p in self.players if p.id == target_id), None)
                if target_player:
                    is_werewolf = target_player.role == "werewolf"
                    result = {
                        "target_id": decision.target_id,
                        "result": "狼人" if is_werewolf else "好人",
                        "is_werewolf": is_werewolf,
                    }
                    private_content = f"查验玩家 {target_player.seat_number}号({target_player.player_name})，结果为：{result['result']}"
                    self.log(f"🔮 预言家查验 {target_player.seat_number}号({target_player.player_name}) → {result['result']}")
                    self.log(f"   内心独白: {decision.internal_thought[:80] if decision.internal_thought else '(无)'}")
            except (ValueError, TypeError):
                result = {"target_id": decision.target_id, "result": "查验失败"}
                private_content = f"查验玩家 {decision.target_id}，结果无效"
                self.log(f"🔮 预言家查验失败: target={decision.target_id}")

            await self.emit_event(GameEvent(
                game_id=self.game.id,
                round_number=self.round,
                phase="night_seer",
                player_id=seer_player.id,
                event_type="seer_check",
                public_content="🔮 预言家已看到今晚的天机。" if target_player else "预言家已完成查验",
                private_content=private_content,
                internal_thought=decision.internal_thought,
                reasoning_content=decision.reasoning,
            ))

        return result

    async def _witch_action(self, wolf_target_id):
        from schemas.game_schemas import AgentDecision as AD

        witch_player = next((p for p in self.players if p.role == "witch" and p.is_alive), None)
        if not witch_player:
            return AD(action="witch_action", use_antidote=False, use_poison=False)

        async with async_session() as db:
            memory_manager = MemoryManager(db, self.game.id, self.memory)
            game_state = {
                "phase": "night_witch",
                "round_number": self.round,
                "victim_id": int(wolf_target_id) if wolf_target_id else None,
            }
            ctx = await memory_manager.build_context(witch_player.id, witch_player.role, witch_player.personality or "", game_state)

        ctx.conversation_history = self.memory.get_all_conversations()
        if wolf_target_id:
            vp = next((p for p in self.players if p.id == wolf_target_id), None)
            ctx.witch_info["victim_id"] = str(vp.seat_number) if vp else str(wolf_target_id)
        else:
            ctx.witch_info["victim_id"] = None
        ctx.witch_info["has_antidote"] = self.witch_has_antidote
        ctx.witch_info["has_poison"] = self.witch_has_poison

        self.log(f"🧪 女巫 {witch_player.seat_number}号({witch_player.player_name}) 正在决定用药...")
        self.log(f"   今晚狼人袭击: {'平安夜' if not wolf_target_id else f'{wolf_target_id}号'}")
        await self.emit_event(GameEvent(game_id=self.game.id, round_number=self.round, phase="night_witch", player_id=witch_player.id, event_type="agent_thinking", public_content=f"{witch_player.seat_number}号正在思考..."))
        decision = await self.agent_manager.ask_witch(witch_player.id, ctx)
        await self.emit_event(GameEvent(game_id=self.game.id, round_number=self.round, phase="night_witch", player_id=witch_player.id, event_type="thinking_clear", public_content=""))
        if decision.use_antidote:
            self.log(f"🧪 女巫使用解药 → 救活")
            self.stats.record_ability_use(witch_player.id, "antidote")
        if decision.use_poison:
            self.log(f"🧪 女巫使用毒药 → 毒杀 {decision.poison_target}号")
            self.stats.record_ability_use(witch_player.id, "poison")
        if not decision.use_antidote and not decision.use_poison:
            self.log(f"🧪 女巫不使用任何药水")
        self.log(f"   内心独白: {decision.internal_thought[:80] if decision.internal_thought else '(无)'}")

        if decision.use_antidote and decision.use_poison:
            decision.use_poison = False

        event_type = "witch_action"
        private_content = "女巫选择："
        if decision.use_antidote:
            private_content += "使用解药救活"
            event_type = "witch_use_antidote"
        if decision.use_poison and decision.poison_target:
            private_content += f"使用毒药毒杀 {decision.poison_target}"
            event_type = "witch_use_poison"
        if not decision.use_antidote and not decision.use_poison:
            private_content += "不使用任何药水"

        await self.emit_event(GameEvent(
            game_id=self.game.id,
            round_number=self.round,
            phase="night_witch",
            player_id=witch_player.id,
            event_type=event_type,
            public_content="🧪 女巫在暗中调配着药剂..." if event_type == "witch_action" else "💊 女巫使用了药水",
            private_content=private_content,
            internal_thought=decision.internal_thought,
            reasoning_content=decision.reasoning,
        ))

        return decision

    def _resolve_night_deaths(self, wolf_target_id, witch_decision) -> list:
        deaths = []

        wolf_kill_id: int | None = None
        try:
            wolf_kill_id = int(wolf_target_id) if wolf_target_id else None
        except (ValueError, TypeError):
            pass

        if wolf_kill_id is not None:
            if witch_decision.use_antidote:
                self.witch_has_antidote = False
                self.log(f"女巫使用解药救活 {wolf_kill_id}")
            else:
                deaths.append(wolf_kill_id)
                self.log(f"狼人击杀 {wolf_kill_id}")

        if witch_decision.use_antidote:
            self.witch_has_antidote = False

        if witch_decision.use_poison and witch_decision.poison_target:
            try:
                pt = int(witch_decision.poison_target)
                if pt not in deaths:
                    deaths.append(pt)
                self.witch_has_poison = False
                self.log(f"女巫毒杀 {pt}")
                killed_player = next((p for p in self.players if p.id == pt), None)
                if killed_player and killed_player.role == "hunter":
                    self.hunter_can_shoot = False
                    self.log("猎人中女巫毒药，不能开枪")
            except (ValueError, TypeError):
                pass

        return list(set(deaths))

    async def _apply_deaths(self, deaths: list):
        async with async_session() as db:
            for pid in deaths:
                player = await db.get(GamePlayer, pid)
                if player:
                    player.is_alive = False
            await db.commit()

        for pid in deaths:
            for player in self.players:
                if player.id == pid:
                    player.is_alive = False

    async def _trigger_hunter_shoot(self, deaths: list, trigger: str):
        hunter_player = next((p for p in self.players if p.role == "hunter" and p.id in deaths), None)
        if not hunter_player or not self.hunter_can_shoot:
            return

        self.hunter_can_shoot = False
        self.log(f"猎人{hunter_player.seat_number}号被{'刀' if trigger == 'night' else '票'}，开枪！")

        await self.emit_event(GameEvent(
            game_id=self.game.id,
            round_number=self.round,
            phase="hunter_shoot",
            player_id=hunter_player.id,
            event_type="phase_change",
            public_content=f"🔫 猎人{hunter_player.seat_number}号被淘汰，可以开枪！请选择目标。",
        ))

        async with async_session() as db:
            memory_manager = MemoryManager(db, self.game.id, self.memory)
            game_state = {"phase": "hunter_shoot", "round_number": self.round}
            ctx = await memory_manager.build_context(hunter_player.id, hunter_player.role, hunter_player.personality or "", game_state)
            ctx.conversation_history = self.memory.get_all_conversations()
            ctx.valid_targets = [p.id for p in self.players if p.is_alive and p.id != hunter_player.id]

        await self.emit_event(GameEvent(game_id=self.game.id, round_number=self.round, phase="hunter_shoot", player_id=hunter_player.id, event_type="agent_thinking", public_content=f"{hunter_player.seat_number}号正在思考..."))
        decision = await self.agent_manager.ask_hunter(hunter_player.id, ctx)
        await self.emit_event(GameEvent(game_id=self.game.id, round_number=self.round, phase="hunter_shoot", player_id=hunter_player.id, event_type="thinking_clear", public_content=""))
        self.log(f"猎人开枪: target={decision.target_id}")
        self.stats.record_ability_use(hunter_player.id, "shoot")

        if decision.target_id:
            try:
                shoot_target_id = int(decision.target_id)
                shoot_target = next((p for p in self.players if p.id == shoot_target_id), None)
                if shoot_target and shoot_target.is_alive:
                    shoot_target.is_alive = False
                    await self._sync_player_death(shoot_target_id)
                    shoot_msg = f"🔫 猎人{hunter_player.seat_number}号开枪带走了{shoot_target.seat_number}号！"
                    self.log(shoot_msg)
                    self.memory.add_conversation(self.round, "hunter_shoot", f"{hunter_player.seat_number}号猎人", shoot_msg, "hunter_shoot")
                    await self.emit_event(GameEvent(
                        game_id=self.game.id,
                        round_number=self.round,
                        phase="hunter_shoot",
                        player_id=hunter_player.id,
                        event_type="hunter_shoot",
                        public_content=shoot_msg,
                        internal_thought=decision.internal_thought,
                    ))
            except (ValueError, TypeError):
                pass

    async def _announce_deaths(self, deaths: list):
        if not deaths:
            self.memory.add_conversation(self.round, "day_announce", "系统", "昨夜是平安夜。", "death")
            await self.emit_event(GameEvent(
                game_id=self.game.id,
                round_number=self.round,
                phase="day_announce",
                event_type="death",
                public_content="昨夜是平安夜。",
            ))
            return

        for pid in deaths:
            dead_player = next((p for p in self.players if p.id == pid), None)
            if dead_player:
                death_msg = f"{dead_player.seat_number}号玩家 {dead_player.player_name} 死亡"
                self.memory.add_conversation(self.round, "day_announce", dead_player.player_name, death_msg, "death")
                await self.emit_event(GameEvent(
                    game_id=self.game.id,
                    round_number=self.round,
                    phase="day_announce",
                    player_id=dead_player.id,
                    event_type="death",
                    public_content=f"昨夜死亡：{dead_player.seat_number}号玩家 {dead_player.player_name}。",
                ))

    async def day_phase(self):
        self.phase = "day_speech"
        self.memory.clear_current_round()
        await self._emit_phase_change("day_speech", "进入白天发言环节。")
        await asyncio.sleep(2)

        alive_players = [p for p in self.players if p.is_alive]
        alive_players_sorted = sorted(alive_players, key=lambda p: p.seat_number)

        async with async_session() as db:
            memory_manager = MemoryManager(db, self.game.id, self.memory)
            for i, player in enumerate(alive_players_sorted):
                if not player.is_alive:
                    continue
                game_state = {"phase": "day_speech", "round_number": self.round}
                ctx = await memory_manager.build_context(player.id, player.role, player.personality or "", game_state)
                ctx.conversation_history = self.memory.get_all_conversations()
                self.log(f"调用LLM发言: {player.id}({player.player_name}) ({i+1}/{len(alive_players_sorted)})")
                decision = await self.agent_manager.ask_speech(player.id, ctx)

                await self.emit_event(GameEvent(
                    game_id=self.game.id,
                    round_number=self.round,
                    phase="day_speech",
                    player_id=player.id,
                    event_type="speech",
                    public_content=f"{player.seat_number}号 {player.player_name}：{decision.speech or ''}",
                    internal_thought=decision.internal_thought,
                    reasoning_content=decision.reasoning,
                ))
                self.memory.add_conversation(self.round, "day_speech", f"{player.seat_number}号{player.player_name}", decision.speech or "", "discussion")
                self.stats.record_speech(player.id)
                await asyncio.sleep(1.0)

        self.phase = "day_vote"
        await self._emit_phase_change("day_vote", "进入投票环节，请各位玩家投票。")
        await asyncio.sleep(1.5)

        async with async_session() as db:
            memory_manager = MemoryManager(db, self.game.id, self.memory)
            contexts = {}
            for player in alive_players_sorted:
                if not player.is_alive:
                    continue
                game_state = {"phase": "day_vote", "round_number": self.round}
                ctx = await memory_manager.build_context(player.id, player.role, player.personality or "", game_state)
                ctx.conversation_history = self.memory.get_all_conversations()
                contexts[player.id] = ctx

        self.log(f"调用LLM投票: {len(contexts)}个玩家")
        for pid in contexts:
            voter = next((p for p in self.players if p.id == pid), None)
            if voter:
                await self.emit_event(GameEvent(game_id=self.game.id, round_number=self.round, phase="day_vote", player_id=pid, event_type="agent_thinking", public_content=f"{voter.seat_number}号正在思考..."))
        votes = await self.agent_manager.ask_votes(contexts)
        for pid in contexts:
            await self.emit_event(GameEvent(game_id=self.game.id, round_number=self.round, phase="day_vote", player_id=pid, event_type="thinking_clear", public_content=""))

        vote_count: dict[str, int] = {}
        for pid, decision in votes.items():
            voter = next((p for p in self.players if p.id == pid), None)
            if not voter:
                continue

            target = decision.target_id
            target_player = None
            if target:
                try:
                    target_int = int(target)
                    target_player = next((p for p in self.players if p.id == target_int and p.is_alive), None)
                    if target_player:
                        vote_count[target] = vote_count.get(target, 0) + 1
                    else:
                        target = None
                except (ValueError, TypeError):
                    target = None

            vote_msg = f"投票给 {target_player.seat_number}号" if target_player else "弃票"
            await self.emit_event(GameEvent(
                game_id=self.game.id,
                round_number=self.round,
                phase="day_vote",
                player_id=pid,
                event_type="vote",
                public_content=f"{voter.seat_number}号 {voter.player_name} {vote_msg}",
                internal_thought=decision.internal_thought,
                reasoning_content=decision.reasoning,
            ))
            self.memory.add_conversation(self.round, "day_vote", f"{voter.seat_number}号{voter.player_name}", vote_msg, "vote")
            self.stats.record_vote(voter.id, target_player.id if target_player else None, target_player.role if target_player else None, voter.role)

        self.phase = "elimination"
        max_votes = max(vote_count.values()) if vote_count else 0
        if max_votes > 0:
            top_candidates = [k for k, v in vote_count.items() if v == max_votes]
            if len(top_candidates) == 1:
                eliminated_id = int(top_candidates[0])
                eliminated_player = next((p for p in self.players if p.id == eliminated_id), None)
                if eliminated_player:
                    role_display = (
                        "狼人" if eliminated_player.role == "werewolf"
                        else "预言家" if eliminated_player.role == "seer"
                        else "女巫" if eliminated_player.role == "witch"
                        else "猎人" if eliminated_player.role == "hunter"
                        else "村民"
                    )
                    elim_msg = f"{eliminated_player.seat_number}号 {eliminated_player.player_name} 被放逐出局，身份是：{role_display}。"
                    self.memory.add_conversation(self.round, "elimination", eliminated_player.player_name, elim_msg, "elimination")

                    await self.emit_event(GameEvent(
                        game_id=self.game.id,
                        round_number=self.round,
                        phase="elimination",
                        player_id=eliminated_player.id,
                        event_type="elimination",
                        public_content=elim_msg,
                    ))

                    is_hunter = eliminated_player.role == "hunter" and self.hunter_can_shoot
                    eliminated_player.is_alive = False
                    await self._sync_player_death(eliminated_id)

                    if is_hunter:
                        await self._trigger_hunter_shoot([eliminated_id], "vote")
            else:
                await self.emit_event(GameEvent(
                    game_id=self.game.id,
                    round_number=self.round,
                    phase="elimination",
                    event_type="elimination",
                    public_content="平票，本轮无人被放逐。",
                ))
        else:
            await self.emit_event(GameEvent(
                game_id=self.game.id,
                round_number=self.round,
                phase="elimination",
                event_type="elimination",
                public_content="无人投票，本轮无人被放逐。",
            ))

        self.winner = self._check_winner()
        await self._emit_phase_change("elimination_end", "放逐阶段结束。")

    def _check_winner(self):
        alive_werewolves = sum(1 for p in self.players if p.role == "werewolf" and p.is_alive)
        alive_seers = sum(1 for p in self.players if p.role == "seer" and p.is_alive)
        alive_witches = sum(1 for p in self.players if p.role == "witch" and p.is_alive)
        alive_hunters = sum(1 for p in self.players if p.role == "hunter" and p.is_alive)
        alive_villagers = sum(1 for p in self.players if p.role == "villager" and p.is_alive)

        self.log(f"存活: 狼{alive_werewolves} 预{alive_seers} 巫{alive_witches} 猎{alive_hunters} 村{alive_villagers}")

        if alive_werewolves == 0:
            return "villagers"
        if alive_villagers == 0:
            return "werewolves"
        if alive_seers + alive_witches + alive_hunters == 0:
            return "werewolves"

        return None

    async def _emit_phase_change(self, phase: str, message: str):
        await self.emit_event(GameEvent(
            game_id=self.game.id,
            round_number=self.round,
            phase=phase,
            event_type="phase_change",
            public_content=message,
        ))

    async def _sync_player_death(self, player_id: int):
        async with async_session() as db:
            player = await db.get(GamePlayer, player_id)
            if player:
                player.is_alive = False
                await db.commit()

    def get_game_state(self) -> dict:
        return {
            "game_id": self.game.id,
            "phase": self.phase,
            "round_number": self.round,
            "winner": self.winner,
            "alive_players": [
                {
                    "id": p.id,
                    "name": p.player_name,
                    "seat_number": p.seat_number,
                    "role": p.role,
                    "is_alive": p.is_alive,
                }
                for p in self.players
            ],
            "log": self._log[-50:],
        }
