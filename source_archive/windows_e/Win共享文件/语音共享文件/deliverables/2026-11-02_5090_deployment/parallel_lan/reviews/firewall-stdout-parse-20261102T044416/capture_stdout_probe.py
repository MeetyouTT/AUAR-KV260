import json
import sys

print(json.dumps({"adapter": {"alias": "\u4ee5\u592a\u7f51"}, "sentinel": "after_alias"},
                 ensure_ascii=sys.argv[1] == "ascii", indent=2))
