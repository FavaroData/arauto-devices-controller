from colorama import Fore, Style

from Command import Command
from controllers.DeviceController import DeviceController, DeviceControllerError
from DevicesRepository import DeviceRepository, DeviceNotFoundError


class OnCommand(Command):
    def __init__(self, controller: DeviceController, repo: DeviceRepository, device_name: str):
        self.controller = controller
        self.repo = repo
        self.device_name = device_name

    def execute(self) -> None:
        try:
            device = self.repo.get_by_name(self.device_name)
        except DeviceNotFoundError:
            print(f"{Fore.RED}Dispositivo '{self.device_name}' não encontrado.")
            return

        try:
            # switch_1 cacheado pela Cloud API pode estar desatualizado se o
            # dispositivo caiu depois da última vez que esteve online — só
            # confia no "já está LIGADO" quando is_online() confirma que o
            # dado é atual.
            online = self.controller.is_online(device)
            status = self.controller.get_status(device)
            if online and status.get("dps", {}).get("switch_1") is True:
                print(f"{Fore.YELLOW}'{device.name}' já está LIGADO")
                return

            self.controller.turn_on(device)
            print(f"{Fore.GREEN}{Style.BRIGHT}'{device.name}' -> LIGADO")
        except DeviceControllerError as e:
            print(f"{Fore.RED}Erro ao LIGAR '{device.name}': {e}")

class OffCommand(Command):
    def __init__(self, controller: DeviceController, repo: DeviceRepository, device_name: str):
        self.controller = controller
        self.repo = repo
        self.device_name = device_name

    def execute(self) -> None:
        try:
            device = self.repo.get_by_name(self.device_name)
        except DeviceNotFoundError:
            print(f"{Fore.RED}Dispositivo '{self.device_name}' não encontrado.")
            return

        try:
            online = self.controller.is_online(device)
            status = self.controller.get_status(device)
            if online and status.get("dps", {}).get("switch_1") is False:
                print(f"{Fore.YELLOW}'{device.name}' já está DESLIGADO")
                return

            self.controller.turn_off(device)
            print(f"{Fore.GREEN}{Style.BRIGHT}'{device.name}' -> DESLIGADO")
        except DeviceControllerError as e:
            print(f"{Fore.RED}Erro ao DESLIGAR '{device.name}': {e}")

class StatusCommand(Command):
    def __init__(self, controller: DeviceController, repo: DeviceRepository, device_name: str):
        self.controller = controller
        self.repo = repo
        self.device_name = device_name

    def execute(self) -> None:
        try:
            device = self.repo.get_by_name(self.device_name)
        except DeviceNotFoundError:
            print(f"{Fore.RED}Dispositivo '{self.device_name}' não encontrado.")
            return

        try:
            status = self.controller.get_status(device)
            dps = status.get("dps", {})

            print(f"{Style.BRIGHT}{Fore.CYAN}Status de '{device.name}':")
            largura = max((len(k) for k in dps), default=0)
            for k, v in dps.items():
                cor = Fore.GREEN if v is True else Fore.RED if v is False else Fore.WHITE
                print(f"  {k:<{largura}}  {cor}{v}")
        except DeviceControllerError as e:
            print(f"{Fore.RED}Erro ao consultar '{device.name}': {e}")

class ListCommand(Command):
    def __init__(self, controller: DeviceController, repo: DeviceRepository):
        self.controller = controller
        self.repo = repo

    def execute(self) -> None:
        devices = self.repo.list_all()
        if not devices:
            print(f"{Fore.YELLOW}Nenhum dispositivo cadastrado.")
            return

        print(f"{Style.BRIGHT}{'Nome':<25} {'IP':<16} {'Device ID':<25} {'Status'}")
        print("-" * 80)
        for device in devices:
            try:
                online = self.controller.is_online(device)
            except DeviceControllerError:
                online = False

            cor, texto = (Fore.GREEN, "Online") if online else (Fore.RED, "Offline")
            print(f"{device.name:<25} {device.ip:<16} {device.id:<25} {cor}{texto}")
    