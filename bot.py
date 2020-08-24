#!/usr/bin/env python

try:
    from datetime import datetime
    import re

    from telegram import Update
    from telegram.ext import Updater
    from telegram.ext import Filters
    from telegram.ext import CallbackContext
    from telegram.ext import MessageHandler
    from telegram.ext import CommandHandler
    from telegram.ext import ConversationHandler
    from telegram.utils.request import Request
    from telegram import Bot

    import config
    from helpers import validate_flight_code, validate_date
    from helpers import get_logger
    from helpers import validate_and_save

except ImportError as e:
    raise ImportError(f'Error occurred during import: {e}\
    Please install all necessary libraries and try again')


FLIGHT_CODE = 1
DATE = 2

logger = get_logger(
        logger_name="zvartnots_bot",
        file_name="log.log",
        )


def log_error(func):
    def inner(*args, **kwargs):
        try:
            logger.info(f"Calling function {func.__name__}")
            result = func(*args, **kwargs)
            logger.info(f"Finished function {func.__name__}")
            return result
        except Exception as e:
            logger.exception(f"Exception during {func.__name__} call: {e}")
            raise e
    return inner


@log_error
def do_help(update: Update, context: CallbackContext):
    reply = "My purpose is to inform you about the flights you are interested in.\
            \nYou can create alerts on flights using the /add_alert command.\
            \nType /add_alert to get started."
    update.message.reply_text(
            text=reply,
    )


@log_error
def do_start(update: Update, context: CallbackContext):
    reply = f"Hey {update.message.from_user.first_name}. Welcome onboard.\
            \nTo begin, type /help."
    update.message.reply_text(
            text=reply,
    )


@log_error
def add_alert(update: Update, context: CallbackContext):
    if not hasattr(update, "message"):
        return
    if not hasattr(update.message, "text"):
        return
    # If plain add_alert is supplied, then process the conversation handler
    if len(context.args) == 0:
        context.bot.send_message(
                chat_id=update.message.chat_id,
                text="All right, lets start.\
                    \nIf you do any mistakes, type /cancel and start over.\
                    \nor /add_alert to reset.\
                    \nNow type your flight code."
                )
        return FLIGHT_CODE
    else:
        context.bot.send_message(
                chat_id=update.message.chat_id,
                text="Not sure if I get you right :/\
                        \nTry /add_alert and follow the instructions or\
                        \n hit /help for reference.",
                        )


@log_error
def flight_code_handler(update: Update, context: CallbackContext):
    if not hasattr(update, "message"):
        return
    if not hasattr(update.message, "text"):
        return
    try:
        flight_data = validate_flight_code(update.message.text)
    except ValueError:
        context.bot.send_message(
                chat_id=update.message.chat_id,
                text="Looks like there is an error in flight code.\
                        \nTry again or hit /cancel to cancel.",
                )
        return FLIGHT_CODE
    context.user_data[FLIGHT_CODE] = flight_data 
    context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"Flight code registered.\
            \nNow enter the date in the following format: DD/MM/YYYY",
            )
    return DATE


@log_error
def date_handler(update: Update, context: CallbackContext):
    if not hasattr(update, "message"):
        return
    if not hasattr(update.message, "text"):
        return
    try:
        date = validate_date(update.message.text)
    except ValueError:
        context.bot.send_message(
                chat_id=update.message.chat_id,
                text="Looks like there is an error in date.\
                        \nTry again or hit /cancel to cancel.",
                        )
        return DATE
    context.user_data[DATE] = date
    context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"Date registered.\
                    \nLet me take a look at that",
            )
    data = context.user_data.copy()
    context.user_data.clear()

    try:
        curr_state = validate_and_save(data[FLIGHT_CODE], data[DATE])
    except ValueError as e:
        context.bot.send_message(
                chat_id=update.message.chat_id,
                text=f"{' '.join(e.args)}",
                )
    else:
        context.bot.send_message(
                chat_id=update.message.chat_id,
                text=curr_state,
                )
    return ConversationHandler.END


@log_error
def cancel_handler(update: Update, context: CallbackContext):
    context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Canceled. Use /add_alert to start over",
            )
    return ConversationHandler.END


def main():
    req = Request(
            connect_timeout=5,
            )
    bot = Bot(
            token=config.TG_TOKEN,
            request=req,
            )

    updater = Updater(
            bot=bot,
            use_context=True,
            )
    bot_get_me = updater.bot.get_me()

    print(f"Bot {bot_get_me.first_name} is live now")

    conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("add_alert", add_alert),
            ],
            states={
                FLIGHT_CODE: [
                    MessageHandler(
                        Filters.text & (~Filters.command), 
                        flight_code_handler, 
                        pass_user_data=True),
                ],
                DATE: [
                    MessageHandler(
                        Filters.text & (~Filters.command), 
                        date_handler, 
                        pass_user_data=True
                        ),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", cancel_handler),
            ],
            allow_reentry=True,
            )
    help_handler = CommandHandler("help", do_help)
    start_handler = CommandHandler("start", do_start)
    updater.dispatcher.add_handler(start_handler, 1)
    updater.dispatcher.add_handler(help_handler, 1)
    updater.dispatcher.add_handler(conv_handler, 2)

    # Start listening
    updater.start_polling()
    updater.idle()
    print("Finish")
    # answer to all - Filters.all
    # answer to text only - Filters.text


if __name__ == "__main__":
    main()
