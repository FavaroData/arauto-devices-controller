# Arauto Devices — Arquitetura

## Escopo

- Linguagem: Python
- Dispositivos suportados: apenas tomadas/interruptores (liga/desliga)
- Interface: CLI, com modo direto e modo interativo (shell)
- Sem agendamento, sem API web — controle manual apenas
- Padrões aplicados: Command + Adapter + Repository, com injeção de dependência via interfaces

## Visão geral

```
CLI (Cli.py)  →  Commands (Commands.py)  →  DeviceController (interface)
                        ↓                          ↓
              DevicesRepository            CloudDeviceController
              (lê devices.json)            (fala com a Tuya Cloud API)
```

**Fluxo**: a CLI recebe, por exemplo, `on AirFrier` → monta um `OnCommand` → o Command pede o `Device` ao `DevicesRepository` → chama `DeviceController.turn_on(device)` → quem executa de fato é o `CloudDeviceController`, que autentica com `tinytuya.Cloud()` e manda o comando pelos servidores da Tuya (mesmo caminho que o app SmartLife usa).

**Princípio central**: nenhuma camada superior conhece os detalhes da camada inferior. O `OnCommand` não sabe que existe `tinytuya`, nem se o controller por trás fala com a nuvem ou com o IP local. O `DevicesRepository` não sabe controlar dispositivo nenhum, só carrega dados. Essa separação é o que permitiu a troca de local pra cloud: só a linha que instancia o controller em `Cli.py` mudou (`TuyaDeviceController()` → `CloudDeviceController()`); `Command`, `DevicesRepository` e `Device` continuaram intactos.

## Local vs Cloud

O projeto tem duas implementações de `DeviceController`, cumprindo o mesmo contrato:

| | `CloudController.py` (em uso) | `TuyaController.py` (implementado, não usado por padrão) |
|---|---|---|
| Caminho de comunicação | Servidores da Tuya (HTTP) | Direto no IP do dispositivo (LAN) |
| Alcance | Qualquer lugar com internet | Só na mesma rede local |
| Depende de | Servidores da Tuya estarem no ar | Rede WiFi local |
| Limite de uso | Chamadas limitadas em conta Trial | Sem limite |
| Credencial usada | `tinytuya.json` (apiKey/apiSecret) | `local_key` de cada dispositivo (`devices.json`) |

A troca entre os dois é só uma questão de qual controller é instanciado em `Cli.py` — nenhuma outra camada precisa saber qual dos dois está em uso.

## Componentes

| Arquivo | Papel | Padrão aplicado |
|---|---|---|
| `Device.py` | Ficha de dados de uma tomada (`name`, `id`, `ip`, `local_key`, `version`) | — |
| `DevicesRepository.py` | Lê o `devices.json` e traduz pra objetos `Device`; expõe `DeviceNotFoundError` | Repository |
| `DeviceController.py` | Contrato abstrato (`turn_on`, `turn_off`, `get_status`); expõe `DeviceControllerError` | — (interface/porta) |
| `CloudController.py` | Implementação real do contrato via Tuya Cloud API (`tinytuya.Cloud`) — em uso por padrão | Adapter |
| `TuyaController.py` | Implementação real do contrato via API local (`tinytuya.Device`) — não usada por padrão, mantida como alternativa | Adapter |
| `Command.py` / `Commands.py` | Cada ação da CLI (`OnCommand`, `OffCommand`, `StatusCommand`, `ListCommand`) | Command |
| `Cli.py` | Parsing de argumentos, modo interativo, monta o `Command` certo e injeta as dependências | Dependency Injection |

### `Device.py`

```python
class Device:
    def __init__(self, name, id, ip, local_key, version):
        self.name = name
        self.id = id
        self.ip = ip
        self.local_key = local_key
        self.version = version
```

Não tem comportamento, só carrega dados.

### `DevicesRepository.py`

Única responsabilidade: ler o `devices.json` e devolver objetos `Device`. A tradução de nomes acontece só aqui — o JSON usa `"key"` (formato exigido pelo tinytuya), guardado como `local_key` no `Device`:

```python
local_key=item["key"],
```

