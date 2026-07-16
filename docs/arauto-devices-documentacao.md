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

### Fluxo completo: `on AirFrier` (Exemplo onde seu dispositivo se chama "AirFrier")

Você digita `on AirFrier` no shell, ou roda `python Cli.py on AirFrier` direto no terminal. Isso não liga a tomada na hora — o comando passa por quatro arquivos do projeto antes de qualquer coisa sair da sua máquina: `Cli.py`, `Commands.py`, `DevicesRepository.py` e `CloudController.py`.

Primeiro, o `Cli.py` pega o texto digitado e usa o `argparse` pra separar em `cmd = "on"` e `nome = "AirFrier"`. Com isso, ele monta um objeto `OnCommand`, passando pra ele o `controller` e o `repo` que já tinham sido criados no início do `main()`. O `OnCommand` em si não sabe ler arquivo nem falar com a Tuya — ele só organiza a sequência de passos.

O primeiro passo do `OnCommand.execute()` é pedir o dispositivo pro `DevicesRepository`, chamando `get_by_name("AirFrier")`. O repositório abre o `devices.json`, lê o conteúdo e devolve um objeto `Device` com nome, IP, ID e chave local daquele dispositivo. Se o nome não existir no arquivo, ele levanta `DeviceNotFoundError` e o comando para ali mesmo, sem chegar perto da rede.

Com o `Device` em mãos, o `OnCommand` chama `is_online(device)` pra confirmar que o dispositivo está acessível, e `get_status(device)` pra ver se ele já não está ligado (evitando mandar o comando à toa). Só depois dessas duas checagens é que `turn_on(device)` roda de verdade.

É nesse ponto que a execução sai da sua máquina. `CloudDeviceController.turn_on()` delega pra `_send_switch()`, que monta o payload:

```json
{"commands": [{"code": "switch_1", "value": true}]}
```

e chama `self._cloud.sendcommand(device.id, commands)`. Esse `self._cloud` é a instância de `tinytuya.Cloud()` criada quando o `CloudDeviceController` foi instanciado, e ela já carrega as credenciais (`apiKey`/`apiSecret`) do `tinytuya.json`, cuidando da autenticação sozinha.

Dali em diante, quem processa o comando são os servidores da Tuya, os mesmos que o app SmartLife usa no celular. A tomada nunca recebe nada direto de você: ela fica conectada via WiFi nos servidores da Tuya o tempo todo, esperando comandos chegarem de lá. O app SmartLife e essa CLI são só dois clientes diferentes batendo na mesma API.

## Local vs Cloud

O projeto tem duas implementações de `DeviceController`, cumprindo o mesmo contrato:

| | `CloudController.py` (em uso) | `TuyaController.py` (implementado, não usado) |
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

`Device` é a classe mais simples do projeto. Ela guarda os cinco atributos que identificam uma tomada (`name`, `id`, `ip`, `local_key`, `version`) e não tem nenhum método além do `__init__`. Não valida nada, não decide nada sozinha, não fala com arquivo nem com rede.

Pense nela como um envelope: o `DevicesRepository` lê o `devices.json` e preenche esse envelope, e cada camada seguinte (`Commands`, `CloudController`) só lê o que está dentro, sem alterar. É esse mesmo objeto que atravessa toda a cadeia descrita no fluxo acima, do `Cli.py` até a chamada real na Tuya Cloud.

### `DevicesRepository.py`

Única responsabilidade: ler o `devices.json` e devolver objetos `Device`. Não fala com a Tuya, não sabe ligar nem desligar nada, só traduz o que está no arquivo pra um formato que o resto do projeto entende.

Essa tradução de nomes acontece só aqui, e existe por um motivo específico: o `devices.json` usa a chave `"key"` (nome que o `tinytuya wizard` gera automaticamente), mas dentro do projeto esse valor vira `local_key` no objeto `Device`. Deixar essa tradução concentrada num único lugar evita que o resto do código precise saber que esse desalinhamento de nomes existe:

```python
local_key=item["key"],
```

Também é aqui que fica a única regra de fallback do projeto. Se o campo `"ip"` não existir no JSON (o que acontece quando o dispositivo nunca foi visto online durante o wizard), o repositório usa `"Auto"` no lugar, deixando o `tinytuya` descobrir o IP sozinho na hora de falar com o dispositivo:

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
    @abstractmethod
    def is_online(self, device: Device) -> bool: ...
