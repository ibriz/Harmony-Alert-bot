from install import *
from conf import BotConfig
from messages import startMessage

import logging
from datetime import datetime, timedelta
from pytz import timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from telegram.error import Unauthorized, BadRequest

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

updater = Updater(BotConfig.TOKEN_API, use_context=True)
dispatcher = updater.dispatcher
job = updater.job_queue

validator_keyboard = [["Validator Status", 'Epoch Time'],
                      ["Rewards", 'Check Balance', "Market Status"], ["Faucet",
                                                                      "Undelegations"]]
menu_markup = ReplyKeyboardMarkup(validator_keyboard, resize_keyboard=True, selective=False)

wallet_address_confirm = {}

currentEpoch = EpochNumber()
currentStatus = getEpochStatus()
threshold_votes = getElectedValidators()


def welcomeMessage(update: Update, context: CallbackContext):
    chat_type = update.message.chat['type']
    first_name = update.message.chat['first_name']
    user_id = update.message.chat_id

    if chat_type == 'private':
        context.bot.send_message(chat_id=user_id,
                                 text=startMessage(first_name))
        wallet_address_confirm[user_id] = ""


def epochTimeRemaining(update: Update, context: CallbackContext):
    current_block = latestHeader()['blockNumber']
    last_epochBlock = getStakingNetwork()['epoch-last-block']

    block_remaining = last_epochBlock - current_block
    remaining_time = block_remaining * 8

    minutes_remaining, seconds_remaining = divmod(remaining_time, 60)
    hours_remaining, minutes_remaining = divmod(minutes_remaining, 60)

    utc_time_now = datetime.now(timezone(BotConfig.ktm_timezone))
    update_time = utc_time_now + timedelta(hours=hours_remaining, minutes=minutes_remaining,
                                           seconds=seconds_remaining)
    next_update_time = str(int(minutes_remaining)) + "mins  " + str(int(seconds_remaining)) + "seconds"

    update_message = "Next Epoch will start after: " + next_update_time

    context.bot.send_message(chat_id=update.message.chat_id,
                             text=update_message + " @ " + str(update_time)[0:16] + " UTC")