Se o campo `"ip"` não existir no JSON (dispositivo nunca visto online), usa `"Auto"` como padrão, deixando o `tinytuya` descobrir o IP em tempo real:

```python
ip=item.get("ip", "Auto"),
```

### `DeviceController.py`

```python
class DeviceController(ABC):
    @abstractmethod
    def turn_on(self, device: Device) -> None: ...
    @abstractmethod
    def turn_off(self, device: Device) -> None: ...
    @abstractmethod
    def get_status(self, device: Device) -> dict: ...
```

Define o contrato — qualquer coisa que controla um dispositivo sabe fazer essas 3 coisas. `ABC` + `@abstractmethod` impedem instanciar essa classe diretamente, e barram na hora de criar qualquer subclasse que esqueça de implementar algum dos três métodos.

### `CloudController.py` (em uso)

Fala com a Tuya Cloud API via `tinytuya.Cloud()` (que lê `apiKey`/`apiSecret` do `tinytuya.json` automaticamente). Duas decisões não óbvias aqui:

**Normalização de formato** — a Cloud API devolve status como `{"result": [{"code": "switch_1", "value": True}, ...]}`, diferente do formato `{"dps": {...}}` que o modo local usa. `get_status` traduz um pro outro, mantendo o mesmo contrato de saída pros dois controllers:

```python
items = result.get("result", []) if isinstance(result, dict) else []
return {"dps": {item["code"]: item["value"] for item in items}}
```

**Checagem de online antes de comandar** — a Cloud API retorna `"success": True` mesmo com o dispositivo desligado/offline (ela só confirma que o comando foi recebido pelos servidores da Tuya, não que foi executado). Por isso `_send_switch` consulta `_is_online` antes de mandar o comando, evitando reportar "LIGADO" quando o dispositivo nem está acessível:

```python
def _send_switch(self, device: Device, ligar: bool) -> None:
    if not self._is_online(device):
        raise DeviceControllerError("Dispositivo está offline — comando não será entregue agora.")
    # ...envia o comando
```

Essa checagem custa uma chamada HTTP extra por comando (status + comando, em vez de só comando) — uma simplificação deliberada aceita pelo uso pessoal do projeto; se a quota da conta Trial virar problema, o próximo passo seria cachear `_is_online` com um TTL curto.

### `TuyaController.py` (implementado, não usado por padrão)

Implementação alternativa via API local — fala direto com o IP do dispositivo na rede, sem depender da nuvem. É a única classe que faz `import tinytuya` no sentido "protocolo local" (`tinytuya.Device`, não `tinytuya.Cloud`). Captura falhas de conexão (incluindo erro na própria descoberta do dispositivo) e relança como `DeviceControllerError`:

```python
try:
    d = tinytuya.Device(...)
except RuntimeError as e:
    raise DeviceControllerError(f"Dispositivo não encontrado na rede: {e}")
```

Mantida no projeto como alternativa — trocar de volta pro modo local é só voltar a instanciar `TuyaDeviceController()` em vez de `CloudDeviceController()` no `Cli.py`.

### `Commands.py`

Cada ação vira uma classe própria, recebendo só o que precisa via injeção de dependência (`ListCommand`, por exemplo, não recebe `controller`, já que listar não fala com hardware nenhum). Cada `execute()` trata separadamente `DeviceNotFoundError` (nome não existe no JSON) e `DeviceControllerError` (falha ao falar com o dispositivo real), imprimindo mensagem clara em vez de deixar o traceback estourar.

### `Cli.py`

Faz parsing via `argparse` com subcomandos (`list`, `on`, `off`, `status`). Quando rodado sem argumentos, entra em modo interativo (shell), reaproveitando o mesmo `DevicesRepository` e `CloudDeviceController` a cada comando digitado, sem recriar as peças a cada linha. É o único arquivo que precisou mudar na troca de local pra cloud — a linha `controller = TuyaDeviceController()` virou `controller = CloudDeviceController()`.

## Testes

Como `Command` depende só da interface `DeviceController`, dá pra testar sem tocar em rede nenhuma, usando um `FakeDeviceController`:

