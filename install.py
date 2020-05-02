import requests
from pymongo import MongoClient
import urllib.parse

from conf import BotApi
from settings import *


def dbConfig():
    mongodb_username = urllib.parse.quote_plus('xxx')
    mongodb_password = urllib.parse.quote_plus('xxx')
    mongodb_client = MongoClient('mongodb://%s:%s@xxx.xxx.xxx.xxx/admin' % (mongodb_username, mongodb_password))
    mydb = mongodb_client["xxx-xxx"]

    return mydb


def getWalletBalance(wallet_address):
    balance_api = requests.post(BotApi.openStaking, json=getBalance(wallet_address)).json()

    wallet_balance = format(balance_api['result'] // 10 ** 18, '>7,d')

    return wallet_balance


def getValidatorName(validator_address):
    validatorInfo = requests.post(BotApi.openStaking, json=getValidatorInformation(validator_address)).json()['result']
    validator_name = "\n<b>" + validatorInfo['validator']['name'] + "</b>"

    return validator_name


def EpochNumber():
    epoch = requests.post(BotApi.openStaking, json=getEpoch()).json()['result']
    return epoch


def latestHeader():
    headers = requests.post(BotApi.openStaking, json=getLatestHeader()).json()['result']
    return headers


def getStakingNetwork():
    utilities = requests.post(BotApi.openStaking, json=getStakingInfo()).json()['result']
    return utilities


def getElectedValidators():
    electedValidators = requests.post(BotApi.openStaking, json=getElectedValidatorAddresses()).json()['result']
    validatorInfo = requests.post(BotApi.openStaking, json=getValidatorInformation(electedValidators[-1])).json()

    return validatorInfo['result']['total-delegation'] // 10 ** 18


def getEpochStatus():
    validator_address = dbConfig().Validator.distinct('address')
    epos_status = {}
    for i in range(0, len(validator_address)):
        validatorInfo = \
            requests.post(BotApi.openStaking, json=getValidatorInformation(validator_address[i])).json()['result']

        epos_status[validator_address[i]] = [validatorInfo['epos-status'],
                                             float(validatorInfo['validator']['rate']) * 100]

    return epos_status


def getBlockSignings(validator_address):
    validatorInfo = requests.post(BotApi.openStaking, json=getValidatorInformation(validator_address)).json()['result']
    currentEpochStatus = validatorInfo['current-epoch-performance']['current-epoch-signing-percent']
    validatorStatus = validatorInfo['lifetime']['blocks']

    total_to_sign = validatorStatus['to-sign']
    total_signed = validatorStatus['signed']

    total_missedBlocks = total_to_sign - total_signed

    current_to_sign = currentEpochStatus['current-epoch-to-sign']
    current_signed_blocks = currentEpochStatus['current-epoch-signed']

    current_missedBlocks = current_to_sign - current_signed_blocks

    return [current_missedBlocks, total_missedBlocks]


def getDelegationMonitor(validator_address):
    validatorInfo = requests.post(BotApi.openStaking, json=getValidatorInformation(validator_address)).json()['result']
    return validatorInfo['validator']['delegations']


def getValidatorInfo(address):
    validatorInfo = requests.post(BotApi.openStaking, json=getValidatorInformation(address)).json()['result']

    median_raw_stake = float(getStakingNetwork()['median-raw-stake']) // 10 ** 18

    validator_name = "------------------------------------\n<b>" + validatorInfo['validator']['name'] + "</b>"
    validator_identity = "\n<i>" + validatorInfo['validator']['details'] + "</i>"

    validator_fee = "\nFees : " + str(float(validatorInfo['validator']['rate']) * 100) + "%"

    total_delgations = "\n\nTotal Delegations: " + str(format(validatorInfo['total-delegation'] // 10 ** 18, ">7,d"))

    change_in_stake = float(validatorInfo['total-delegation'] // 10 ** 18) - median_raw_stake
    deflection_stake = "\nMedian Deviation: " + str(float('%.2f' % ((change_in_stake * 100) / median_raw_stake))) + "%"
    effective_stake = "\nEffective Stake : "

    if validatorInfo['currently-in-committee']:
        in_Committee = "\nIn Committee: " + '✅'
    else:
        in_Committee = "\nIn Committee: " + '❌'

    epoch_status = validatorInfo['epos-status']
    if epoch_status == 'currently elected':
        epoch_status = '✅'
        epoch_uptime = float('%.2f' % float(validatorInfo['current-epoch-performance']['current-epoch-signing-percent'][
                                                'current-epoch-signing-percentage'])) * 100
        effective_stake += str(
            format(int(float(validatorInfo['metrics']['by-bls-key'][0]['key']['effective-stake']) // 10 ** 18), ">7,d"))

    elif epoch_status == 'eligible to be elected next epoch':
        epoch_status = "<code>Eligible for next epoch</code> ⏲"
        effective_stake += '--'
        epoch_uptime = "0"

    else:
        epoch_status = "<code>Not eligible for next epoch</code>"
        epoch_uptime = "0"
        effective_stake += '--'

    if validatorInfo['lifetime']['blocks']['to-sign'] == 0:
        avg_uptime = 0
    else:
        avg_uptime = (validatorInfo['lifetime']['blocks']['signed'] * 100) / validatorInfo['lifetime']['blocks'][
            'to-sign']

    validator_status_text = validator_name + validator_identity + validator_fee + total_delgations + effective_stake + \
                            "\nMedian Raw Stake : " + str(format(int(median_raw_stake), ">7,d")) + deflection_stake + \
                            "\n\nElected Status:  " + epoch_status + in_Committee + "\n\nCurrent Epoch Uptime: " + \
                            str(epoch_uptime) + "%\nAverage Uptime: " + str(float('%.2f' % avg_uptime)) + "%\n"

    return validator_status_text


def getDelegations(wallet_address):
    delegations = requests.post(BotApi.openStaking, json=getDelegationsByDelegator(wallet_address)).json()['result']

    return delegations


def getTransactionsByBlockNumber(blockHeight):
    transactions = requests.post(BotApi.openStaking, json=getTxnByBlock(blockHeight)).json()['result']['transactions']

    return transactions
