from itl.datastruct import *
from itl.scraper import *

import os
from dotenv import load_dotenv

load_dotenv()
SHA_C = os.environ["SHA_C"]
SHA_M = os.environ["SHA_M"]

GG = GGScraper(SHA_C, SHA_M, 200)
ally = Composition('NA', 'kal1brate', 'Fizsie', 'thef1tnessgram', 'AmbientSolace', 'imwangingrn')
assert GG.inform(ally)
for summary in ally.support.champion_pool:
    print(summary)