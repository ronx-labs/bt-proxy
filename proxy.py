#!/usr/bin/env python3
"""
Proxy script for blockchain staking operations.
"""

import argparse
import sys
from modules import RonProxy
from bittensor.utils.balance import Balance


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Proxy script for blockchain staking operations",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add stake command
    add_parser = subparsers.add_parser('addstake', help='Add stake to a subnet')
    add_parser.add_argument('--netuid', type=int, required=True, help='Network/subnet ID')
    add_parser.add_argument('--hotkey', type=str, required=True, help='Hotkey address')
    add_parser.add_argument('--amount', type=float, help='Amount to stake')
    add_parser.add_argument('--tolerance', type=float, default=0.05, help='Tolerance for stake')
    
    # Remove stake command
    remove_parser = subparsers.add_parser('removestake', help='Remove stake from a subnet')
    remove_parser.add_argument('--netuid', type=int, required=True, help='Network/subnet ID')
    remove_parser.add_argument('--hotkey', type=str, required=True, help='Hotkey address')
    remove_parser.add_argument('--amount', type=float, default=0, help='Amount to unstake')
    remove_parser.add_argument('--all', action='store_true', help='Remove all staked balance')
    remove_parser.add_argument('--tolerance', type=float, default=0.05, help='Tolerance for stake')
    
    # Swap stake command
    swap_parser = subparsers.add_parser('swapstake', help='Swap stake between subnets')
    swap_parser.add_argument('--hotkey', type=str, required=True, help='Hotkey address')
    swap_parser.add_argument('--origin-netuid', type=int, required=True, help='Source subnet ID')
    swap_parser.add_argument('--dest-netuid', type=int, required=True, help='Destination subnet ID')
    swap_parser.add_argument('--amount', type=float, default=0, help='Amount to swap')
    swap_parser.add_argument('--all', action='store_true', help='Swap all available balance')
    
    return parser


def validate_args(args: argparse.Namespace) -> bool:
    """Validate argument combinations."""
    if args.command == 'addstake':
        if not args.amount:
            print("Error: Must specify --amount")
            return False
    
    elif args.command in ['removestake', 'swapstake']:    
        if not args.amount and not args.all:
            print("Error: Must specify either --amount or --all")
            return False
        if args.amount and args.all:
            print("Error: Cannot specify both --amount and --all")
            return False
    
    return True


def main():
    """Main entry point."""
    # Import environment variables
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    network = os.getenv('NETWORK')
    delegator = os.getenv('DELEGATOR')
    proxy_wallet = os.getenv('PROXY_WALLET')
    
    # Validate environment variables
    if not network or not delegator or not proxy_wallet:
        print("Error: Missing environment variables")
        sys.exit(1)

    # Create parser
    parser = create_parser()
    
    # Parse arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if not validate_args(args):
        sys.exit(1)
        
    # Initialize RonProxy object
    ron_proxy = RonProxy(
        proxy_wallet=proxy_wallet,
        network=network,
        delegator=delegator,
    )
    print(f"Initialized RonProxy object for {network} network")
    
    try:
        if args.command == 'addstake':
            ron_proxy.add_stake(
                netuid=args.netuid,
                hotkey=args.hotkey,
                amount=Balance.from_tao(args.amount),
                tolerance=args.tolerance,
            )
        elif args.command == 'removestake':
            ron_proxy.remove_stake(
                netuid=args.netuid,
                hotkey=args.hotkey,
                amount=Balance.from_tao(args.amount, netuid=args.netuid),
                tolerance=args.tolerance,
                all=args.all,
            )
        elif args.command == 'swapstake':
            ron_proxy.swap_stake(
                hotkey=args.hotkey,
                origin_netuid=getattr(args, 'origin_netuid'),
                dest_netuid=getattr(args, 'dest_netuid'),
                amount=Balance.from_tao(args.amount, netuid=getattr(args, 'origin_netuid')),
                all=args.all,
            )
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
