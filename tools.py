"""
This module contains functions that are used to interact with the IOTA and Shimmer
network and send NFTs.

The module defines various constants, including the Shimmer wallet's passwords,
database names, account details, node URL, API key, subdomain, and delta_days.

It also defines a logger object that logs the events and errors generated by the module.

The module defines several functions, including check_if_sent, which checks if
the NFTs have already been sent to the specified addresses; send_nfts,
which sends NFTs to a single address; and write_to_csv, which writes
the transaction details to a CSV file.
"""
import requests
from iota_client import IotaClient
from iota_wallet import IotaWallet, StrongholdSecretManager
import logging
import sys
import traceback
import os
import environ
import time
import csv
import json
import random

env = environ.Env()
environ.Env.read_env()

# Global constants
stronghold_password = os.getenv("STRONGHOLD_PASSWORD")
stronghold_db_name = os.getenv("STRONGHOLD_DB_NAME")
wallet_db_name = os.getenv("WALLET_DB_NAME")
shimmer_mnemonic = os.getenv("SHIMMER_MNEMONIC")
shimmer_account_name = os.getenv("SHIMMER_ACCOUNT_NAME")
shimmer_address_hrp = os.getenv("SHIMMER_ADDRESS_HRP")
collection_nft_address = os.getenv("COLLECTION_NFT_ADDRESS")
collection_nft_id = os.getenv("COLLECTION_NFT_ID")
node_url = os.getenv("NODE_URL")
shimmer_address_sent_to_filename = os.getenv("SHIMMER_ADDRESS_SENT_TO_FILENAME")
x_api_key = env("ZEALY_API_KEY")
subdomain = env("ZEALY_SUBDOMAIN")
smr_address_quest_id = env("SMR_ADDRESS_QUEST_ID")
nft_drop_quest_id = env("NFT_DROP_QUEST_ID")

##########################
# Configure Logger
##########################
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# Create a file handler
file_handler = logging.FileHandler("app.log")
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

# Create a stream handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

# Add the stream handler to the logger
logger.addHandler(stream_handler)
logger.info("Logger is configured")
##########################
# Shimmer wallet configurations
##########################
client_options = {
    "nodes": [node_url],
}
coin_type = 4219
secret_manager = StrongholdSecretManager(stronghold_db_name, stronghold_password)
client = IotaClient(client_options)

def check_if_sent(addresses):
    """
    Checks if the given addresses have already been sent to, based on a CSV file.
    
    Args:
        addresses (list[str]): A list of email addresses to check.
    
    Returns:
        list[str]: A list of email addresses that have not yet been sent to.
        
    Raises:
        FileNotFoundError: If the CSV file containing previously sent addresses
        cannot be found.
    """
    with open(shimmer_address_sent_to_filename, encoding="UTF-8") as file:
        csv_reader = csv.reader(file)
        sent_addresses = {row[0]: True for row in csv_reader}

    new_addresses = []
    for address in addresses:
        if address in sent_addresses:
            logger.info("%s is already in the CSV", address)
        else:
            logger.info("%s  is a new address, sending", address)
            new_addresses.append(address)

    return new_addresses


def send_nfts(outputs):
    """Sends SMR tokens to a single address."""
    logger.info("Received bulk outputs.")
    logger.debug("Received bulk outputs: %s", outputs)
    try:
        # Sync account with the node
        wallet = IotaWallet(wallet_db_name, client_options, coin_type, secret_manager)
        account = wallet.get_account(shimmer_account_name)
        logger.info("Account retrieved")
        address = account.addresses()
        logger.debug("Address: %s", address[0]['address'])
        balance = account.get_balance()
        logger.debug("Balance: %s", balance)
        account.sync()
        logger.info("Account Synced")

        # Verify if there is enough balance
        # check_enough_balance(account_status)

        # Set the Stronghold password
        wallet.set_stronghold_password(stronghold_password)

        # Define the output transaction
        logger.debug("Outputs: %s", outputs)

        try:
            # Build the output now
            outputs_to_send = []
            for output in outputs:
                prepared_output = account.prepare_output(output)
                outputs_to_send.append(prepared_output)

            # Send the transaction with the defined outputs
            transaction = account.send_outputs(outputs_to_send)
            logger.info("Transaction sent")
            transaction_id = transaction['transactionId']
            account.retry_transaction_until_included(transaction_id)
            account.sync()
            logger.debug("Transaction %s", transaction)
            transaction = account.get_transaction(transaction_id)
            # Check if the transaction's networkId is the
            # mainnet (14364762045254553490)
            # testnet (1856588631910923207)
            if transaction["networkId"] == "1856588631910923207":
                # Get the blockId for this transaction
                block_id = transaction["blockId"]
                for item in outputs:
                    address = item["recipientAddress"]
                    nftId = item["assets"]["nftId"]
                    write_to_csv(address, nftId, block_id)

        except Exception:
            logger.info(traceback.format_exc())
        return

    except ValueError as e:  # Catch the raised ValueError
        logger.info("Stopping the program: %s", e)  # Add a log message
        sys.exit(1)  # Stop the program

    except Exception:
        logger.info(traceback.format_exc())

