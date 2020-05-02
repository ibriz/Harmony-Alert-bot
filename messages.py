from conf import BotConfig


def startMessage(first_name):
    reply_text = "Hi " + first_name + ",\nWelcome to " + BotConfig.BOT_NAME + "\n\nTo start Enter you ONE address."
    return reply_text
