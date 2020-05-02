def getBalance(address):
    balance = {"jsonrpc": "2.0",
               "method": "hmyv2_getBalance",
               "params": [address],
               "id": 1
               }

    return balance


def getStakingInfo():
    networkInfo = {"jsonrpc": "2.0",
                   "method": "hmyv2_getStakingNetworkInfo",
                   "params": [],
                   "id": 1
                   }
    return networkInfo


def getEpoch():
    epoch = {"jsonrpc": "2.0",
             "method": "hmyv2_getEpoch",
             "params": [],
             "id": 1
             }

    return epoch


def getLatestHeader():
    blocks = {"jsonrpc": "2.0", "method": "hmyv2_latestHeader", "params": [], "id": 1}
    return blocks


def getElectedValidatorAddresses():
    electedAddress = {"jsonrpc": "2.0",
                      "method": "hmyv2_getElectedValidatorAddresses",
                      "params": [],
                      "id": 1
                      }

    return electedAddress


def getValidatorInformation(address):
    validatorInfo = {"jsonrpc": "2.0",
                     "method": "hmyv2_getValidatorInformation",
                     "params": [address],
                     "id": 1
                     }

    return validatorInfo


def getDelegationsByValidator(address):
    delegationsValidator = {"jsonrpc": "2.0",
                            "method": "hmyv2_getDelegationsByValidator",
                            "params": [address],
                            "id": 1
                            }

    return delegationsValidator


def getDelegationsByDelegator(address):
    delegationsDelegator = {"jsonrpc": "2.0",
                            "method": "hmyv2_getDelegationsByDelegator",
                            "params": [address],
                            "id": 1
                            }
    return delegationsDelegator


def getTxnByBlock(blockNumber):
    txns = {"jsonrpc": "2.0",
            "method": "hmyv2_getBlockByNumber",
            "params": [blockNumber, {"fullTx": True,
                                     "inclTx": True,
                                     "withSigners": True,
                                     }],
            "id": 1
            }

    return txns
