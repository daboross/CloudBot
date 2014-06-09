import json

from cloudbot import hook, http
from cloudbot.util.formatting import FormattedString, Color, Bold


@hook.command(autohelp=False)
def mcstatus():
    """- gets the status of various Mojang (Minecraft) servers"""

    try:
        request = http.get("http://status.mojang.com/check")
    except (http.URLError, http.HTTPError) as e:
        return "Unable to get Minecraft server status: {}".format(e)

    # lets just reformat this data to get in a nice format
    data = json.loads(request.replace("}", "").replace("{", "").replace("]", "}").replace("[", "{"))

    out = []

    # use a loop so we don't have to update it if they add more servers
    green = []
    yellow = []
    red = []
    for server, status in list(data.items()):
        if status == "green":
            green.append(server)
        elif status == "yellow":
            yellow.append(server)
        else:
            red.append(server)

    if green:
        out = Bold.on(Color.green("Online: ")) + ", ".join(green)
        if yellow:
            out += " "
    if yellow:
        out += Bold.on(Color.green("Issues: ")) + ", ".join(yellow)
        if red:
            out += " "
    if red:
        out += Bold.on(Color.green("Offline: ")) + ", ".join(red)

    out = FormattedString(out).render()

    return "\x0f" + out.replace(".mojang.com", ".mj") \
        .replace(".minecraft.net", ".mc")
