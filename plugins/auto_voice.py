# """
# auto_voice.py - plugin that automatically voices people when they speak, and devoices them after a set amount of time.
# """
# from sqlalchemy import Table, Column, UniqueConstraint, String, DateTime
#
# from cloudbot import hook, botvars
#
# table = Table(
#     "auto_voice",
#     botvars.metadata,
#     Column("connection", String),
#     Column("channel", String),
#     Column("time", DateTime),
#     UniqueConstraint("connection", "channel")
# )
#
# # Default value.
# # If True, all channels without a setting will have regex enabled
# # If False, all channels without a setting will have regex disabled
# default_enabled = False
#
# # dict[(str, str), set[str]]
# # dict((connection, channel), set(voicing))
# voicing_dict = {}
#
# @hook.onload()
# def load_cache(db):
#     """
#     :type db: sqlalchemy.orm.Session
#     """
#     global time_cache
#     time_cache = {}
#     for row in db.execute(table.select()):
#         conn = row["connection"]
#         chan = row["channel"]
#         time = row["time"]
#         time_cache[(conn, chan)] = time
#
#
# def set_status(db, conn, chan, status):
#     """
#     :type db: sqlalchemy.orm.Session
#     :type conn: str
#     :type chan: str
#     :type status: str
#     """
#     if (conn, chan) in time_cache:
#         # if we have a set value, update
#         db.execute(
#             table.update().values(status=status).where(table.c.connection == conn).where(table.c.channel == chan))
#     else:
#         # otherwise, insert
#         db.execute(table.insert().values(connection=conn, channel=chan, status=status))
#     db.commit()
#
#
# def delete_status(db, conn, chan):
#     db.execute(table.delete().where(table.c.connection == conn).where(table.c.channel == chan))
#     db.commit()
#
#
# @hook.irc_raw("PRIVMSG")
# def autovoice_check(bot, event, _hook):
#     key = (event.conn.name, event.chan)
#     if key not in voicing_dict:
#         voicing_dict[key] = set()
#     voicing = voicing_dict[key]
#
#     status = time_cache.get((event.conn.name, event.chan))
#     if status != "ENABLED" and (status == "DISABLED" or not default_enabled):
#         bot.logger.info("[{}] Denying {} from {}".format(event.conn.readable_name, _hook.function_name, event.chan))
#         return None
#     bot.logger.info("[{}] Allowing {} to {}".format(event.conn.readable_name, _hook.function_name, event.chan))
#
#     return event
#
#
# @hook.command(autohelp=False, permissions=["botcontrol"])
# def enableregex(text, db, conn, chan, nick, message, notice):
#     text = text.strip().lower()
#     if not text:
#         channel = chan
#     elif text.startswith("#"):
#         channel = text
#     else:
#         channel = "#{}".format(text)
#
#     message("Enabling regex matching (youtube, etc) (issued by {})".format(nick), target=channel)
#     notice("Enabling regex matching (youtube, etc) in channel {}".format(channel))
#     set_status(db, conn.name, channel, "ENABLED")
#     load_cache(db)
#
#
# @hook.command(autohelp=False, permissions=["botcontrol"])
# def disableregex(text, db, conn, chan, nick, message, notice):
#     text = text.strip().lower()
#     if not text:
#         channel = chan
#     elif text.startswith("#"):
#         channel = text
#     else:
#         channel = "#{}".format(text)
#
#     message("Disabling regex matching (youtube, etc) (issued by {})".format(nick), target=channel)
#     notice("Disabling regex matching (youtube, etc) in channel {}".format(channel))
#     set_status(db, conn.name, channel, "DISABLED")
#     load_cache(db)
#
#
# @hook.command(autohelp=False, permissions=["botcontrol"])
# def resetregex(text, db, conn, chan, nick, message, notice):
#     text = text.strip().lower()
#     if not text:
#         channel = chan
#     elif text.startswith("#"):
#         channel = text
#     else:
#         channel = "#{}".format(text)
#
#     message("Resetting regex matching setting (youtube, etc) (issued by {})".format(nick), target=channel)
#     notice("Resetting regex matching setting (youtube, etc) in channel {}".format(channel))
#     delete_status(db, conn.name, channel)
#     load_cache(db)
#
#
# @hook.command(autohelp=False, permissions=["botcontrol"])
# def regexstatus(text, conn, chan):
#     text = text.strip().lower()
#     if not text:
#         channel = chan
#     elif text.startswith("#"):
#         channel = text
#     else:
#         channel = "#{}".format(text)
#     status = time_cache.get((conn.name, chan))
#     if status is None:
#         if default_enabled:
#             status = "ENABLED"
#         else:
#             status = "DISABLED"
#     return "Regex status for {}: {}".format(channel, status)
#
#
# @hook.command(autohelp=False, permissions=["botcontrol"])
# def listregex(conn):
#     values = []
#     for (conn_name, chan), status in time_cache.values():
#         if conn_name != conn.name:
#             continue
#         values.append("{}: {}".format(chan, status))
#     return ", ".join(values)
