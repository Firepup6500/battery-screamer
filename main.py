# pylint: disable=redefined-builtin
from os import environ as env
from sys import exit
from requests import post
from requests.exceptions import ConnectionError
from dotenv import load_dotenv

# pylint: enable=redefined-builtin

load_dotenv()
if not env.get("SLACK_WEBHOOK_URL"):
    exit("Please set the slack webhook URL as SLACK_WEBHOOK_URL in your .env file.")
cacheData = {
    "old_state": "N/A",
    "raw_old_percent": 0,
    "old_percent": 0,
    "runsSinceLastLog": 0,
}
try:
    from cache import cacheData
except ImportError:
    ...

# pylint: disable=pointless-string-statement
# Data example, from slack
"""
{
  "hostname": "Example text",
  "percent": "Example text",
  "change": "Example text",
  "state": "Example text",
  "runs": "Example text",
}
"""
# pylint: enable=pointless-string-statement


def writeCache(cache: dict) -> None:
    with open("cache.py", "w", encoding="utf-8") as file:
        file.write(f"cacheData = {cache}")


cacheData["runsSinceLastLog"] += 1
writeCache(cacheData)
data = {
    "hostname": b"\xe2\x80\xad".decode("utf-8").join(
        list(__import__("platform").node())
    ),
    "runs": str(cacheData["runsSinceLastLog"]),
}
tmpData = {}
with open("/sys/class/power_supply/BAT0/status", "r", encoding="utf-8") as state:
    data["state"] = state.read().strip().lower()

with open("/sys/class/power_supply/BAT0/charge_now", "r", encoding="utf-8") as charge:
    tmpData["current"] = int(charge.read().strip())

with open("/sys/class/power_supply/BAT0/charge_full", "r", encoding="utf-8") as full:
    tmpData["full"] = int(full.read().strip())

tmpData["raw_percent"] = (tmpData["current"] / tmpData["full"]) * 100
data["percent"] = str(round(tmpData["raw_percent"], 2))
if (
    data["state"] == cacheData["old_state"]
    and tmpData["raw_percent"] > 15
    and cacheData["raw_old_percent"] > 15
    and cacheData["runsSinceLastLog"] < 5
):
    exit()

tmpData["percent_change"] = round(
    tmpData["raw_percent"] - cacheData["raw_old_percent"], 2
)
if tmpData["percent_change"] > 0:
    data["change"] = (
        f"up from {cacheData['old_percent']}% (+{tmpData['percent_change']}%)"
    )
elif tmpData["percent_change"] < 0:
    data["change"] = (
        f"down from {cacheData['old_percent']}% ({tmpData['percent_change']}%)"
    )
else:
    data["change"] = "no change"

try:
    post(env["SLACK_WEBHOOK_URL"], json=data, timeout=10)
    writeCache(
        {
            "old_state": data["state"],
            "raw_old_percent": tmpData["raw_percent"],
            "old_percent": data["percent"],
            "runsSinceLastLog": 0,
        }
    )
except ConnectionError:
    cacheData["runsSinceLastLog"] += 1
    writeCache(cacheData)
    exit("Failed to post to webhook")
