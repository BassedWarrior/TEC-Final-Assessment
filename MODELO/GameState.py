from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class Outcome:
    STRIKEOUT ="K"
    WALK = "BB"
    HIT_BY_PITCH = "HBP"
    SINGLE = "1B"
    DOUBLE = "2B"
    TRIPLE = "3B"
    HOME_RUN = "HR"
    OUT_IN_PLAY = "OUT"


@dataclass
class GameState:
    inning: int=1
    is_top: bool= True
    outs: int=0
    bases: tuple[bool, bool, bool]= (False,False,False)
    home_score: int =0
    away_score: int=0
    
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
        """Limpia bases, resetea outs, cambia de half-inning."""
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
        """Devuelve True con probabilidad `prob` (runner toma base extra)."""
        import random
        return random.random() < prob
    
    def apply_outcome (self, outcome: Outcome) ->int :
        runs_scored=0
        on1b, on2b, on3b= self.bases
        
        if outcome==Outcome.STRIKEOUT:
            self.outs+=1
           
        #Sac_fly 
        elif outcome == Outcome.OUT_IN_PLAY:
            if on3b and self.outs < 2 and self._sac_fly_roll():
                runs_scored += 1
                self.bases = (on1b, on2b, False)  # 3B se vacía
            self.outs += 1
        
        elif outcome==Outcome.WALK or outcome==Outcome.HIT_BY_PITCH:
            if on1b and on2b and on3b:
                runs_scored += 1  # bases llenas, anota el de 3ra
                self.bases = (True, True, True)
            elif on1b and on2b:
                self.bases = (True, True, True)
            elif on1b:
                self.bases = (True, True, on3b)
            else:
                self.bases = (True, on2b, on3b)
        
        elif outcome==Outcome.SINGLE:
            if on3b:
                runs_scored += 1
            if on2b:
                runs_scored += 1
            # new_2b = on1b
            # self.bases = (True, new_2b, False)
            # Encontramos que la probabilidad de que un corredor en primera llegue a tercer con un sinlge es del 30%
            if on1b and self._extra_base_roll():
                # Avance extra: runner de 1B llega a 3B
                self.bases = (True, False, True)
            else:
                # Avance normal: runner de 1B (si existe) va a 2B
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
            
        elif outcome==Outcome.HOME_RUN:
            #Anotan todos y el bateador 
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
        
        # Si todavía no llegamos al final del 9°, no termina
        if self.inning < 9:
            return False

        # Walk-off: estamos en bottom del 9°+ y el local va arriba
        if self.inning >= 9 and not self.is_top and self.home_score > self.away_score:
            return True

        if self.inning >= 10 and self.is_top and self.home_score != self.away_score:
            # Acabó el inning previo (bottom del N-1) con scores distintos
            return True

        return False
    
    def copy(self) -> "GameState":
        return GameState(
            inning=self.inning,
            is_top=self.is_top,
            outs=self.outs,
            bases=self.bases,  # tuple es inmutable, no necesita deepcopy
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
        
