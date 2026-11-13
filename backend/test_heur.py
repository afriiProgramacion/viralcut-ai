import asyncio
from app.services.analysis import _heuristic_analyze
res = _heuristic_analyze(20.0, [], 2, 10, "mixed")
import pprint; pprint.pprint(res)
print(type(res), type(res[0]))