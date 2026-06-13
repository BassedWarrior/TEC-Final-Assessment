"""
Seed the `teams` and `lineups` tables with hand-authored MLB lineups.

Each team carries its official MLB Stats API team id and a `lineup_id` group;
every player slot lands in `lineups` tagged with that same lineup_id, the
batting order, an is_batter flag (True = batter, False = pitcher) and the
resolved MLBAM player id.

Lineups are written by hand below (real rosters, approximate). Player ids are
NOT hardcoded: each name is resolved against the already-seeded `players` table
(accent/case-insensitive). Any name missing from players is reported and skipped
— so run `seed_players` first, and expect a few skips for sub-threshold players.

Usage (from the backend/ directory):
    python -m app.db.scripts.seed_players      # must run first
    python -m app.db.scripts.seed_lineups
"""

import asyncio
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # adds backend/ to path

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.base import engine
from app.models.player import Player
from app.models.team import Team
from app.models.lineup import Lineup

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# A complete lineup is 9 batters + a 4-man pitching staff (starter + bullpen).
# Hand-authored names missing from `players` (injuries, sub-threshold PA) leave
# gaps; we backfill those from real teammates so no team is left incomplete.
TARGET_BATTERS = 9
TARGET_PITCHERS = 4


# Each team: official MLB team id, full name, 9 batters in order, then pitchers
# (starter first, the rest bullpen). lineup_id is assigned by position below.
TEAMS = [
    {
        "id": 147, "name": "New York Yankees",
        "batters": ["Trent Grisham", "Aaron Judge", "Cody Bellinger",
                    "Giancarlo Stanton", "Jazz Chisholm Jr.", "Anthony Volpe",
                    "Austin Wells", "Paul Goldschmidt", "Jasson Domínguez"],
        "pitchers": ["Max Fried", "Devin Williams", "Luke Weaver", "Ian Hamilton"],
    },
    {
        "id": 111, "name": "Boston Red Sox",
        "batters": ["Jarren Duran", "Rafael Devers", "Alex Bregman",
                    "Trevor Story", "Wilyer Abreu", "Triston Casas",
                    "Ceddanne Rafaela", "Connor Wong", "Masataka Yoshida"],
        "pitchers": ["Garrett Crochet", "Aroldis Chapman", "Liam Hendriks",
                     "Justin Slaten"],
    },
    {
        "id": 110, "name": "Baltimore Orioles",
        "batters": ["Gunnar Henderson", "Adley Rutschman", "Ryan O'Hearn",
                    "Cedric Mullins", "Anthony Santander", "Jordan Westburg",
                    "Colton Cowser", "Ramón Urías", "Jackson Holliday"],
        "pitchers": ["Zach Eflin", "Félix Bautista", "Yennier Cano",
                     "Cionel Pérez"],
    },
    {
        "id": 139, "name": "Tampa Bay Rays",
        "batters": ["Yandy Díaz", "Brandon Lowe", "Josh Lowe",
                    "Isaac Paredes", "Junior Caminero", "José Caballero",
                    "Christopher Morel", "Ben Rortvedt", "Jonny DeLuca"],
        "pitchers": ["Shane McClanahan", "Pete Fairbanks", "Jason Adam",
                     "Garrett Cleavinger"],
    },
    {
        "id": 141, "name": "Toronto Blue Jays",
        "batters": ["George Springer", "Bo Bichette", "Vladimir Guerrero Jr.",
                    "Anthony Santander", "Daulton Varsho", "Alejandro Kirk",
                    "Ernie Clement", "Andrés Giménez", "Davis Schneider"],
        "pitchers": ["José Berríos", "Jeff Hoffman", "Chad Green",
                     "Yimi García"],
    },
    {
        "id": 114, "name": "Cleveland Guardians",
        "batters": ["Steven Kwan", "José Ramírez", "Josh Naylor",
                    "Lane Thomas", "Bo Naylor", "Kyle Manzardo",
                    "Andrés Giménez", "Gabriel Arias", "Brayan Rocchio"],
        "pitchers": ["Tanner Bibee", "Emmanuel Clase", "Cade Smith",
                     "Hunter Gaddis"],
    },
    {
        "id": 116, "name": "Detroit Tigers",
        "batters": ["Riley Greene", "Kerry Carpenter", "Spencer Torkelson",
                    "Colt Keith", "Gleyber Torres", "Jake Rogers",
                    "Parker Meadows", "Trey Sweeney", "Zach McKinstry"],
        "pitchers": ["Tarik Skubal", "Jason Foley", "Tyler Holton",
                     "Will Vest"],
    },
    {
        "id": 118, "name": "Kansas City Royals",
        "batters": ["Maikel Garcia", "Bobby Witt Jr.", "Vinnie Pasquantino",
                    "Salvador Perez", "MJ Melendez", "Michael Massey",
                    "Hunter Renfroe", "Kyle Isbel", "Freddy Fermin"],
        "pitchers": ["Cole Ragans", "Lucas Erceg", "Carlos Estévez",
                     "John Schreiber"],
    },
    {
        "id": 142, "name": "Minnesota Twins",
        "batters": ["Carlos Correa", "Byron Buxton", "Trevor Larnach",
                    "Matt Wallner", "Royce Lewis", "Ryan Jeffers",
                    "Willi Castro", "Edouard Julien", "Brooks Lee"],
        "pitchers": ["Pablo López", "Jhoan Duran", "Griffin Jax",
                     "Cole Sands"],
    },
    {
        "id": 145, "name": "Chicago White Sox",
        "batters": ["Andrew Benintendi", "Luis Robert Jr.", "Andrew Vaughn",
                    "Miguel Vargas", "Lenyn Sosa", "Gavin Sheets",
                    "Korey Lee", "Nicky Lopez", "Brooks Baldwin"],
        "pitchers": ["Garrett Crochet", "Jordan Leasure", "Steven Wilson",
                     "Justin Anderson"],
    },
    {
        "id": 117, "name": "Houston Astros",
        "batters": ["Jose Altuve", "Yordan Alvarez", "Kyle Tucker",
                    "Alex Bregman", "Yainer Diaz", "Jeremy Peña",
                    "Christian Walker", "Jake Meyers", "Mauricio Dubón"],
        "pitchers": ["Framber Valdez", "Josh Hader", "Bryan Abreu",
                     "Ryan Pressly"],
    },
    {
        "id": 140, "name": "Texas Rangers",
        "batters": ["Marcus Semien", "Corey Seager", "Wyatt Langford",
                    "Adolis García", "Nathaniel Lowe", "Josh Jung",
                    "Jonah Heim", "Evan Carter", "Josh Smith"],
        "pitchers": ["Nathan Eovaldi", "Kirby Yates", "Chris Martin",
                     "José Leclerc"],
    },
    {
        "id": 136, "name": "Seattle Mariners",
        "batters": ["Julio Rodríguez", "Cal Raleigh", "Randy Arozarena",
                    "Jorge Polanco", "Luke Raley", "Mitch Garver",
                    "J.P. Crawford", "Dylan Moore", "Victor Robles"],
        "pitchers": ["Logan Gilbert", "Andrés Muñoz", "Matt Brash",
                     "Gabe Speier"],
    },
    {
        "id": 108, "name": "Los Angeles Angels",
        "batters": ["Mike Trout", "Taylor Ward", "Logan O'Hoppe",
                    "Anthony Rendon", "Jo Adell", "Nolan Schanuel",
                    "Zach Neto", "Luis Rengifo", "Mickey Moniak"],
        "pitchers": ["Tyler Anderson", "Ben Joyce", "Robert Stephenson",
                     "José Soriano"],
    },
    {
        "id": 133, "name": "Athletics",
        "batters": ["Lawrence Butler", "Brent Rooker", "JJ Bleday",
                    "Tyler Soderstrom", "Shea Langeliers", "Seth Brown",
                    "Max Muncy", "Zack Gelof", "Miguel Andujar"],
        "pitchers": ["JP Sears", "Mason Miller", "Lucas Erceg",
                     "T.J. McFarland"],
    },
    {
        "id": 119, "name": "Los Angeles Dodgers",
        "batters": ["Shohei Ohtani", "Mookie Betts", "Freddie Freeman",
                    "Teoscar Hernández", "Will Smith", "Max Muncy",
                    "Tommy Edman", "Gavin Lux", "Andy Pages"],
        "pitchers": ["Yoshinobu Yamamoto", "Tyler Glasnow", "Blake Treinen",
                     "Evan Phillips"],
    },
    {
        "id": 137, "name": "San Francisco Giants",
        "batters": ["Willy Adames", "Heliot Ramos", "Matt Chapman",
                    "Jung Hoo Lee", "Mike Yastrzemski", "LaMonte Wade Jr.",
                    "Patrick Bailey", "Tyler Fitzgerald", "Wilmer Flores"],
        "pitchers": ["Logan Webb", "Ryan Walker", "Camilo Doval",
                     "Tyler Rogers"],
    },
    {
        "id": 135, "name": "San Diego Padres",
        "batters": ["Fernando Tatis Jr.", "Luis Arraez", "Manny Machado",
                    "Xander Bogaerts", "Jackson Merrill", "Jake Cronenworth",
                    "Kyle Higashioka", "Jurickson Profar", "Ha-Seong Kim"],
        "pitchers": ["Dylan Cease", "Robert Suarez", "Jeremiah Estrada",
                     "Yuki Matsui"],
    },
    {
        "id": 109, "name": "Arizona Diamondbacks",
        "batters": ["Ketel Marte", "Corbin Carroll", "Eugenio Suárez",
                    "Christian Walker", "Joc Pederson", "Lourdes Gurriel Jr.",
                    "Gabriel Moreno", "Geraldo Perdomo", "Alek Thomas"],
        "pitchers": ["Zac Gallen", "Justin Martinez", "A.J. Puk",
                     "Kevin Ginkel"],
    },
    {
        "id": 115, "name": "Colorado Rockies",
        "batters": ["Brenton Doyle", "Ezequiel Tovar", "Ryan McMahon",
                    "Kris Bryant", "Charlie Blackmon", "Elias Díaz",
                    "Michael Toglia", "Jordan Beck", "Nolan Jones"],
        "pitchers": ["Kyle Freeland", "Tyler Kinley", "Jake Bird",
                     "Victor Vodnik"],
    },
    {
        "id": 121, "name": "New York Mets",
        "batters": ["Francisco Lindor", "Juan Soto", "Pete Alonso",
                    "Brandon Nimmo", "Mark Vientos", "Jeff McNeil",
                    "Starling Marte", "Francisco Alvarez", "Luis Torrens"],
        "pitchers": ["Kodai Senga", "Edwin Díaz", "Reed Garrett",
                     "José Buttó"],
    },
    {
        "id": 143, "name": "Philadelphia Phillies",
        "batters": ["Kyle Schwarber", "Trea Turner", "Bryce Harper",
                    "Nick Castellanos", "J.T. Realmuto", "Alec Bohm",
                    "Bryson Stott", "Brandon Marsh", "Johan Rojas"],
        "pitchers": ["Zack Wheeler", "Jordan Romano", "Matt Strahm",
                     "Orion Kerkering"],
    },
    {
        "id": 144, "name": "Atlanta Braves",
        "batters": ["Ronald Acuña Jr.", "Ozzie Albies", "Austin Riley",
                    "Matt Olson", "Marcell Ozuna", "Michael Harris II",
                    "Sean Murphy", "Jarred Kelenic", "Orlando Arcia"],
        "pitchers": ["Chris Sale", "Raisel Iglesias", "Pierce Johnson",
                     "Joe Jiménez"],
    },
    {
        "id": 146, "name": "Miami Marlins",
        "batters": ["Xavier Edwards", "Jesús Sánchez", "Jake Burger",
                    "Connor Norby", "Jesús Aguilar", "Otto Lopez",
                    "Nick Fortes", "Derek Hill", "Dane Myers"],
        "pitchers": ["Sandy Alcantara", "Calvin Faucher", "Anthony Bender",
                     "Declan Cronin"],
    },
    {
        "id": 120, "name": "Washington Nationals",
        "batters": ["CJ Abrams", "Luis García Jr.", "Dylan Crews",
                    "James Wood", "Keibert Ruiz", "Nathaniel Lowe",
                    "Josh Bell", "Alex Call", "Jacob Young"],
        "pitchers": ["MacKenzie Gore", "Kyle Finnegan", "Jordan Weems",
                     "Derek Law"],
    },
    {
        "id": 158, "name": "Milwaukee Brewers",
        "batters": ["Jackson Chourio", "William Contreras", "Christian Yelich",
                    "Rhys Hoskins", "Willy Adames", "Sal Frelick",
                    "Garrett Mitchell", "Brice Turang", "Joey Ortiz"],
        "pitchers": ["Freddy Peralta", "Devin Williams", "Trevor Megill",
                     "Joel Payamps"],
    },
    {
        "id": 112, "name": "Chicago Cubs",
        "batters": ["Ian Happ", "Seiya Suzuki", "Cody Bellinger",
                    "Dansby Swanson", "Nico Hoerner", "Christopher Morel",
                    "Pete Crow-Armstrong", "Michael Busch", "Miguel Amaya"],
        "pitchers": ["Justin Steele", "Porter Hodge", "Héctor Neris",
                     "Tyson Miller"],
    },
    {
        "id": 113, "name": "Cincinnati Reds",
        "batters": ["TJ Friedl", "Matt McLain", "Elly De La Cruz",
                    "Jeimer Candelario", "Jonathan India", "Spencer Steer",
                    "Tyler Stephenson", "Jake Fraley", "Santiago Espinal"],
        "pitchers": ["Hunter Greene", "Alexis Díaz", "Emilio Pagán",
                     "Fernando Cruz"],
    },
    {
        "id": 134, "name": "Pittsburgh Pirates",
        "batters": ["Oneil Cruz", "Bryan Reynolds", "Ke'Bryan Hayes",
                    "Andrew McCutchen", "Joey Bart", "Isiah Kiner-Falefa",
                    "Jared Triolo", "Michael A. Taylor", "Nick Gonzales"],
        "pitchers": ["Paul Skenes", "David Bednar", "Colin Holderman",
                     "Aroldis Chapman"],
    },
    {
        "id": 138, "name": "St. Louis Cardinals",
        "batters": ["Brendan Donovan", "Lars Nootbaar", "Nolan Arenado",
                    "Willson Contreras", "Alec Burleson", "Nolan Gorman",
                    "Masyn Winn", "Iván Herrera", "Michael Siani"],
        "pitchers": ["Sonny Gray", "Ryan Helsley", "JoJo Romero",
                     "Andrew Kittredge"],
    },
]


