import logging
import argparse
import sys

from slither import Slither
from crytic_compile import cryticparser
from slither.exceptions import SlitherException
from slither.utils.json_utils import output_json

from .compare_variables_order import compare_variables_order_implementation, compare_variables_order_proxy
from .compare_function_ids import compare_function_ids
from .check_initialization import check_initialization


logging.basicConfig()
logger = logging.getLogger("Slither-check-upgradeability")
logger.setLevel(logging.INFO)

def parse_args():

    parser = argparse.ArgumentParser(description='Slither Upgradeability Checks. For usage information see https://github.com/crytic/slither/wiki/Upgradeability-Checks.',
                                     usage="slither-check-upgradeability proxy.sol ProxyName implem.sol ContractName")


    parser.add_argument('proxy.sol', help='Proxy filename')
    parser.add_argument('ProxyName', help='Contract name')

    parser.add_argument('implem.sol', help='Implementation filename')
    parser.add_argument('ContractName', help='Contract name')

    parser.add_argument('--new-version', help='New implementation filename')
    parser.add_argument('--new-contract-name', help='New contract name (if changed)')

    parser.add_argument('--json',
                        help='Export the results as a JSON file ("--json -" to export to stdout)',
                        action='store',
                        default=False)
    
    cryticparser.init(parser)

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    return parser.parse_args()


###################################################################################
###################################################################################
# region Main
###################################################################################
###################################################################################


def main():
    args = parse_args()

    proxy_filename = vars(args)['proxy.sol']
    proxy = Slither(proxy_filename, **vars(args))
    proxy_name = args.ProxyName

    v1_filename = vars(args)['implem.sol']
    v1 = Slither(v1_filename, **vars(args))
    v1_name = args.ContractName

    # Define some variables for potential JSON output
    json_results = {}
    output_error = ''

    json_results['check-initialization'] = check_initialization(v1)

    if not args.new_version:
        json_results['compare-function-ids'] = compare_function_ids(v1, v1_name, proxy, proxy_name)
        json_results['compare-variables-order-proxy'] = compare_variables_order_proxy(v1, v1_name, proxy, proxy_name)
    else:
        v2 = Slither(args.new_version, **vars(args))
        v2_name = v1_name if not args.new_contract_name else args.new_contract_name

        json_results['check-initialization-v2'] = check_initialization(v2)

        json_results['compare-function-ids'] = compare_function_ids(v2, v2_name, proxy, proxy_name)

        results = {}
        output_error = ''

        try:
            results = compare_variables_order_proxy(v2, v2_name, proxy, proxy_name)
        except SlitherException as se:
            output_error = str(se)
        json_results['compare-variables-order-proxy'] = results
        
        try:
            results = compare_variables_order_implementation(v1, v1_name, v2, v2_name)
        except SlitherException as se:
            output_error += str(se)
        json_results['compare-variables-order-implementation'] = results

    if output_error == '':
        output_error = None
        
    # If we are outputting JSON, capture the redirected output and disable the redirect to output the final JSON.
    if args.json:
        output_json(args.json, output_error, {"upgradeability-check": json_results})

        
# endregion