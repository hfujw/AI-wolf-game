"""MVP/SVP 统计追踪器"""


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