def _norm(name: str) -> str:
    """Lowercase + strip diacritics so 'José Ramírez' matches 'Jose Ramirez'."""
    decomposed = unicodedata.normalize("NFKD", name)
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return no_accents.casefold().strip()


async def seed():
    async with AsyncSessionLocal() as db:
        # Load every seeded player once: a name->id index for resolving the
        # hand-authored names, plus per-team candidate pools (sorted by playing
        # time) used to backfill gaps with real teammates.
        result = await db.execute(
            select(Player.id, Player.name, Player.team, Player.is_batter, Player.pa_count)
        )
        name_to_id: dict[str, int] = {}
        pool: dict[tuple[str, bool], list[tuple[float, int, str]]] = {}
        for pid, pname, pteam, is_bat, pa in result.all():
            name_to_id.setdefault(_norm(pname), pid)
            pool.setdefault((pteam, bool(is_bat)), []).append((pa or 0.0, pid, pname))
        for cands in pool.values():
            cands.sort(reverse=True)  # most plate appearances / batters faced first

        if not name_to_id:
            print("players table is empty — run `seed_players` first. Aborting.")
            return

        teams: list[Team] = []
        lineups: list[Lineup] = []
        missing: list[str] = []
        backfilled: list[str] = []

        for idx, team in enumerate(TEAMS):
            lineup_id = idx + 1
            teams.append(Team(id=team["id"], name=team["name"], lineup_id=lineup_id))

            used: set[int] = set()
            order = {True: 0, False: 0}

            def add_slot(pid: int, is_batter: bool):
                used.add(pid)
                order[is_batter] += 1
                lineups.append(Lineup(
                    lineup_id=lineup_id,
                    team_id=team["id"],
                    batting_order=order[is_batter],
                    is_batter=is_batter,
                    player_id=pid,
                ))

            # 1) Hand-authored slots: batters in order, then the pitching staff.
            slots = (
                [(n, True) for n in team["batters"]]
                + [(n, False) for n in team["pitchers"]]
            )
            for name, is_batter in slots:
                pid = name_to_id.get(_norm(name))
                if pid is None:
                    missing.append(f"{team['name']}: {name}")
                    continue
                if pid in used:
                    continue  # same player listed twice for this team
                add_slot(pid, is_batter)

            # 2) Backfill any shortfall from real teammates not already used.
            for is_batter, target in ((True, TARGET_BATTERS), (False, TARGET_PITCHERS)):
                for _pa, pid, pname in pool.get((team["name"], is_batter), []):
                    if order[is_batter] >= target:
                        break
                    if pid in used:
                        continue
                    add_slot(pid, is_batter)
                    role = "batter" if is_batter else "pitcher"
                    backfilled.append(f"{team['name']}: {pname} ({role})")

        # lineups FK -> teams, so wipe children first; CASCADE covers any leftovers.
        await db.execute(text("TRUNCATE TABLE lineups, teams RESTART IDENTITY CASCADE"))
        db.add_all(teams)
        await db.flush()  # insert parents before children
        db.add_all(lineups)
        await db.commit()

    print(f"Seeded {len(teams)} teams and {len(lineups)} lineup slots "
          f"({len(backfilled)} backfilled from teammates).")
    if missing:
        print(f"\n{len(missing)} hand-authored names not in `players` (replaced by backfill):")
        for m in missing:
            print(f"  - {m}")
    if backfilled:
        print(f"\n{len(backfilled)} slots backfilled with real teammates:")
        for b in backfilled:
            print(f"  - {b}")


if __name__ == "__main__":
    asyncio.run(seed())