```

Define o contrato: qualquer coisa que controla um dispositivo sabe fazer essas quatro coisas. `ABC` + `@abstractmethod` impedem instanciar essa classe diretamente, e barram na hora de criar qualquer subclasse que esqueça de implementar algum dos quatro métodos. O Python levanta `TypeError` na hora de instanciar, não em tempo de importação.

`is_online` é o mais recente dos quatro. Ele nasceu de um problema real: `get_status()` devolve o último `switch_1` conhecido, que pode estar desatualizado se o dispositivo caiu da rede depois da última vez que respondeu. Sem um jeito de confirmar conectividade de verdade, tanto o comando `list` (que precisa mostrar Online/Offline) quanto `on`/`off` (que precisam decidir se confiam num "já está ligado" cacheado) ficariam expostos a esse dado velho.

Como o contrato é compartilhado pelas três implementações do projeto (`CloudController`, `TuyaController`, `FakeDeviceController`), adicionar `is_online` aqui obrigou as três a implementar o método, mesmo a `TuyaController`, que não estava em uso no momento da mudança.

### `CloudController.py` (em uso)

Fala com a Tuya Cloud API via `tinytuya.Cloud()`, que lê `apiKey`/`apiSecret` do `tinytuya.json` sozinho, sem precisar passar nada explicitamente no construtor. Duas decisões desse arquivo não são óbvias só de ler o código, e vale explicar o porquê de cada uma.

**Normalização de formato.** A Cloud API devolve o status de um dispositivo como `{"result": [{"code": "switch_1", "value": True}, ...]}`, um formato completamente diferente do `{"dps": {...}}` que o modo local (`TuyaController.py`) usa. Se cada camada de cima tivesse que saber qual desses dois formatos está recebendo, o resto do projeto ficaria acoplado a um detalhe de implementação da Tuya. Por isso `get_status` traduz um formato pro outro internamente, mantendo a mesma saída pros dois controllers:

```python
items = result.get("result", []) if isinstance(result, dict) else []
return {"dps": {item["code"]: item["value"] for item in items}}
```

**Checagem de online antes de comandar.** A Cloud API tem um comportamento enganoso: ela retorna `"success": True` mesmo quando o dispositivo está desligado da energia ou fora da rede. Esse `"success"` só confirma que o comando chegou nos servidores da Tuya, não que a tomada realmente executou. Sem checar isso antes, a aplicação relataria "LIGADO" pro usuário mesmo com a tomada fisicamente desconectada, comportamento que já foi reproduzido em teste durante o desenvolvimento. Por isso `_send_switch` chama `is_online` antes de mandar qualquer comando:

```python
def _send_switch(self, device: Device, ligar: bool) -> None:
    if not self.is_online(device):
        raise DeviceControllerError("Dispositivo está offline — comando não será entregue agora.")
    # ...envia o comando
```

Essa checagem tem um custo: dobra o número de chamadas HTTP por comando, já que agora são duas requisições (checar status, depois enviar) em vez de uma só. É uma simplificação aceita de propósito, pensando em uso pessoal esporádico dentro da quota de uma conta Trial. Se essa quota virar um problema real, o próximo passo natural seria cachear o resultado de `is_online` por alguns segundos, em vez de consultar a API a cada chamada.

### `TuyaController.py` (implementado, não usado por padrão)

Implementação alternativa via API local. Fala direto com o IP do dispositivo na rede, sem depender da nuvem, e é a única classe do projeto que usa `tinytuya` no sentido "protocolo local" (`tinytuya.Device`, em vez de `tinytuya.Cloud`, que é o que o `CloudController.py` usa).

Toda operação passa primeiro por `_connect()`, que monta um `tinytuya.Device` com o IP, a `local_key` e a versão de protocolo daquele dispositivo específico. Se a conexão falhar (dispositivo desligado, fora da rede, ou credencial errada), `tinytuya` levanta um `RuntimeError` genérico, e `_connect()` traduz isso pra `DeviceControllerError`, mantendo o mesmo contrato de erro que o resto do projeto já espera:

```python
try:
    d = tinytuya.Device(...)
except RuntimeError as e:
    raise DeviceControllerError(f"Dispositivo não encontrado na rede: {e}")
```

Como esse controller não tem acesso a nenhum endpoint tipo o `cloudrequest` da Tuya Cloud, ele não tem como perguntar "esse dispositivo está online?" sem tentar falar com ele de verdade. Por isso `is_online()` aqui funciona diferente do `CloudController`: em vez de consultar um status separado, ele tenta se conectar e ler o status do dispositivo, devolvendo `True` ou `False` dependendo se essa tentativa deu certo, sem deixar a exceção estourar pra fora:

```python
def is_online(self, device: Device) -> bool:
    try:
        d = self._connect(device)
        result = d.status()
        return isinstance(result, dict) and "Error" not in result
    except DeviceControllerError:
        return False