def epochChange(context: CallbackContext):
    global currentEpoch
    epoch = EpochNumber()

    total_supply = format(int(float(getStakingNetwork()['total-supply'])), ">7,d")
    circulating_supply = format(int(float(getStakingNetwork()['circulating-supply'])), ">7,d")

    total_staking = format(int(float(getStakingNetwork()['total-staking'] // 10 ** 18)), ">7,d")
    median_raw_stake = format(int(float(getStakingNetwork()['median-raw-stake'])) // 10 ** 18, ">7,d")

    if currentEpoch != epoch:
        currentEpoch = epoch

        global threshold_votes
        threshold_votes = getElectedValidators()

        validators = dbConfig().Validator.distinct('user_id')
        delegators = dbConfig().Delegator.distinct('user_id')
        users = list(dict.fromkeys(validators + delegators))

        for x in range(0, len(users)):
            context.bot.send_message(chat_id=users[x],
                                     text="EPOCH " + str(
                                         currentEpoch - 1) + " Completed\n-----------------------------" +
                                          "---\nCurrent Supply: " + str(circulating_supply) + " ONE\nTotal Supply: " +
                                          str(total_supply) + " ONE\n---------------------------------\n" +
                                          "Total Staking: " + str(total_staking) + " ONE\nEffective Median Stake: " +
                                          str(median_raw_stake) + " ONE")


def getDelegatedValidatorStatus(update: Update, context: CallbackContext):
    address = []
    validator_address = dbConfig().Validator.find({'user_id': update.message.chat_id},
                                                  {'address': "$address", "_id": 0})
    delegator_address = dbConfig().Delegator.find({'user_id': update.message.chat_id},
                                                  {'address': "$address", "_id": 0})
    for x in validator_address:
        address.append(x['address'])
    for y in delegator_address:
        address.append(y['address'])

    for i in range(0, len(address)):
        user_validators = "Address : " + address[i] + "\n"
        delegations = getDelegations(address[i])

        if len(delegations) != 0:
            for x in range(0, len(delegations)):
                if delegations[x]['amount'] != 0:
                    user_validators += getValidatorInfo(delegations[x]['validator_address'])

            context.bot.send_message(chat_id=update.message.chat_id,
                                     text=user_validators,
                                     parse_mode='html')

        else:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text="You haven't delegated any validators till now." +
                                          "<a href='https://staking.harmony.one/'> Visit Here</a> to delegate.",
                                     parse_mode='html',
                                     disable_web_page_preview=True)


def getUndelegations(update: Update, context: CallbackContext):
    address = []
    validator_address = dbConfig().Validator.find({'user_id': update.message.chat_id},
                                                  {'address': "$address", "_id": 0})
    delegator_address = dbConfig().Delegator.find({'user_id': update.message.chat_id},
                                                  {'address': "$address", "_id": 0})
    for x in validator_address:
        address.append(x['address'])
    for y in delegator_address:
        address.append(y['address'])

    for x in range(0, len(address)):
        delegations = getDelegations(address[x])

        reply_message = "You've a pending undelegation request of : "

        for i in range(0, len(delegations)):
            if len(delegations[i]['Undelegations']) != 0:
                undelegate_amount = format(delegations[i]['Undelegations'][0]['Amount'] // 10 ** 18, ">7,d")
                undelegate_epoch = delegations[i]['Undelegations'][0]['Epoch']

                remainingEpoch = (undelegate_epoch + 8) - currentEpoch

                reply_message += "\n\n" + str(undelegate_amount) + " ONE\nRequested Epoch: " + str(undelegate_epoch) + \
                                 "\nCurrent Epoch: " + str(currentEpoch) + "\n\nRemaining Epoch: " + str(remainingEpoch)

        if reply_message == "You've a pending undelegation request of \n":
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text="NO UNDELEGATIONS REQUEST")

        else:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text=reply_message)


def marketPlace(update: Update, context: CallbackContext):
    rates = requests.get(BotApi.coingecko_url).json()['market_data']

    one_usd_amount = float("%.5f" % float(rates['current_price']['usd']))
    one_btc_amount = str('{0:.8f}'.format(rates['current_price']['btc']))

    total_supply = format(int(float(getStakingNetwork()['total-supply'])), ">7,d")
    circulating_supply = format(int(float(getStakingNetwork()['circulating-supply'])), ">7,d")

    total_staking = format(int(float(getStakingNetwork()['total-staking'] // 10 ** 18)), ">7,d")
    median_raw_stake = format(int(float(getStakingNetwork()['median-raw-stake'])) // 10 ** 18, ">7,d")

    reply_text = "<code>ONE/USD: " + str(one_usd_amount) + "\nONE/BTC: " + one_btc_amount + \
                 "\n\nTotal Supply: " + str(total_supply) + " ONE\nCirculating Supply: " + circulating_supply + \
                 " ONE\n\nTotal Staking: " + total_staking + " ONE\nMedian Raw Stake: " + median_raw_stake + \
                 " ONE</code>"

    context.bot.send_message(chat_id=update.message.chat_id,
                             text=reply_text,
                             parse_mode="HTML")


def walletBalance(update: Update, context: CallbackContext):
    validator_users = dbConfig().Validator.find({'user_id': update.message.chat_id}, {'address': "$address", "_id": 0})
    delegator_users = dbConfig().Delegator.find({'user_id': update.message.chat_id}, {'address': "$address", "_id": 0})

    address = []
    for x in validator_users:
        address.append(x['address'])
    for y in delegator_users:
        address.append(y['address'])

    for i in range(0, len(address)):
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text="<code>Address: </code><b>" + address[i] + "</b>\n\n<code>Wallet Balance: " +
                                      "</code><b>" + str(getWalletBalance(address[i])) + " ONE</b>",
                                 parse_mode="HTML")


def voteLoader(context: CallbackContext):
    validators = dbConfig().Validator.distinct('address')
    new_validators = dbConfig().Votes.distinct('validator_address')

    list_difference = []
    for item in validators:
        if item not in new_validators:
            list_difference.append(item)

    if len(list_difference) > 0:
        for i in range(0, len(list_difference)):
            delegations = getDelegationMonitor(list_difference[i])
            for voters in range(0, len(delegations)):
                address = delegations[voters]['delegator-address']
                amount = float(delegations[voters]['amount'] // 10 ** 18)

                delegators = {"delegator_address": address,
                              "validator_address": list_difference[i],
                              "stake_amount": amount}
                dbConfig().Votes.insert_one(delegators)


def voteMonitor(context: CallbackContext):
    validators = dbConfig().Validator.distinct('address')
    for i in range(0, len(validators)):
        current_vote_dict, tracker_votes_dict = {}, {}
        votes_cursor = dbConfig().Votes.find({'validator_address': validators[i]})
        for x in votes_cursor:
            current_vote_dict[x['delegator_address']] = x['stake_amount']

        delegations = getDelegationMonitor(validators[i])
        for y in range(0, len(delegations)):
            tracker_votes_dict[delegations[y]['delegator-address']] = float(delegations[y]['amount'] // 10 ** 18)

        voter_text = "🗳<b><u>Delegation Monitor</u></b>🗳\n"

        try:
            if current_vote_dict != tracker_votes_dict:
                new_voter = {k: tracker_votes_dict[k] for k in set(tracker_votes_dict) - set(current_vote_dict)}
                less_voter = {k: current_vote_dict[k] for k in set(current_vote_dict) - set(tracker_votes_dict)}

                if len(new_voter) != 0:
                    voter_text += "\n❇❇️<b>New Delegator</b> ❇❇\n"
                    for key in new_voter:
                        dbConfig().Votes.insert_one(
                            {'delegator_address': key, 'validator_address': validators[i],
                             'stake_amount': tracker_votes_dict[key]})

                        voter_text += '\n' + key + " has delegated " + str(
                            format(int(tracker_votes_dict[key]), '>7,d')) + " ONE"

                if len(less_voter) != 0:
                    voter_text += "\n\n⛔️⛔️ <b>Undelegation</b> ⛔️⛔️\n"
                    for key in less_voter:
                        dbConfig().Votes.delete_one({'delegator_address': key})
                        voter_text += '\n' + key + " has undelegated <b>" + str(
                            format(int(current_vote_dict[key]), '>7,d')) + " ONE</b>"

                diff_keys = {key: tracker_votes_dict[key] - current_vote_dict[key] for key in tracker_votes_dict if
                             key in current_vote_dict}
                changes_dict = {key: v for key, v in diff_keys.items() if v != 0.0}

                if len(changes_dict) != 0:
                    voter_text += "\n\n🔺🔻<b> Change in Delegation </b>🔺🔻\n"
                    for key in changes_dict:
                        dbConfig().Votes.delete_one({'delegator_address': key})
                        dbConfig().Votes.insert_one(
                            {'delegator_address': key, 'validator_address': validators[i],
                             'stake_amount': tracker_votes_dict[key]})

                        diff_in_vote = tracker_votes_dict[key] - current_vote_dict[key]
                        if diff_in_vote < 0:
                            diff_in_vote = " ONE</b> (🔻️️ <b>" + str(format(int(diff_in_vote), '>7,d')) + " ONE</b>🔻)"
                        else:
                            diff_in_vote = " ONE</b> (🔺<b>" + str(format(int(diff_in_vote), '>7,d')) + " ONE</b> 🔺)"

                        voter_text += '\n' + key + " has changed their delegations from <b>" + \
                                      str(format(int(current_vote_dict[key]), '>7,d')) + " ONE</b> to <b>" + \
                                      str(format(int(tracker_votes_dict[key]), '>7,d')) + diff_in_vote

                users = dbConfig().Validator.find({'address': validators[i]}, {'user_id': "$user_id", "_id": 0})
                for numbers in users:
                    context.bot.send_message(chat_id=numbers['user_id'],
                                             text=voter_text,
                                             parse_mode='HTML')
        except Exception as err:
            print(err)


def stateChange(context: CallbackContext):
    validators = dbConfig().Validator.distinct('address')


def thresholdVotes(context: CallbackContext):
    validators = dbConfig().Validator.distinct('address')

    for i in range(0, len(validators)):
        total_votes = 0
        for j in range(0, len(getDelegationMonitor(validators[i]))):
            total_votes += getDelegationMonitor(validators[i])[j]['amount'] // 10 ** 18

        changePercent = ((total_votes - threshold_votes) * 100) / total_votes

        if changePercent < 20.0:
            users = dbConfig().Validator.find({'address': validators[i]}, {'user_id': "$user_id", "_id": 0})
            for numbers in users:
                context.bot.send_message(chat_id=numbers['user_id'],
                                         text="You got only " + str(float(
                                             '%.2f' % changePercent)) + "% more delegations than the last elected " +
                                              "validator.Stake more to be in committee for the next epoch.",
                                         parse_mode='HTML')


# def blockSignings(context: CallbackContext):
#     total_missed_blocks = str(getBlockSignings(validator_address)[1])
#     current_missed_blocks = str(getBlockSignings(validator_address)[0])
#
#     text_reply = "\n\n⛔️⛔️ Node is Offline\n\nTotal Missed Blocks: " + total_missed_blocks + \
#                  "\nCurrent Epoch Missed Blocks: " + current_missed_blocks
#
#     context.bot.send_message(chat_id=631133527,
#                              text=text_reply,
#                              parse_mode="HTML")


def totalRewards(update: Update, context: CallbackContext):
    validator_users = dbConfig().Validator.find({'user_id': update.message.chat_id}, {'address': "$address", "_id": 0})
    delegator_users = dbConfig().Delegator.find({'user_id': update.message.chat_id}, {'address': "$address", "_id": 0})

    address = []
    for x in validator_users:
        address.append(x['address'])
    for y in delegator_users:
        address.append(y['address'])

    for i in range(0, len(address)):
        rewards_dict = getDelegations(address[i])
        total_rewards = 0.0
        rewards_text = "<b>Rewards</b>\n\nAddress : " + address[i] + "\n"
        for j in range(0, len(rewards_dict)):
            rewards_text += getValidatorName(rewards_dict[j]['validator_address']) + " : " + str(
                float(rewards_dict[j]['reward'] // 10 ** 18)) + " ONE"
            total_rewards += float(rewards_dict[j]['reward'] // 10 ** 18)

        context.bot.send_message(chat_id=update.message.chat_id,
                                 text=rewards_text + "\n\nTotal Rewards : " + str(int(total_rewards)) + "  ONE",
                                 parse_mode='html')


def userContextsReply(update: Update, context: CallbackContext):
    if update.edited_message is not None:
        chat_id = update.edited_message['chat']['id']
        chat_type = update.edited_message['chat']['type']
        updateMessage = update.edited_message

    else:
        chat_id = update.message.chat_id
        chat_type = update.message.chat['type']
        updateMessage = update.message

    user_text = updateMessage.text
    first_name = updateMessage.chat['first_name']

    if chat_type == 'private':
        if user_text == "Validator Status":
            getDelegatedValidatorStatus(update, context)

        elif user_text == 'Epoch Time':
            epochTimeRemaining(update, context)

        elif user_text == "Undelegations":
            getUndelegations(update, context)

        elif user_text == "Rewards":
            totalRewards(update, context)

        elif user_text == "Check Balance":
            walletBalance(update, context)

        elif user_text == "Market Status":
            marketPlace(update, context)

        elif user_text == "Faucet":
            context.bot.send_message(chat_id=chat_id,
                                     text="Sorry, Faucet Not available Now. ")

        if len(user_text) == 42:
            if user_text.startswith('one'):
                if chat_id in wallet_address_confirm.keys():
                    try:
                        getValidatorInfo(user_text)
                        wallets = dbConfig().Validator.distinct('user_id')
                        if chat_id not in wallets:
                            dbConfig().Validator.insert_one({"user_id": chat_id, 'address': user_text})

                            context.bot.send_message(chat_id=chat_id,
                                                     text="Hi " + first_name + ",\nYou have successfully added \n<b>" +
                                                          user_text + "</b>\n" + getValidatorInfo(user_text) +
                                                          "\nPlease check the buttons on the drawer below.",
                                                     reply_markup=menu_markup,
                                                     parse_mode='HTML')

                            del wallet_address_confirm[chat_id]

                        else:
                            context.bot.send_message(chat_id=chat_id,
                                                     text="Hi " + first_name + ",\nYou have already added a " +
                                                          "validator address.",
                                                     parse_mode='HTML')

                    except KeyError:
                        if len(getDelegations(user_text)) == 0:
                            context.bot.send_message(chat_id=chat_id,
                                                     text="Please enter a valid Harmony ONE Address.")
                        else:
                            wallets = dbConfig().Delegator.distinct('user_id')
                            del wallet_address_confirm[chat_id]

                            if chat_id not in wallets:
                                dbConfig().Delegator.insert_one({"user_id": chat_id, 'address': user_text})
                                context.bot.send_message(chat_id=chat_id,
                                                         text="Hi " + first_name + ",\nYou have successfully added " +
                                                              "\n<b>" + user_text + "</b>.\nPlease check the buttons" +
                                                              " on the drawer below.",
                                                         reply_markup=menu_markup,
                                                         parse_mode='HTML')
                            else:
                                context.bot.send_message(chat_id=chat_id,
                                                         text="Hi " + first_name + ",\nYou have already added a " +
                                                              "delegator address.",
                                                         parse_mode='HTML')
                else:
                    pass


def main():
    dispatcher.add_handler(CommandHandler("start", welcomeMessage))

    dispatcher.add_handler(MessageHandler(Filters.text, userContextsReply))

    # job.run_repeating(epochChange, interval=8, first=0)
    # job.run_repeating(voteLoader, interval=120, first=0)
    # job.run_repeating(voteMonitor, interval=110, first=0)

    # job.run_repeating(thresholdVotes, interval=3000, first=4)
    job.run_repeating(stateChange, interval=3, first=0)


if __name__ == '__main__':
    try:
        main()
        updater.start_polling()
        updater.idle()

    except KeyboardInterrupt:
        exit()
