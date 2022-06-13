from . import datastruct as _datastruct

import concurrent.futures as _cf
import requests as _requests
from requests.structures import CaseInsensitiveDict as _CaseInsensitiveDict
import pandas as _pd
from typing import Literal as _Literal, Optional as _Optional

class GGScraper:
    """Scrapes https://mobalytics.gg/ for both player and global matchup data.
    
    Attributes
    ----------
    SHA_*: str
        SHA-256 hashes used to scrape matchup data.
    df: pandas.DataFrame
        A dataframe containing champion ids and slugs.
    max_games: int
        The maximum number of matchups that can be scraped for a given summoner. Note that this cannot exceed the number of champions * 5.
    max_workers: int=5
        The maximum number of threads that can be used to make requests.
    """

    def __init__(self, SHA_C: str, SHA_M: str, max_games: int, max_workers: int=5):
        self.SHA_C = SHA_C
        self.SHA_M = SHA_M
        self.max_games = max_games
        self.max_workers = max_workers

    @property
    def df(self) -> _pd.DataFrame:
        """A dataframe containing champion ids and slugs."""

        if not hasattr(self, '_df'):
            url = "https://app.mobalytics.gg/api/league/gql/static/v1"
            champion_data = {
                "operationName":"LolCommonDataQuery",
                "variables":{},
                "query":"query LolCommonDataQuery {champions: queryChampionsV1Contents(top: 200) {\n    flatData {\n      ...ChampionCommonFragment\n      __typename\n    }\n    __typename}} \n fragment ChampionCommonFragment on ChampionsV1DataFlatDto {\n  slug\n  riotId\n  name\n  title\n  isInFreeRotation\n }"
            }
            
            headers = _CaseInsensitiveDict()
            headers["Content-Type"] = "application/json"

            resp = _requests.post(url, headers=headers, json=champion_data)

            df = _pd.DataFrame(
                list(map(
                    lambda row: [row['flatData']['name'], row['flatData']['slug'], row['flatData']['riotId']], 
                    resp.json()['data']['champions'])
                ), 
                columns=['name', 'slug', 'id'])
            self._df = df

        return self._df

    def to_id(self, name: str) -> int:
        """Get the Riot ID of a champion by name."""

        return self.df.loc[self.df['name'] == name, 'id'].values[0]

    def from_id(self, riot_id: int) -> str:
        """Get a champion's name by their Riot ID."""

        return self.df.loc[self.df['id'] == riot_id, 'name'].values[0]

    def _get_pool(self, 
                  operation: _Literal["LolProfilePageChampionsPoolQuery", "LolProfilePageMatchupsPoolQuery"],
                  summoner: str,
                  region: _Literal["NA", "KR", "LAS", "BR", 
                                   "EUNE", "OCE", "RU", "JP", 
                                   "EUW", "LAN", "TR"],
                  name: _Optional[str] = None,
                  queue: _Optional[_Literal["NORMAL_DRAFT", "RANKED_SOLO", "RANKED_FLEX"]] = None,
                  role: _Optional[_Literal["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]] = None,
                  ) -> list[_datastruct.ChampionSummary]:

        riot_id = None if name is None else self.to_id(name)
        sha = self.SHA_C if operation == "LolProfilePageChampionsPoolQuery" else self.SHA_M
        mode = "Best" if operation == "LolProfilePageChampionsPoolQuery" else "Worst"
        data = {
            "operationName":operation,
            "variables":{
                "top":self.max_games,
                "mode":mode,
                "summonerName":summoner,
                "region":region,
                "cChampionId":riot_id,
                "cQueue":queue,
                "cRolename":role,
                "cSeasonId":None,
                "cSortDirection":"DESC",
                "cSortField":"GAMES",
                "skip":0
            },
            "extensions":{
                "persistedQuery":{
                    "version":1,
                    "sha256Hash":sha
                }
            }
        }

        url = "https://app.mobalytics.gg/api/lol/graphql/v1/query"
        headers = _CaseInsensitiveDict()
        headers["Content-Type"] = "application/json"

        resp = _requests.post(url, headers=headers, json=data)
        results = resp.json()['data']['lol']['player']['championsMatchups']['items']
        stats = []
        for result in results:
            stats.append(_datastruct.ChampionSummary(
                    self.from_id(result['championId']), result['role'],
                    result['csm'], result['goldDiff15'], 
                    result['kda']['k'], result['kda']['d'], result['kda']['a'],
                    result['damagePerMinute'], result['kp'],
                    result['looses'], result['wins'], result['lp']
                )
            )
        
        return stats

    def get_champion_pool(self,
                          summoner: str, 
                          region: _Literal["NA", "KR", "LAS", "BR", 
                                           "EUNE", "OCE", "RU", "JP", 
                                           "EUW", "LAN", "TR"],
                          name: _Optional[str] = None,
                          queue: _Optional[_Literal["NORMAL_DRAFT", "RANKED_SOLO", "RANKED_FLEX"]] = None,
                          role: _Optional[_Literal["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]] = None,
                          ) -> list[_datastruct.ChampionSummary]:
        """Get the champion pool for a specific summoner as a list of ChampionSummary objects."""
        return self._get_pool("LolProfilePageChampionsPoolQuery", summoner, region, name, queue, role)

    def get_matchup_pool(self, 
                         summoner: str, 
                         region: _Literal["NA", "KR", "LAS", "BR", 
                                          "EUNE", "OCE", "RU", "JP", 
                                          "EUW", "LAN", "TR"],
                         name: _Optional[str] = None,
                         queue: _Optional[_Literal["NORMAL_DRAFT", "RANKED_SOLO", "RANKED_FLEX"]] = None,
                         role: _Optional[_Literal["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]] = None,
                         ) -> list[_datastruct.ChampionSummary]:
        """Get the matchup pool for a specific summoner as a list of ChampionSummary objects."""
        return self._get_pool("LolProfilePageMatchupsPoolQuery", summoner, region, name, queue, role)

    def _fetch(self, future: _cf.Future) -> list[_datastruct.ChampionSummary] | None:
        try: 
            return future.result()
        except Exception:
            return None

    def inform(self, team: _datastruct.Composition) -> bool:
        """Finish the initialization of SummonerInformation objects contained within Composition objects. Return a boolean for whether all initializations succeeded."""

        # use concurrency to fetch all of the relevant data
        with _cf.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            
            fs = {
                # get champion pools
                executor.submit(self.get_champion_pool, team.top.name, team.top.region, role="TOP"):'top.champion_pool',
                executor.submit(self.get_champion_pool, team.jungle.name, team.jungle.region, role="JUNGLE"):'jungle.champion_pool',
                executor.submit(self.get_champion_pool, team.mid.name, team.mid.region, role="MID"):'mid.champion_pool',
                executor.submit(self.get_champion_pool, team.adc.name, team.adc.region, role="ADC"):'adc.champion_pool',
                executor.submit(self.get_champion_pool, team.support.name, team.support.region, role="SUPPORT"):'support.champion_pool',
                # get matchup pools
                executor.submit(self.get_matchup_pool, team.top.name, team.top.region, role="TOP"):'top.matchup_pool',
                executor.submit(self.get_matchup_pool, team.jungle.name, team.jungle.region, role="JUNGLE"):'jungle.matchup_pool',
                executor.submit(self.get_matchup_pool, team.mid.name, team.mid.region, role="MID"):'mid.matchup_pool',
                executor.submit(self.get_matchup_pool, team.adc.name, team.adc.region, role="ADC"):'adc.matchup_pool',
                executor.submit(self.get_matchup_pool, team.support.name, team.support.region, role="SUPPORT"):'support.matchup_pool',
            }

            ps = _cf.as_completed(fs)
            for f in ps:
                role, pool = fs[f].split('.')
                setattr(getattr(team, role), pool, self._fetch(f))

        return all(info for info in team)