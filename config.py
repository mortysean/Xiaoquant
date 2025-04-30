# /home/seanhuang/XiaoquantSystem/config.py
import argparse
from types import SimpleNamespace
import os

def dict_to_namespace(d):
    if isinstance(d, dict):
        return SimpleNamespace(**{k: dict_to_namespace(v) for k, v in d.items()})
    elif isinstance(d, list):
        return [dict_to_namespace(x) for x in d]
    else:
        return d


def parse_cli_args():
    parser = argparse.ArgumentParser(description="Configuration for XiaoquantSystem")

    # === Global logging
    parser.add_argument(
        '--log_level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Global logging level (default: INFO)'
    )

    # === API Credentials
    api_group = parser.add_argument_group('API Credentials')

    api_group.add_argument('--tushare_token', type=str, default=os.getenv("TUSHARE_TOKEN", ""))
    
    api_group.add_argument('--binance_api_key', type=str, default='your_default_binance_api_key')
    api_group.add_argument('--binance_api_secret', type=str, default='your_default_binance_api_secret')
    api_group.add_argument('--usstock_api_key', type=str, default='your_default_usstock_api_key')

    # === Exchange
    exchange_group = parser.add_argument_group('Exchange Configuration')
    exchange_group.add_argument('--exchange', type=str, default='tushare', choices=['tushare', 'binance', 'usstock'])

    # === Data Fetch
    data_group = parser.add_argument_group('Data Configuration')
    data_group.add_argument('--frequency', type=str, default='daily', choices=['daily', 'hourly', 'minutely'])
    data_group.add_argument('--symbol', type=str, default='000001.SH')
    data_group.add_argument('--index_symbol', type=str, default=None) 
    data_group.add_argument('--start_date', type=str, default=None)
    data_group.add_argument('--end_date', type=str, default=None)
    data_group.add_argument('--fields', type=str, default=None)


    # === Executor / Factor engine
    parser.add_argument('--expr', type=str, default=None, help='Path to expression file (e.g. alpha101.txt)')

    # === Dash
    dash_group = parser.add_argument_group('Dash Configuration')
    dash_group.add_argument('--dash_port', type=int, default=8050)
    dash_group.add_argument('--dash_debug', action='store_true')

    # === Django
    django_group = parser.add_argument_group('Django Configuration')
    django_group.add_argument('--django_host', type=str, default='127.0.0.1')
    django_group.add_argument('--django_port', type=int, default=8000)

    return parser.parse_args()


def merge_config(cli_args):
    # Use CLI values only
    cfg = {}

    # --- Data Source ---
    cfg["data_source"] = {"type": cli_args.exchange}

    # --- Fetch ---
    fetch = {
        "symbols": [cli_args.symbol] if cli_args.symbol else [],
        "index_symbol": cli_args.index_symbol.split(",") if cli_args.index_symbol else [],
        "start": cli_args.start_date,
        "end": cli_args.end_date,
        "frequency": cli_args.frequency,
        "fields": cli_args.fields.split(",") if cli_args.fields else []
    }
    cfg["fetch"] = fetch


    # --- Executor ---
    cfg["executor"] = {"expression_path": cli_args.expr} if cli_args.expr else {}

    # --- API ---
    cfg["api"] = {
        "tushare_token": cli_args.tushare_token,
        "binance_api_key": cli_args.binance_api_key,
        "binance_api_secret": cli_args.binance_api_secret,
        "usstock_api_key": cli_args.usstock_api_key
    }

    # --- Dash ---
    cfg["dash"] = {
        "port": cli_args.dash_port,
        "debug": cli_args.dash_debug
    }

    # --- Django ---
    cfg["django"] = {
        "host": cli_args.django_host,
        "port": cli_args.django_port
    }

    # --- Logging ---
    cfg["log_level"] = cli_args.log_level

    # --- Flatten common fields ---
    cfg["symbol"] = fetch["symbols"][0] if fetch["symbols"] else None
    cfg["index_symbol"] = fetch["index_symbol"]
    cfg["start_date"] = fetch["start"]
    cfg["end_date"] = fetch["end"]
    cfg["frequency"] = fetch["frequency"]
    cfg["exchange"] = cfg["data_source"]["type"]
    
    

    return cfg


# === Final config ===
cli_args = parse_cli_args()
config = dict_to_namespace(merge_config(cli_args))