```python
class FakeDeviceController(DeviceController):
    def __init__(self):
        self.calls = []
    def turn_on(self, device):
        self.calls.append(("on", device.name))
    def turn_off(self, device):
        self.calls.append(("off", device.name))
    def get_status(self, device):
        return {"dps": {"1": True}}
```

Nenhum teste com esse fake chama `tinytuya` nem depende de estar na mesma rede da tomada — o que permite CI rodando sem hardware físico.

## Estrutura de arquivos

```
arauto-devices/
├── src/
│   ├── Cli.py                        # ponto de entrada, parsing e modo interativo
│   ├── Command.py                    # interface abstrata dos comandos
│   ├── Commands.py                   # OnCommand, OffCommand, StatusCommand, ListCommand
│   ├── Device.py                     # classe de dados de uma tomada
│   ├── DevicesRepository.py          # leitura do devices.json + DeviceNotFoundError
│   ├── devices.json                  # dados dos dispositivos, fora do git
│   ├── tinytuya.json                 # credenciais da Cloud API, fora do git
│   └── controllers/
│       ├── DeviceController.py       # interface abstrata + DeviceControllerError
│       ├── CloudController.py        # implementação real via Tuya Cloud API (em uso)
│       ├── TuyaController.py         # implementação real via API local (não usada por padrão)
│       └── FakeDeviceController.py   # implementação fake, usada em testes
└── scripts/
    ├── teste01.py
    └── teste02.py
```

## Erros comuns e como resolver

| Sintoma | Causa provável | Solução |
|---|---|---|
| `ModuleNotFoundError` ao rodar um teste dentro de `tests/` | O Python só procura módulos na pasta do próprio arquivo executado | Roda a partir da pasta raiz do projeto, ou ajusta `sys.path` |
| `FileNotFoundError: devices.json` | Caminho relativo depende de onde o terminal está (`cwd`), não de onde o script está | Usa `Path(__file__).parent / "devices.json"` em vez de `Path("devices.json")` |
| `KeyError: 'key'` ao rodar `tinytuya scan`/`wizard` | O campo no `devices.json` foi renomeado manualmente (ex: pra `"local_key"`) | O tinytuya exige o nome `"key"` no arquivo — não altera esse nome no JSON, só na sua classe `Device` internamente |
| `AttributeError: 'Device' object has no attribute ...` | Nome de atributo não bate entre `Device.py` e quem o consome | Confere que o nome do atributo é o mesmo em todos os arquivos que usam a classe `Device` |
| "Dispositivo está offline — comando não será entregue agora" (`CloudController`) | Dispositivo desligado da energia/rede; a Cloud API confirmaria sucesso mesmo assim sem a checagem de `_is_online` | Liga o dispositivo fisicamente antes de repetir o comando |
| Erro de quota/limite de chamadas (`CloudController`) | Conta Tuya IoT Platform em modo Trial | Aguarda o reset do período, ou avalia upgrade de plano |
| `Unable to find device on network` / `RuntimeError` (`TuyaController`, se estiver em uso) | Dispositivo desligado da energia ou fora da rede WiFi | Liga o dispositivo fisicamente e confirma que está na mesma rede WiFi do computador |
| `Check device key or version` (`TuyaController`, se estiver em uso) | `local_key` desatualizada ou versão de protocolo errada | Roda `python -m tinytuya wizard` de novo pra atualizar a chave; confere a versão com `tinytuya scan` |
| `FileNotFoundError` relacionado ao `tinytuya.json` | Arquivo de credenciais da Cloud API não está na mesma pasta do `Cli.py` | Roda `python -m tinytuya wizard` de novo, ou copia o `tinytuya.json` já gerado pra pasta do projeto |

## Fora do escopo (por decisão de projeto)

- **Agendamento automático** — controle manual apenas por enquanto. A arquitetura em camadas comporta adicionar depois (novo `Command` ou módulo separado que reusa `DeviceController`) sem refatoração grande.
- **Suporte a outros tipos de dispositivo** (luzes, sensores, câmeras) — exigiria ampliar a interface `DeviceController` ou criar controladores especializados por tipo.
- **API web / dashboard** — o projeto é CLI apenas.
