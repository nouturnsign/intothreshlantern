from typing import NamedTuple as _NamedTuple

class ChampionSummary(_NamedTuple):
    """A summary of a champion as part of a matchup, either the champion being played or played against. See class definition for docstrings."""
    
    champion: str # champion being played or champion being played against
    role: str # role
    csm: float # average cs per minute
    gd15: float # average gold difference at 15 minutes
    k: float # average number of kills
    d: float # average number of deaths
    a: float # average number of assists
    dpm: float # average damage per minute
    kp: float # average kill participation
    losses: int # number of losses
    wins: int # number of wins
    lp: int # change in lp from games of ranked

class SummonerInformation:
    """An object that is partially initialized without champion pool and matchup pool.
    
    Attributes
    ----------
    region: str
        The region where the summoner plays.
    name: str
        The username of the summoner.
    champion_pool: Iterable[ChampionSummary]
        The list of ChampionSummary objects. Does not initially exist.
    matchup_pool: Iterable[ChampionSummary]
        The list of ChampionSummary objects. Does not initially exist.
        
    Notes
    -----
    Casting to bool returns whether the object has been completely initialized. 
    Attempts to reassign attributes after initialization raise a TypeError.
    """

    __slots__ = ['region', 'name', 'champion_pool', 'matchup_pool']

    def __init__(self, region: str, name: str):
        self.region = region
        self.name = name

    def __setattr__(self, attr, value):
        if hasattr(self, attr):
            raise TypeError("'SummonerInformation' does not support item reassignment")
        if attr in ('champion_pool', 'matchup_pool'):
            try:
                check = all(isinstance(stats, ChampionSummary) for stats in value)
            except Exception:
                check = False
            if not check:
                raise TypeError(f"'{value}' should be an iterable of 'ChampionSummary' objects")
        super().__setattr__(attr, value)

    def __bool__(self):
        return (self.champion_pool is not None) and (self.matchup_pool is not None)

    def __repr__(self):
        return f"SummonerInformation{{region={self.region}, name={self.name}, champion_pool={getattr(self, 'champion_pool', None)}, matchup_pool={getattr(self, 'matchup_pool', None)}}}"

class Composition:
    """A standard 5-player team composition.
    
    Attributes
    ----------
    top, jungle, mid, adc, support: SummonerInformation
        The summoner information associated with each player.
        
    Notes
    -----
    Functions as a NamedTuple with a custom __init__ method.
    """

    __slots__ = ['top', 'jungle', 'mid', 'adc', 'support']

    def __init__(self, region: str, top: str, jungle: str, mid: str, adc: str, support: str):
        self.top = SummonerInformation(region, top)
        self.jungle = SummonerInformation(region, jungle)
        self.mid = SummonerInformation(region, mid)
        self.adc = SummonerInformation(region, adc)
        self.support = SummonerInformation(region, support)

    def __iter__(self):
        yield self.top
        yield self.jungle
        yield self.mid
        yield self.adc
        yield self.support

    def __repr__(self):
        return f'Composition{{top={self.top}, jungle={self.jungle}, mid={self.mid}, adc={self.adc}, support={self.support}}}'