```

Mantida no projeto como alternativa, não como código morto: trocar de volta pro modo local é só voltar a instanciar `TuyaDeviceController()` em vez de `CloudDeviceController()` no `Cli.py`. Foi essa mesma classe que ficou desatualizada quando `is_online` entrou na interface `DeviceController`: toda subclasse de uma `ABC` precisa implementar todos os métodos abstratos, senão a instanciação falha com `TypeError`.

### `Commands.py`

Cada ação da CLI vira uma classe própria (`OnCommand`, `OffCommand`, `StatusCommand`, `ListCommand`), recebendo só o que precisa via injeção de dependência. A maioria segue o mesmo formato: pede o `Device` pro repositório e chama o `controller` pra agir. `ListCommand` também recebe `controller` hoje, porque listar dispositivos inclui testar a conexão de cada um (ver mais abaixo).

`OnCommand` e `OffCommand` têm uma lógica de no-op: antes de mandar o comando de verdade, eles checam se o dispositivo já está no estado desejado, pra não gastar uma chamada à toa. Essa checagem não usa só o `switch_1` que vem de `get_status()`, porque esse valor pode ser um dado cacheado, potencialmente desatualizado se o dispositivo caiu da rede depois da última vez que esteve online. Por isso o comando também chama `is_online()`, e só aceita o atalho de "já está LIGADO/DESLIGADO" quando as duas informações batem:

```python
online = self.controller.is_online(device)
status = self.controller.get_status(device)
if online and status.get("dps", {}).get("switch_1") is True:
    print(f"{Fore.YELLOW}'{device.name}' já está LIGADO")
    return
```

Cada `execute()` trata dois tipos de erro separadamente: `DeviceNotFoundError` (o nome digitado não existe no `devices.json`) e `DeviceControllerError` (o nome existe, mas alguma coisa falhou ao tentar falar com o dispositivo de verdade). Os dois viram mensagem de erro colorida pro usuário, sem deixar o traceback estourar no terminal.

`ListCommand` segue essa mesma ideia de testar antes de confiar: pra cada dispositivo cadastrado, ela chama `is_online()` e monta uma coluna de Status (Online em verde, Offline em vermelho) junto com nome, IP e ID. Se `is_online()` levantar `DeviceControllerError` pra um dispositivo específico, por exemplo por falha de rede naquela consulta, a linha dele é tratada como Offline em vez de derrubar a listagem inteira.

### `Cli.py`

Faz o parsing dos argumentos via `argparse`, com subcomandos pra `list`, `on`, `off` e `status` (cada um definido em `build_parser()`). Quando você roda `python Cli.py` sem nenhum argumento, ele entra em modo interativo (shell) em vez de pedir ajuda ou dar erro, porque `add_subparsers` foi criado com `required=False` de propósito.

Antes de fazer qualquer coisa, `main()` chama `_connect_cloud()`, que tenta instanciar `CloudDeviceController()` e, junto com ele, autenticar na Tuya Cloud. Se não tiver internet, essa chamada falha com `requests.exceptions.ConnectionError`, e em vez de deixar o traceback estourar, `_connect_cloud()` tenta de novo a cada `RETRY_DELAY` segundos (5, por padrão), até `MAX_RETRIES` vezes (10). Esgotadas as tentativas, imprime um erro final e encerra com `sys.exit(1)` em vez de entrar no shell com uma conexão que não existe.

No modo interativo, `run_shell()` reaproveita o mesmo `DevicesRepository` e o mesmo `controller` a cada linha digitada, sem recriar nada entre comandos. Ele mostra o banner (`_print_banner()`, com a arte ASCII e a caixa desenhada com caracteres Unicode) e a lista de comandos (`_print_help()`) só uma vez, no início, mas o comando `help` digitado a qualquer momento reimprime essa lista sem precisar reiniciar o shell. O loop principal captura `SystemExit` (que o `argparse` levanta em erro de parsing) pra não derrubar o shell inteiro por causa de um comando digitado errado.

Trocar de cloud pra local continua sendo uma mudança pequena, mas hoje ela mora dentro de `_connect_cloud()`: em vez de `CloudDeviceController()`, bastaria instanciar `TuyaDeviceController()` ali, perdendo, claro, a lógica de retry, que só faz sentido pra uma conexão de rede real.

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
