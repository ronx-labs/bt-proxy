#!/usr/bin/env python3
"""
Multisig script for creating blockchain transfer and proxy proposals.
"""

import bittensor as bt
from substrateinterface import SubstrateInterface
from bittensor.utils.balance import Balance
from dotenv import load_dotenv
import os
import sys

RPC_ENDPOINTS = {
    'test': 'wss://test.finney.opentensor.ai:443',
    'finney': 'wss://entrypoint-finney.opentensor.ai:443',
}

class MultisigProposal:
    def __init__(self, network: str, multisig_address: str, proxy_wallet: str, approver_address: str):
        """
        Initialize the MultisigProposal object.
        
        Args:
            network: Network name (test/finney)
            multisig_address: Multisig account address 
            proxy_wallet: Proxy wallet name for signing
        """
        if network not in RPC_ENDPOINTS:
            raise ValueError(f"Invalid network: {network}")
        
        self.network = network
        self.multisig_address = multisig_address
        self.proxy_wallet = bt.wallet(name=proxy_wallet)
        self.approver_address = approver_address
        self.substrate = SubstrateInterface(
            url=RPC_ENDPOINTS[self.network],
            ss58_format=42,
            type_registry_preset='substrate-node-template',
        )
        self.subtensor = bt.subtensor(network=network)

    def create_transfer_proposal(self, destination: str, amount: Balance) -> None:
        """
        Create a multisig proposal for token transfer.
        
        Args:
            destination: Destination address
            amount: Amount to transfer
        """
        print(f"Creating transfer proposal...")
        print(f"From: {self.multisig_address}")
        print(f"To: {destination}")
        print(f"Current balance: {self.subtensor.get_balance(address=self.multisig_address)}")
        print(f"Amount: {amount}")
        
        confirm = input(f"Do you really want to create this transfer proposal? (y/n): ")
        if confirm.lower() != "y":
            print("Transfer proposal cancelled.")
            return
        
        # Create the transfer call
        transfer_call = self.substrate.compose_call(
            call_module='Balances',
            call_function='transfer_keep_alive',
            call_params={
                'dest': destination,
                'value': amount.rao,
            }
        )
        
        # Create multisig proposal
        is_success, error_message = self._create_multisig_proposal(transfer_call)
        if is_success:
            print("Transfer proposal created successfully!")
        else:
            print(f"Error creating transfer proposal: {error_message}")

    def create_proxy_proposal(self, proxy_address: str, proxy_type: str) -> None:
        """
        Create a multisig proposal for adding proxy.
        
        Args:
            proxy_address: Address to add as proxy
            proxy_type: Type of proxy ('staking' or 'registration' or 'transfer')
        """
        # Map proxy type string to proper case
        proxy_type_mapping = {
            'staking': 'Staking',
            'registration': 'Registration',
            'transfer': 'Transfer'
        }
        
        if proxy_type.lower() not in proxy_type_mapping:
            print(f"Error: Invalid proxy type. Must be 'staking' or 'registration' or 'transfer'")
            return
            
        formatted_proxy_type = proxy_type_mapping[proxy_type.lower()]
        
        print(f"Creating proxy proposal...")
        print(f"Multisig: {self.multisig_address}")
        print(f"Proxy Address: {proxy_address}")
        print(f"Proxy Type: {formatted_proxy_type}")
        
        confirm = input(f"Do you really want to create this proxy proposal? (y/n): ")
        if confirm.lower() != "y":
            print("Proxy proposal cancelled.")
            return
        
        # Create the add_proxy call
        add_proxy_call = self.substrate.compose_call(
            call_module='Proxy',
            call_function='add_proxy',
            call_params={
                'delegate': proxy_address,
                'proxy_type': formatted_proxy_type,
                'delay': 0,
            }
        )
        
        # Create multisig proposal
        is_success, error_message = self._create_multisig_proposal(add_proxy_call)
        if is_success:
            print("Proxy proposal created successfully!")
        else:
            print(f"Error creating proxy proposal: {error_message}")

    def _create_multisig_proposal(self, call) -> tuple[bool, str]:
        """
        Create a multisig proposal with the given call.
        
        Args:
            call: The substrate call to propose
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get multisig info to determine threshold and other signatories
            # For simplicity, we'll use threshold=2 and assume this wallet is a signatory
            threshold = 2
            other_signatories = [self.approver_address]  # This would need to be populated with actual signatories
            
            print("")
            print(f"Call hash: {call.call_hash.hex()}")
            print(f"Call data: {self._get_call_data(call)}")
            
            # Create the multisig proposal call
            multisig_call = self.substrate.compose_call(
                call_module='Multisig',
                call_function='approve_as_multi',
                call_params={
                    'threshold': threshold,
                    'other_signatories': other_signatories,
                    'maybe_timepoint': None,
                    'call_hash': call.call_hash,
                    'max_weight': {'ref_time': 1000000000, 'proof_size': 10000}
                }
            )
            
            print("")
            print(f"Signing with proxy wallet: {self.proxy_wallet.name}")
            extrinsic = self.substrate.create_signed_extrinsic(
                call=multisig_call,
                keypair=self.proxy_wallet.coldkey,
            )
            
            receipt = self.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
            
            return receipt.is_success, receipt.error_message
            
        except Exception as e:
            return False, str(e)
        
    def _get_call_data(self, call) -> str:
        """
        Get the call data from a substrate call.
        """
        processed_call = call.process()        
        del processed_call['call_index']
        return call.process_encode(value=processed_call)


def get_user_input():
    """Get user input for action type and parameters."""
    print("=== Multisig Proposal Creator ===")
    
    # Get action type
    while True:
        action_type = input("Enter action type (transfer/proxy): ").strip().lower()
        if action_type in ['transfer', 'proxy']:
            break
        print("Invalid action type. Please enter 'transfer' or 'proxy'.")
        print("")
    
    if action_type == 'transfer':
        # Get transfer parameters
        destination = input("Enter destination address: ").strip()
        if not destination:
            print("Error: Destination address is required")
            sys.exit(1)
        
        while True:
            try:
                amount_input = input("Enter transfer amount (TAO): ").strip()
                amount_float = float(amount_input)
                if amount_float <= 0:
                    print("Error: Amount must be positive")
                    continue
                amount = Balance.from_tao(amount_float)
                break
            except ValueError:
                print("Error: Invalid amount format")
                continue
        
        return action_type, destination, amount
    
    else:  # proxy
        # Get proxy parameters
        proxy_address = input("Enter proxy address (if you want to add yourself as a proxy, just type 'self'): ").strip()
        if not proxy_address:
            print("Error: Proxy address is required")
            sys.exit(1)
            
        if proxy_address.lower() == 'self':
            proxy_address = bt.wallet(name=os.getenv('PROXY_WALLET')).coldkey.ss58_address
            print(f"Proxy address set to your own address: {proxy_address}")
        
        while True:
            proxy_type = input("Enter proxy type (staking/registration/transfer): ").strip().lower()
            if proxy_type in ['staking', 'registration', 'transfer']:
                break
            print("Invalid proxy type. Please enter 'staking' or 'registration' or 'transfer'.")
        
        return action_type, proxy_address, proxy_type


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()
    
    print(f"=== Loaded environment variables ===")
    
    network = os.getenv('NETWORK')
    multisig_address = os.getenv('DELEGATOR')  # Using delegator as multisig address
    proxy_wallet = os.getenv('PROXY_WALLET')
    approver_address = os.getenv('APPROVER')

    print(f"Network: {network}")
    print(f"Multisig address: {multisig_address}")
    print(f"Proxy wallet: {proxy_wallet}")
    print(f"Approver address: {approver_address}")
    print("")
    
    # Validate environment variables
    if not network or not multisig_address or not proxy_wallet:
        print("Error: Missing environment variables")
        print("Please ensure NETWORK, DELEGATOR, and PROXY_WALLET are set in .env")
        sys.exit(1)
    
    if network not in RPC_ENDPOINTS:
        print(f"Error: Invalid network '{network}'. Must be 'test' or 'finney'")
        sys.exit(1)
    
    try:
        # Initialize MultisigProposal
        multisig = MultisigProposal(
            network=network,
            multisig_address=multisig_address,
            proxy_wallet=proxy_wallet,
            approver_address=approver_address,
        )
        
        # Get user input
        user_input = get_user_input()
        action_type = user_input[0]
        
        print("")
        
        if action_type == 'transfer':
            _, destination, amount = user_input
            multisig.create_transfer_proposal(destination, amount)
        else:  # proxy
            _, proxy_address, proxy_type = user_input
            multisig.create_proxy_proposal(proxy_address, proxy_type)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
