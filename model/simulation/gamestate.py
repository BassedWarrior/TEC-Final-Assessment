from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Outcome:
    """Possible outcomes of a plate appearance, with their canonical string codes."""

    STRIKEOUT = "K"
    WALK = "BB"
    HIT_BY_PITCH = "HBP"
    SINGLE = "1B"
    DOUBLE = "2B"
    TRIPLE = "3B"
    HOME_RUN = "HR"
    OUT_IN_PLAY = "OUT"
    DOUBLE_PLAY = "DP"  # 2 outs (removes forced runner from 1B + batter)
    SAC_FLY = "SF"  # 1 out + the runner on 3B scores


@dataclass
class GameState:
    """Mutable state of a baseball game: inning, half-inning, outs, bases, scores and batter indices."""

    inning: int = 1
    is_top: bool = True
    outs: int = 0
    bases: tuple[bool, bool, bool] = (False, False, False)
    home_score: int = 0
    away_score: int = 0

    home_batter_idx: int = 0
    away_batter_idx: int = 0

    @property
    def batting_team_score(self) -> int:
        return self.away_score if self.is_top else self.home_score

    @property
    def fielding_team_score(self) -> int:
        return self.home_score if self.is_top else self.away_score

    def _add_runs(self, runs: int) -> None:
        if self.is_top:
            self.away_score += runs
        else:
            self.home_score += runs

    def _advance_batter(self) -> None:
        if self.is_top:
            self.away_batter_idx = (self.away_batter_idx + 1) % 9
        else:
            self.home_batter_idx = (self.home_batter_idx + 1) % 9

    def _end_half_inning(self) -> None:
        """Clear the bases, reset outs, switch half-inning."""
        self.bases = (False, False, False)
        self.outs = 0
        if self.is_top:
            self.is_top = False
        else:
            self.is_top = True
            self.inning += 1

    def _sac_fly_roll(self, prob: float = 0.30) -> bool:
        import random

        return random.random() < prob

    def _extra_base_roll(self, prob: float = 0.30) -> bool:
        """Return True with probability `prob` (runner takes an extra base)."""
        import random

        return random.random() < prob

    def apply_outcome(self, outcome: Outcome) -> int:
        """Apply a plate-appearance outcome to the state (advancing runners, scoring runs, recording outs) and return the number of runs scored."""
        runs_scored = 0
        on1b, on2b, on3b = self.bases

        if outcome == Outcome.STRIKEOUT:
            self.outs += 1

        # Generic out: only the batter is retired (no scoring; the sac fly is
        # now its own explicit class).
        elif outcome == Outcome.OUT_IN_PLAY:
            self.outs += 1

        # Double play: if there is a forced runner on 1B and fewer than 2 outs, the
        # runner on 1B and the batter are retired (2 outs, clears 1B); the runner on
        # 3B scores if present. If there is no force or there are already 2 outs, it
        # is a simple out of the batter.
        elif outcome == Outcome.DOUBLE_PLAY:
            if on1b and self.outs < 2:
                self.outs += 2
                if on3b:
                    runs_scored += 1
                self.bases = (False, on2b, False)  # 1B out, 3B scored/empty, 2B stays
            else:
                self.outs += 1

        # Sac fly: 1 out; the runner on 3B scores (tag-up). If there is no runner
        # on 3B, it is a simple fly-out.
        elif outcome == Outcome.SAC_FLY:
            self.outs += 1
            if on3b:
                runs_scored += 1
                self.bases = (on1b, on2b, False)

        elif outcome == Outcome.WALK or outcome == Outcome.HIT_BY_PITCH:
            if on1b and on2b and on3b:
                runs_scored += 1  # bases loaded, the runner on 3B scores
                self.bases = (True, True, True)
            elif on1b and on2b:
                self.bases = (True, True, True)
            elif on1b:
                self.bases = (True, True, on3b)
            else:
                self.bases = (True, on2b, on3b)

        elif outcome == Outcome.SINGLE:
            if on3b:
                runs_scored += 1
            if on2b:
                runs_scored += 1
            # new_2b = on1b
            # self.bases = (True, new_2b, False)
            # We found that the probability of a runner on first reaching third on a single is 30%
            if on1b and self._extra_base_roll():
                # Extra advance: runner from 1B reaches 3B
                self.bases = (True, False, True)
            else:
                # Normal advance: runner from 1B (if any) goes to 2B
                new_2b = on1b
                self.bases = (True, new_2b, False)

        elif outcome == Outcome.DOUBLE:
            if on3b:
                runs_scored += 1
            if on2b:
                runs_scored += 1
            new_3b = on1b
            self.bases = (False, True, new_3b)

        elif outcome == Outcome.TRIPLE:
            runs_scored += sum([on1b, on2b, on3b])
            self.bases = (False, False, True)

        elif outcome == Outcome.HOME_RUN:
            # Everyone scores plus the batter
            runs_scored += sum([on1b, on2b, on3b]) + 1
            self.bases = (False, False, False)

        else:
            raise ValueError(f"Outcome desconocido: {outcome}")

        self._add_runs(runs_scored)
        self._advance_batter()

        if self.outs >= 3:
            self._end_half_inning()

        return runs_scored

    def is_game_over(self) -> bool:
        """Return True if the game has ended (regulation, walk-off or resolved extra innings)."""
        # If we have not yet reached the end of the 9th, it is not over
        if self.inning < 9:
            return False

        # Walk-off: we are in the bottom of the 9th+ and the home team is ahead
        if self.inning >= 9 and not self.is_top and self.home_score > self.away_score:
            return True

        if self.inning >= 10 and self.is_top and self.home_score != self.away_score:
            # The previous inning (bottom of N-1) ended with different scores
            return True

        return False

    def copy(self) -> "GameState":
        """Return a shallow copy of this GameState (bases tuple is immutable)."""
        return GameState(
            inning=self.inning,
            is_top=self.is_top,
            outs=self.outs,
            bases=self.bases,  # tuple is immutable, no deepcopy needed
            home_score=self.home_score,
            away_score=self.away_score,
            home_batter_idx=self.home_batter_idx,
            away_batter_idx=self.away_batter_idx,
        )

    def __repr__(self) -> str:
        half = "Top" if self.is_top else "Bot"
        b1 = "X" if self.bases[0] else "-"
        b2 = "X" if self.bases[1] else "-"
        b3 = "X" if self.bases[2] else "-"
        return (
            f"<{half} {self.inning} | {self.outs} outs | "
            f"bases [{b1}{b2}{b3}] | "
            f"score H{self.home_score}-A{self.away_score}>"
        )