def write_to_csv(shimmer_receiver_address, nftId, block_id):
    try:
        """Writes the transaction details to a CSV file."""
        # assuming you have the following variables available:
        # - address
        # - token_amount
        # - date_time
        # - block_id

        # construct the explorer link
        explorer_link = f"https://explorer.shimmer.network/shimmer/block/{block_id}"
        # Get the current date and time
        date_time = time.strftime("%Y-%m-%d %H:%M:%S")

        # create a list with the data to write to the CSV file
        data = [
            [shimmer_receiver_address, nftId, explorer_link, date_time]
        ]

        # open the CSV file in 'append' mode
        with open(shimmer_address_sent_to_filename, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            # write the data to the CSV file
            writer.writerows(data)
            logger.info(
                f"Transaction details appended to CSV file for address: {shimmer_receiver_address}"
            )
    except Exception:
        logger.warning(traceback.format_exc())

def get_zealy_api_data(subdomain, x_api_key, quest_id, status):
    # page_number = int(request.GET.get("page", 1))
    # Get quests with quest_id and status "success" from the Crew3 API
    try:
        api_url = (
        f"https://api.zealy.io/communities/{subdomain}/claimed-quests?quest_id={quest_id}&status={status}"
    )
        logger.debug(api_url)
        headers = {"x-api-key": x_api_key}
        response = requests.get(api_url, headers=headers)
        data = response.json()
        logger.debug(data)
        return data
    except Exception:
        logger.warning(traceback.format_exc())

def validate_zealy_api_data(subdomain, x_api_key, claimedQuestIds, status, comment):
    # page_number = int(request.GET.get("page", 1))
    # Get quests with quest_id and status "success" from the Crew3 API
    try:
        api_url = (
            f"https://api.zealy.io/communities/{subdomain}/claimed-quests/review"
        )
        logger.debug(api_url)
        headers = {
            "x-api-key": x_api_key,
            "Content-Type": "application/json"
        }
        data = {
            "status": status,
            "claimedQuestIds": claimedQuestIds,
            "comment": comment
        }
        response = requests.post(api_url, headers=headers, json=data)
        response_data = response.json()

        return response_data
    except Exception:
        logger.warning(traceback.format_exc())

def unique_addresses(addresses):
    try:
        unique_addresses = []
        for address in addresses:
            if address not in unique_addresses:
                unique_addresses.append(address)
            else:
                logger.info(f"Skipping duplicate address: {address}")
        logger.debug(f"unique_addresses {unique_addresses}")
        return unique_addresses
    except Exception:
        logger.info(traceback.format_exc())

def return_valid_shimmer_addresses(smr_addresses):
    try:
        shimmer_client = IotaClient()
        valid_addresses = []
        for i in smr_addresses:
            if not shimmer_client.is_address_valid(i):
                logger.debug(f"Skipping invalid address: {i}")
            else:
                logger.debug(f"Valid address: {i}")
                valid_addresses.append(i)
        logger.info(f"All valid addresses: {valid_addresses}")
        return valid_addresses
    except Exception:
        logger.warning(traceback.format_exc())

def validate_shimmer_address(smr_address):
    shimmer_client = IotaClient()
    if smr_address.startswith(shimmer_address_hrp):
        if shimmer_client.is_address_valid(smr_address):
            return True
    logger.debug(smr_address)
    return False

def mint_nfts(amount):
    try:
        wallet = IotaWallet(wallet_db_name, client_options, coin_type, secret_manager)
        account = wallet.get_account(shimmer_account_name)
        account.sync()
        address = account.addresses()
        balance = account.get_balance()
        available_balance = int(balance['baseCoin']['total'])
        logger.debug(f"Balance: {balance}")
        logger.debug(f"Available balance: {available_balance}")
        if available_balance < 10000000:
            logger.warning(f"⚠️⚠️⚠️ Not enough balance to mint! \n⚠️⚠️⚠️ Send at least 10 000 000 glow to {address[0]['address']} before launching this program again!")
            time.sleep(15)
            return
        else:
            logger.debug("Enough balance, we can mint!")
            nft_collection_size = amount
            # Create the metadata with another index for each
            nft_options = []
            logger.debug(f"Collection NFT address {collection_nft_address}")
            # rarity_attribue_value = ["Common", "Rare", "Legendary"]
            # material_attribue_value = ["Gold", "Silver", "Bronze"]
            # curse_attribute_value = ["The Guardian", "The Legacy", "The Prophecy"]
            for index in range(nft_collection_size):
                # rarity = random.choice(rarity_attribue_value)
                # material = random.choice(material_attribue_value)
                # curse = random.choice(curse_attribute_value)
                immutable_metadata = bytes(json.dumps({
                    "standard": "IRC27",
                    "version": "v1.0",
                    "type": "image/png",
                    "uri": "ipfs://bafybeiapknbq3in35vzc4ystkm4ccm2v63jphgvjaulgdlqkyqfypsil3u",
                    "name": "Shimmer Community Champion Badge",
                    "description": "Shimmer Community Champion Badge",
                    "issuerName": "TEA - Tangle Ecosystem Association",
                    "collectionName": "Shimmer Community Champion Badges",
                    "attributes": [
                        {
                        "trait_type": "Year",
                        "value": "2023",
                        "trait_type": "Artist",
                        "value": "@BingoBongo_ape"
                        }
                    ]
                }).encode('utf-8')).hex()

                combined_metadata = "0x" + immutable_metadata

                nft_options.append({
                "immutableMetadata": combined_metadata,
                "issuer": collection_nft_address,
                })
            logger.debug(f"NFT Options: {nft_options}")
            
            for nft in [nft_options[i:i+50] for i in range(0, len(nft_options), 50)]:
                transaction = account.mint_nfts(nft)
                transaction_id = transaction['transactionId']
                logger.debug(f"Minted NFT with options: {nft}")
                logger.debug("NFT pending transaction id: %s", transaction_id)
                account.retry_transaction_until_included(transaction_id)
                account.sync()
            
            logger.info("NFTs minted")
            logger.debug("NFTs minted. Transaction %s", transaction)
        
                # time.sleep(15)

    except Exception:
        logger.warning(traceback.format_exc())



def get_available_nfts():
    logger.debug("Checking for available NFTs")
    # Sync account with the node
    wallet = IotaWallet(wallet_db_name, client_options, coin_type, secret_manager)
    account = wallet.get_account(shimmer_account_name)
    response = account.sync()
    logger.debug(f'Synced response in get available: {response}')
    nfts = response['nfts']
    print(nfts)
    print(len(nfts))
    logger.info(f"Available NFTs in get function: {len(nfts)}")
    if len(nfts) == 0:
        logger.info(
            f"⚠️There are no NFTs available {nfts}\n⚠️Make sure to have the Collection NFT in this address and to add the Collection NFT ID to the .env file before you continue."
            )
        sys.exit(1)
    else:
        return nfts


def create_shimmer_profile():
    """Create a new Shimmer wallet profile."""
    logger.debug("I am in create_shimmer_profile")

    # Check if wallet.stronghold exists and exit if present
    if os.path.isfile("wallet.stronghold"):
        logger.info("Profile already exists. We continue.")
        return
    else:
        print("Creating new profile")
        # This creates a new database and account
        try:
            wallet = IotaWallet(
                wallet_db_name, client_options, coin_type, secret_manager
            )
            account = wallet.store_mnemonic(shimmer_mnemonic)
            account = wallet.create_account(shimmer_account_name)

            logger.debug(account)
            input("Press Enter to continue...")

            return

        except Exception:
            logger.warning(traceback.format_exc())

def basic_checks():
    # Writes the CSV file with the given filename shimmer_address_sent_to_filename if it doesn't already exist
    if not os.path.exists(shimmer_address_sent_to_filename):
        with open(shimmer_address_sent_to_filename, mode='w', newline='') as file:
            writer = csv.writer(file)

    # Verify that all variables have non-empty values
    env_vars = [
        "STRONGHOLD_PASSWORD",
        "STRONGHOLD_DB_NAME",
        "WALLET_DB_NAME",
        "SHIMMER_MNEMONIC",
        "SHIMMER_ACCOUNT_NAME",
        "NODE_URL",
        "ZEALY_API_KEY",
        "ZEALY_SUBDOMAIN",
        "SHIMMER_ADDRESS_SENT_TO_FILENAME",
    ]
    # iterate through each environment variable and check if it has a non-empty value
    for var in env_vars:
        if os.getenv(var) is None or os.getenv(var) == "":
            return False

    # all variables have a non-empty value
    return True
