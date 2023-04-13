# Shimmer Zealy NFT minter/dropper

This repository contains a module to send NFTs to users who completed a quest and won an NFT airdrop. The module contains four functions:

1. get_nft_winners(): retrieves the list of the winners of the NFT airdrop by querying the Zealy API with a specific quest ID and status.
1. get_smr_address_submitters(status: str): returns a list of submitters for a given status of SMR address.
1. get_smr_address_from_quest_completers(): retrieves the SMR addresses of users who completed a quest and won an NFT airdrop.
1. send_to_address(addresses: list): sends NFTs to the addresses, if addresses are present.

This module imports several variables and functions from the tools module. Please ensure you have the necessary authentication tokens before running the module.

## Usage

- Copy and change all necessary info in .env
- Install the requirements with `pip install -r requirements.txt`
- Run with `python main.py`

## License

This code is licensed under the Apache 2.0 License. Please see the LICENSE file for more information.
