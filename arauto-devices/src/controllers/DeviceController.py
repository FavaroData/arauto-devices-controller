from abc import ABC, abstractmethod
from Device import Device


class DeviceControllerError(Exception):
    """Erro ao comunicar com um dispositivo físico."""

# ABC = Abstratic Base Class: classe especial que serve só pra ser herdada (quem vai herdar vai ser o TuyaController)
class DeviceController(ABC):
    @abstractmethod
    def turn_on(self, device: Device) -> None:
        pass

    @abstractmethod
    def turn_off(self, device: Device) -> None:
        pass

    @abstractmethod
    def get_status(self, device: Device) -> dict:
        pass

    @abstractmethod
    def is_online(self, device: Device) -> bool:
        pass