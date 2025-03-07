from async_substrate_interface.sync_substrate import SubstrateInterface
from bittensor_wallet.keypair import Keypair
from core.coingecko_client import coingecko_client
from core.config import setting
from loguru import logger

async def get_substrate():
    """Get the substrate client"""
    if setting.substrate is None:
        setting.substrate = SubstrateInterface(url=setting.subtensor)
    return setting.substrate


def get_balance(substrate, address, block_hash) -> int:
    """
    Get free balance on an account.
    """
    result = substrate.query(
        module="System",
        storage_function="Account",
        params=[address],
        block_hash=block_hash,
    )
    return result["data"]["free"]


def convert_to_alpha(substrate: SubstrateInterface, amount_in_tao: float) -> float: 
    """
    Convert TAO to alpha

    :param substrate: The substrate client
    :param amount_in_tao: The amount in TAO to convert

    :return: The amount in alpha
    """
    subnet_alpha = substrate.query("SubtensorModule", "SubnetAlphaIn", [setting.net_uid]).value
    subnet_tao = substrate.query("SubtensorModule", "SubnetTAO", [setting.net_uid]).value
    price = subnet_alpha / subnet_tao
    logger.info(f"Subnet alpha: {subnet_alpha}, subnet tao: {subnet_tao}, price: {price}")
    return amount_in_tao * price

def print_extrinsic_receipt(receipt):
    success_event = False
    batch_interrupted_event = None
    error_message = None
    for event in receipt.triggered_events:
        event_details = event.value['event']
        module_id = event_details['module_id']
        event_id = event_details['event_id']

        if module_id == 'System' and event_id == 'ExtrinsicSuccess':
            success_event = True
        elif module_id == 'Utility' and event_id == 'BatchInterrupted':
            batch_interrupted_event = event
            error_message = int(event_details['attributes']['error']['Module']['error'], 16) >> 24

    print(f"Extrinsic included in block: {receipt.block_hash}")
    print(f"Extrinsic hash: {receipt.extrinsic_hash}")
    print(f"Block number: {receipt.block_number}")
    print(f"Events: {receipt.triggered_events}")

    if batch_interrupted_event:
        print("Extrinsic failed due to a batch interruption")
        if error_message:
            print(f"Error message: {error_message}")
    elif success_event:
        print("Extrinsic succeeded")
    else:
        print("Extrinsic failed")
        if receipt.error_message:
            print(f"Error message: {receipt.error_message}")

def batch_transfer_balances(substrate: SubstrateInterface, kaypair, transfer_info_dict: dict):

    all_calls = []
    for dest_coldkey, amount_in_usd in transfer_info_dict:
        
        amount_in_tao, rate = coingecko_client.convert_to_tao(amount_in_usd)
        amount_in_alpha = int(convert_to_alpha(substrate, amount_in_tao) * pow(10, 9))
        
        call = substrate.compose_call(
            call_module="SubtensorModule",
            call_function="transfer_stake",
            call_params={
                "destination_coldkey": dest_coldkey,
                "hotkey": setting.hotkey,
                "origin_netuid": setting.net_uid,
                "destination_netuid": setting.net_uid,
                "alpha_amount": amount_in_alpha,
            },
        )

        all_calls.append(call)

    batch_call = node.compose_call(
        call_module="Utility",
        call_function="force_batch",
        call_params={'calls': all_calls}
    )

    extrinsic = substrate.create_signed_extrinsic(call=batch_call, keypair=keypair)
    wait_for_inclusion = True
    response = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=wait_for_inclusion, wait_for_finalization=False)
    if wait_for_inclusion:
        print_extrinsic_receipt(response)   
    return None, None

def transfer_balance(substrate: SubstrateInterface, keypair, dest_coldkey: str, amount_in_usd: float):
    """
    Transfer balance from keypair to dest_coldkey
    
    :param substrate: The substrate client
    :param keypair: The keypair to transfer the balance from
    :param dest_coldkey: The coldkey of the destination account
    :param amount_in_usd: The amount in USD to transfer

    :return tuple[float, float]: The amount in USD transferred and the amount in TAO
    """
    logger.info(f"Syncing with chain: {setting.subtensor}...")
    block = substrate.get_block_number(substrate.get_chain_head())
    block_hash = substrate.get_block_hash(block)

    result = substrate.get_constant(
        module_name="Balances",
        constant_name="ExistentialDeposit",
        block_hash=block_hash,
    )
    if result is None:
        raise Exception("Unable to retrieve existential deposit amount.")
    
    # Get TAO amount and rate from USD amount
    amount_in_tao, rate = coingecko_client.convert_to_tao(amount_in_usd)
    # Get amount to send in alpha
    amount_in_alpha = int(convert_to_alpha(substrate, amount_in_tao) * pow(10, 9))

    logger.info(f"Sending {amount_in_tao} TAO ({rate} USD) ({amount_in_alpha} ALPHA) for {amount_in_usd} USD to {dest_coldkey}...")
    call = substrate.compose_call(
        call_module="SubtensorModule",
        call_function="transfer_stake",
        call_params={
            "destination_coldkey": dest_coldkey,
            "hotkey": setting.hotkey,
            "origin_netuid": setting.net_uid,
            "destination_netuid": setting.net_uid,
            "alpha_amount": amount_in_alpha,
        },
    )

    extrinsic = substrate.create_signed_extrinsic(call=call, keypair=keypair)
    substrate.submit_extrinsic(extrinsic, wait_for_inclusion=False)
    logger.info(f"Sent {amount_in_tao} TAO ({rate} USD) ({amount_in_alpha} ALPHA) for {amount_in_usd} USD to {dest_coldkey}.")
    return amount_in_usd, amount_in_tao
