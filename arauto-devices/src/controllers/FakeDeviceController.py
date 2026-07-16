from Device import Device
from controllers.DeviceController import DeviceController


class FakeDeviceController(DeviceController):
    def __init__(self):
        self.calls = []

    def turn_on(self, device):
        self.calls.append(("on", device.name))
        print(f"[FAKE] '{device.name}' -> LIGADO")

    def turn_off(self, device):
        self.calls.append(("off", device.name))
        print(f"[FAKE] '{device.name}' -> DESLIGADO")

    def get_status(self, device):
        print(f"[FAKE] Consultando status de '{device.name}'")
        return {"dps": {"1": True}}

    def is_online(self, device):
        print(f"[FAKE] Consultando conexão de '{device.name}'")
        return True


# Testando sem precisar de dispositivo real
device_teste = Device(
    name="tomada_teste",
    id="fake-id-123",
    ip="0.0.0.0",
    local_key="fake-key",
    version=3.3,
)

controller = FakeDeviceController()

print("Status:", controller.get_status(device_teste))
controller.turn_on(device_teste)
controller.turn_off(device_teste)

print("Chamadas registradas:", controller.calls)