import logging
import os
import sys
from pathlib import Path
from pprint import pprint
from urllib.request import urlopen

import telegram
import yaml
from telegram import (LabeledPrice)
from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters, PreCheckoutQueryHandler)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

PATH = os.path.dirname(os.path.abspath(__file__))

"""
#	Load the config file
#	Set the Botname / Token
"""
config_file = PATH + '/config.yaml'
my_file = Path(config_file)
if my_file.is_file():
    with open(config_file, encoding="utf-8") as fp:
        config = yaml.load(fp)
else:
    pprint('config.yaml file does not exist.')
    sys.exit()

TELEGRAM_BOT_TOKEN = config['BOT_TOKEN2']
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "{0}" caused error "{1}"'.format(update, error))


def start_callback(bot, update):
    msg = "Use /invoice to get an invoice for payment. "
    update.message.reply_text(msg)


def cybex_services_payment_callback(bot, update):
    chat_id = update.message.chat_id
    title = "CybeX Payment"
    description = "Payment bot to use cybex services"
    payload = "CybeX-Payload"
    # In order to get a provider_token see https://core.telegram.org/bots/payments#getting-a-token
    provider_token = "PROVIDER_TOKEN"
    start_parameter = "test-payment"
    currency = "CNY"  # TODO I don't know if telegram accepts this
    price = 100
    prices = [LabeledPrice("Test", price * 100)]
    bot.sendInvoice(chat_id, title, description, payload,
                    provider_token, start_parameter, currency, prices,
                    need_name=True, need_phone_number=True, is_flexible=True)


def precheckout_callback(bot, update):
    query = update.pre_checkout_query
    if query.invoice_payload != 'CybeX-Payload':
        bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=False,
                                      error_message="Something went wrong...")
    else:
        bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)


def successful_payment_callback(bot, update):
    my_path = "/Users/staniya/Desktop"
    photo_file = os.path.join(my_path, "cybex.png")
    update.message.reply_text('Thank you for your payment!',
                              img=urlopen('https://cdn-images-1.medium.com/max/800/1*_NCiwykMsFytkQFepO2opw.png'))


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(bot=bot)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # simple start function
    dp.add_handler(CommandHandler("start", start_callback))

    # Add command handler to start the payment invoice
    dp.add_handler(CommandHandler("invoice", cybex_services_payment_callback))

    # Pre-checkout handler to final check
    dp.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    # Success! Notify your user!
    dp.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
