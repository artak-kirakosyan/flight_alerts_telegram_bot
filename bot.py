"""
This module contains all the functions that the bot has.

"""
try:
    import datetime
    import threading

    import telegram.utils.request
    import telegram
    import telegram.ext as tg_ext

    import config
    import helpers
    import common

except ImportError as exc:
    raise ImportError("Error occurred during import: %s" % (exc,))


FLIGHT_CODE = 1
DATE = 2

logger = common.get_logger(
    logger_name="BOT",
    file_name=config.BOT_LOG_PATH,
)


def log_error(func):
    """
    Decorator for the func. Logs the function calls and exceptions if any.
    """
    def inner(*args, **kwargs):
        """
        Inner function of the decorator.
        """
        try:
            logger.info("Calling function %s" % (func.__name__,))
            result = func(*args, **kwargs)
            logger.info("Finished function %s" % (func.__name__,))
            return result
        except Exception as e:
            logger.exception("Exception during %s call" % (func.__name__,))
            raise e
    return inner


@log_error
def do_start(update: telegram.Update, context: tg_ext.CallbackContext):
    """
    Welcomes the user when start command is executed.
    """
    if not hasattr(update, "message"):
        return
    if not hasattr(update.message, "text"):
        return

    reply = "Hey %s. Welcome onboard.\
            \nTo begin, type /help." % (update.message.from_user.first_name,)
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=reply,
    )


@log_error
def do_help(update: telegram.Update, context: tg_ext.CallbackContext):
    """
    Process the help command. Gives a message to the user on how to use
    the bot
    """
    if not hasattr(update, "message"):
        return
    if not hasattr(update.message, "text"):
        return
    reply = "I can inform you about the flights you are interested in.\
            \nYou can create alerts on flights using the /add_alert command.\
            \nType /add_alert to get started.\
            \n\n----------Demo----------\n\
            \n/add_alert\
            \nB2 734\
            \n%s" % (datetime.datetime.now().strftime('%d/%m/%Y'),)
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=reply,
    )


@log_error
def add_alert(update: telegram.Update, context: tg_ext.CallbackContext):
    """
    The start point of the add_alert conversation.
    Ask the user for flight code and trigger the conversation handler's next
    state
    """
    if not hasattr(update, "message"):
        return
    if not hasattr(update.message, "text"):
        return
    # If plain add_alert is supplied, then process the conversation handler
    if len(context.args) == 0:
        context.user_data["chat_id"] = update.message.chat_id
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="All right, lets start. Type your flight code\
                \nIf you do any mistakes, type /cancel and start over.\
                \nor /add_alert to reset."
        )
        return FLIGHT_CODE
    # @TODO support the full supply as well: flight_code date time all at once
    else:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Not sure if I get you right :/\
                \nTry /add_alert and follow the instructions or\
                \n hit /help for reference.",
        )


@log_error
def flight_code_handler(
        update: telegram.Update,
        context: tg_ext.CallbackContext):
    """
    Second state of the conversation. Validate the flight code, if valid,
    proceed to date, else ask for another flight code.
    """
    if not hasattr(update, "message"):
        return
    if not hasattr(update.message, "text"):
        return
    try:
        flight_data = helpers.process_flight_code(
            flight_code=update.message.text,
        )
    except ValueError as exception:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="".join(exception.args),
        )
        return FLIGHT_CODE

    context.user_data["flight_data"] = flight_data

    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="Flight code registered.\
            \nNow enter the date in the following format: 25/08/2020",
    )
    return DATE


@log_error
def date_handler(
        update: telegram.Update,
        context: tg_ext.CallbackContext):
    """
    Last step of the conversation. Validate the date, if valid, process the
    request, else ask for another date.
    """
    if not hasattr(update, "message"):
        return
    if not hasattr(update.message, "text"):
        return
    try:
        date = helpers.process_date(update.message.text)
    except ValueError as exception:
        error_message = "".join(exception.args)
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Looks like there is an error in date: %s.\
                \nTry again or hit /cancel to cancel." % (error_message,),
        )
        return DATE

    context.user_data["date"] = date
    data = context.user_data.copy()
    context.user_data.clear()
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="Date registered. Will send an update shortly",
    )
    kwargs = {
        "user_data": data,
        "bot": context.bot,
    }
    th = threading.Thread(
        target=helpers.validate_and_insert,
        kwargs=kwargs,
    )
    th.start()

    return tg_ext.ConversationHandler.END


@log_error
def cancel_handler(
        update: telegram.Update,
        context: tg_ext.CallbackContext):
    """
    Cancel the conversation of cancel command is supplied.
    """
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="Canceled. Use /add_alert to start over",
    )
    return tg_ext.ConversationHandler.END


def main():
    """
    The main function, which prepares the bot, the updater and dispatcher.
    Then start polling.
    """
    req = telegram.utils.request.Request(
        connect_timeout=5,
        con_pool_size=8,
    )
    bot = telegram.Bot(
        token=config.TG_TOKEN,
        request=req,
    )

    updater = tg_ext.Updater(
        bot=bot,
        use_context=True,
        )
    bot_get_me = updater.bot.get_me()

    print("Bot %s is live now." % (bot_get_me.first_name,))

    conv_handler = tg_ext.ConversationHandler(
        entry_points=[
            tg_ext.CommandHandler("add_alert", add_alert),
        ],
        states={
            FLIGHT_CODE: [
                tg_ext.MessageHandler(
                    tg_ext.Filters.text & (~tg_ext.Filters.command),
                    flight_code_handler,
                    pass_user_data=True
                ),
            ],
            DATE: [
                tg_ext.MessageHandler(
                    tg_ext.Filters.text & (~tg_ext.Filters.command),
                    date_handler,
                    pass_user_data=True
                ),
            ],
        },
        fallbacks=[
            tg_ext.CommandHandler("cancel", cancel_handler),
        ],
        allow_reentry=True,
    )
    help_handler = tg_ext.CommandHandler("help", do_help)
    start_handler = tg_ext.CommandHandler("start", do_start)
    updater.dispatcher.add_handler(start_handler, 1)
    updater.dispatcher.add_handler(help_handler, 1)
    updater.dispatcher.add_handler(conv_handler, 2)

    # Start listening
    updater.start_polling()
    updater.idle()
    print("Finish")


if __name__ == "__main__":
    main()
