import json
from pathlib import Path
from Device import Device


class DeviceNotFoundError(Exception):
    """Dispositivo não encontrado no devices.json."""


class DeviceRepository:
    def __init__(self, devices_file: Path):
        self._devices_file = devices_file

    # Retorna o Dispositivo (Device) pelo nome
    def get_by_name(self, name: str) -> Device:
        devices = self._load()
        if name not in devices:
            raise DeviceNotFoundError(f"Dispositivo '{name}' não encontrado.")
        return devices[name]

    # Lista os dispositivos
    def list_all(self) -> list[Device]:
        return list(self._load().values())

    # Carrega os dados do json
    def _load(self) -> dict[str, Device]:
        # abre o arquivo json
        with open(self._devices_file) as f:
            raw = json.load(f)

        # retorna os dados do json na estrutura
        return {
            item["name"]: Device(
                name=item["name"],
                id=item["id"],
                ip=item.get("ip", "Auto"),   # usa "Auto" se o campo não existir
                local_key=item["key"], # JSON usa "key" (padrão tinytuya) -> guardamos como local_key no Device
                version=float(item.get("version", 3.3)),   # idem pra version, caso falte
            )
            for item in raw
        }