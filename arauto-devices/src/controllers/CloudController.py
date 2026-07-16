import requests
import tinytuya
from Device import Device
from controllers.DeviceController import DeviceController, DeviceControllerError


class CloudDeviceController(DeviceController):
    """
    Controla dispositivos via Tuya Cloud API (mesmo caminho do app SmartLife),
    em vez de conectar direto no IP local.

    Trade-off aceito: precisa de internet e depende dos servidores da Tuya
    estarem no ar; em compensação, funciona de qualquer rede.
    """

    def __init__(self):
        # tinytuya.Cloud() sem argumentos lê as credenciais do tinytuya.json
        # gerado pelo wizard — não é óbvio pelo nome que a leitura é implícita.
        self._cloud = tinytuya.Cloud()

    def turn_on(self, device: Device) -> None:
        """Liga o dispositivo. Levanta DeviceControllerError se estiver offline ou a Cloud API falhar."""
        self._send_switch(device, True)

    def turn_off(self, device: Device) -> None:
        """Desliga o dispositivo. Levanta DeviceControllerError se estiver offline ou a Cloud API falhar."""
        self._send_switch(device, False)

    def get_status(self, device: Device) -> dict:
        """Retorna o último status conhecido do dispositivo no formato {"dps": {...}}."""
        result = self._cloud.getstatus(device.id)
        self._check_error(result)

        # A Cloud API devolve {"result": [{"code": ..., "value": ...}]}, formato
        # diferente do local ({"dps": {...}}). Traduzimos aqui pra manter o
        # mesmo contrato de saída pros dois controllers — quem chama get_status
        # não deveria precisar saber se está falando com local ou cloud.
        items = result.get("result", []) if isinstance(result, dict) else []
        return {"dps": {item["code"]: item["value"] for item in items}}
    
    def is_online(self, device: Device) -> bool:
        # getstatus() não informa conexão — só devolve o último valor conhecido
        # dos dps, que pode ser dado velho de quando o dispositivo esteve
        # online pela última vez. O campo "online" real só existe neste
        # endpoint de informação geral do dispositivo.
        try:
            result = self._cloud.cloudrequest(f"/v1.0/devices/{device.id}")
        except requests.exceptions.ConnectionError as e:
            raise DeviceControllerError(f"Sem conexão com a internet: {e}")

        if not isinstance(result, dict) or not result.get("success"):
            raise DeviceControllerError("Não foi possível consultar o status de conexão do dispositivo.")
        return result.get("result", {}).get("online", False)

    def _send_switch(self, device: Device, ligar: bool) -> None:
        # A Cloud API retorna "success": True mesmo com o dispositivo offline —
        # ela só confirma que o comando foi aceito pelos servidores da Tuya,
        # não que foi executado. Sem essa checagem, o programa reportaria
        # "LIGADO" com a tomada desligada da energia (reproduzido em teste).
        if not self.is_online(device):
            raise DeviceControllerError("Dispositivo está offline — comando não será entregue agora.")

        commands = {"commands": [{"code": "switch_1", "value": ligar}]}
        result = self._cloud.sendcommand(device.id, commands)
        self._check_error(result)

        # SIMPLIFICAÇÃO DELIBERADA: essa checagem dobra as chamadas HTTP por
        # comando (status + comando, em vez de só comando). Teto aceito: uso
        # pessoal esporádico, dentro da quota de conta Trial. Gatilho de
        # upgrade: se a quota estourar ou o uso ficar mais frequente, cachear
        # o resultado de is_online com TTL curto (ex.: 5-10s) em vez de
        # consultar a cada chamada.

    def _check_error(self, result) -> None:
        # A Cloud API não estoura exceção Python em falha — devolve
        # {"success": False, "msg": "..."}. Traduzimos pra DeviceControllerError
        # pra manter o mesmo contrato de erro que o resto do sistema já espera.
        if isinstance(result, dict) and result.get("success") is False:
            raise DeviceControllerError(result.get("msg", "Erro desconhecido na Cloud API"))