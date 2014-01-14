import json

from cloudbot import hook
from cloudbot.util import http


green_prefix = "\x02\x0f"
green_suffix = ": \x033\x02\u2714"
yellow_prefix = "\x02\x0f"
yellow_suffix = ": \x037\x02\u26A0"
red_prefix = "\x02\x0f"
red_suffix = ": \x034\x02\u2716"


@hook.command("mcs", "mcstatus", "mojang", autohelp=False)
def mcstatus():
    """- gets the status of various Mojang (Minecraft) servers"""

    try:
        result = http.get("http://status.mojang.com/check")
    except (http.URLError, http.HTTPError) as e:
        return "Unable to get Minecraft server status: {}".format(e)

    data = json.loads(result)

    # use a loop so we don't have to update it if they add more servers
    servers = []
    for server_dict in data:
        for server, status in server_dict.items():
            if server == "minecraft.net":
                server = "MC|Website"
            elif server.endswith(".mojang.com"):
                server = "MJ|{}".format(server[:-11].capitalize())
            elif server.endswith(".minecraft.net"):
                server = "MC|{}".format(server[:-14].capitalize())

            if status == "green":
                servers.append("{}{}{}".format(green_prefix, server, green_suffix))
            elif status == "yellow":
                servers.append("{}{}{}".format(yellow_prefix, server, yellow_suffix))
            else:
                servers.append("{}{}{}".format(red_prefix, server, red_suffix))
    return "  ".join(servers)
