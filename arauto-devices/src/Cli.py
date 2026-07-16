import argparse
import sys
import shlex
import time
from pathlib import Path

import requests
from colorama import init, Fore, Style

from DevicesRepository import DeviceRepository
from controllers.CloudController import CloudDeviceController
from Commands import OnCommand, OffCommand, StatusCommand, ListCommand


def build_command(args, controller, repo):
    if args.cmd == "on":
        return OnCommand(controller, repo, args.nome)
    if args.cmd == "off":
        return OffCommand(controller, repo, args.nome)
    if args.cmd == "status":
        return StatusCommand(controller, repo, args.nome)
    if args.cmd == "list":
        return ListCommand(controller, repo)
    raise ValueError(f"Comando desconhecido: {args.cmd}")


def build_parser():
    parser = argparse.ArgumentParser(description="Controle de tomadas SmartLife/Tuya via API cloud")
    sub = parser.add_subparsers(dest="cmd", required=False)

    sub.add_parser("list", help="Lista os dispositivos disponíveis")

    p = sub.add_parser("on", help="Liga um dispositivo")
    p.add_argument("nome")

    p = sub.add_parser("off", help="Desliga um dispositivo")
    p.add_argument("nome")

    p = sub.add_parser("status", help="Mostra o status de um dispositivo")
    p.add_argument("nome")

    return parser

# variável para separação padrão na visualização no CLI
BOX_WIDTH = 55

ARAUTO_ASCII = r"""█████╗ ██████╗  █████╗ ██╗   ██╗████████╗ ██████╗
██╔══██╗██╔══██╗██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗
███████║██████╔╝███████║██║   ██║   ██║   ██║   ██║
██╔══██║██╔══██╗██╔══██║██║   ██║   ██║   ██║   ██║
██║  ██║██║  ██║██║  ██║╚██████╔╝   ██║   ╚██████╔╝
╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝"""

# init da aplicação exibida após o 'python Cli.py'
def _print_banner():
    print(f"{Style.BRIGHT}{Fore.CYAN}")
    print(f"╭{'─' * BOX_WIDTH}╮")
    print(f"│{' ' * BOX_WIDTH}│")
    for linha in ARAUTO_ASCII.splitlines():
        print(f"│{linha.center(BOX_WIDTH)}│")
    print(f"│{' ' * BOX_WIDTH}│")
    print(f"│{'D E V I C E S'.center(BOX_WIDTH)}│")
    print(f"│{' ' * BOX_WIDTH}│")
    print(f"╰{'─' * BOX_WIDTH}╯{Style.RESET_ALL}")
    print(f'\nSmartLife Device Manager\n')
    


def _print_help():
    comandos = [
        ("list", "Lista dispositivos"),
        ("on <nome>", "Liga um dispositivo"),
        ("off <nome>", "Desliga um dispositivo"),
        ("status <nome>", "Exibe status"),
        ("exit", "Sair"),
    ]
    print(f"{Style.BRIGHT}Commands{Style.RESET_ALL}")
    print("─" * 16)
    for nome, descricao in comandos:
        print(f"{nome:<18}{descricao}")
    print()


def run_shell(parser, controller, repo):
    _print_banner()
    _print_help()
    while True:
        try:
            linha = input(f"arauto >> {Style.RESET_ALL}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not linha:
            continue
        if linha in ("exit", "quit", "sair"):
            break
        if linha == "help":
            _print_help()
            continue

        try:
            args = parser.parse_args(shlex.split(linha))
        except SystemExit:
            # argparse chama sys.exit() em erro de parsing; evita matar o shell inteiro
            continue

        if args.cmd is None:
            continue

        try:
            command = build_command(args, controller, repo)
            command.execute()
        except ValueError as e:
            print(f"{Fore.RED}{e}")


MAX_RETRIES = 10
RETRY_DELAY = 5


def _connect_cloud():
    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            return CloudDeviceController()
        except requests.exceptions.ConnectionError:
            if tentativa == MAX_RETRIES:
                print(f"{Fore.RED}Não foi possível conectar à Tuya Cloud após {MAX_RETRIES} tentativas. Verifique sua conexão com a internet.")
                sys.exit(1)
            print(f"{Fore.YELLOW}Sem conexão com a Tuya Cloud (tentativa {tentativa}/{MAX_RETRIES}) — tentando de novo em {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)


def main():
    init(autoreset=True)
    parser = build_parser()

    devices_path = Path(__file__).parent / "devices.json"
    repo = DeviceRepository(devices_path)
    controller = _connect_cloud()

    if len(sys.argv) == 1:
        run_shell(parser, controller, repo)
        return

    args = parser.parse_args()
    command = build_command(args, controller, repo)
    command.execute()


if __name__ == "__main__":
    main()