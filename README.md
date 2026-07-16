# Arauto Devices

CLI em Python pra controlar tomadas inteligentes SmartLife/Tuya via Tuya Cloud API — o mesmo caminho que o app SmartLife usa, então funciona de qualquer lugar com internet, não só na rede local.

## O que essa aplicação faz

- Lista as tomadas cadastradas
- Liga, desliga e consulta o status de uma tomada específica
- Funciona tanto por linha de comando direta quanto num modo interativo (shell)
- Fala com o dispositivo através dos servidores da Tuya (Cloud API), então funciona de qualquer rede com internet — mas depende dos servidores da Tuya estarem no ar, e contas developer Trial têm limite de chamadas por período
- Confirma se o dispositivo está online antes de mandar um comando de liga/desliga — a Cloud API confirma "recebido" mesmo se o dispositivo estiver offline, então essa checagem evita reportar sucesso falso

## Pré-requisitos

- Python 3.10+ (o projeto usa recursos como `match` e sintaxe de tipo moderna)
- Um ambiente virtual (venv) configurado
- Pelo menos uma tomada Tuya/SmartLife já pareada no app **SmartLife**
- Conta developer na [Tuya IoT Platform](https://platform.tuya.com/)

## Instalação

Crie o ambiente virtual **dentro da pasta do projeto** (não compartilhe o `.venv` entre projetos diferentes):

```bash
cd ArautoDevices
python -m venv .venv
source .venv/bin/activate
pip install tinytuya
```

### Reproduzindo o ambiente em outra máquina

Depois de instalar as dependências, gera um `requirements.txt` pra deixar o ambiente reproduzível sem precisar versionar o `.venv` em si:

```bash
pip freeze > requirements.txt
```

Em qualquer outra máquina (ou depois de clonar o repositório), basta:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração inicial (obrigatória antes do primeiro uso)

A configuração acontece em três etapas: parear a tomada no app, vincular a conta à Tuya IoT Platform, e gerar o arquivo de credenciais locais.

### 1. Parear a tomada no app SmartLife

1. Coloca a tomada em modo de pareamento (geralmente segurando o botão físico até a luz piscar rápido)
2. No app **SmartLife**: `+` → categoria "Tomada"/"Socket" → conecta no WiFi **2.4GHz** (a maioria dos dispositivos Tuya não suporta 5GHz)
3. Dá um nome pra ela no app — esse nome vai ser usado depois como identificador no CLI (ex: `AirFrier`, `quarto`)

### 2. Criar um Cloud Project na Tuya IoT Platform

1. Acessa [platform.tuya.com](https://platform.tuya.com/) e cria uma conta developer (ou faz login)
2. Cria um **Cloud Project** (Cloud Development)
3. Na aba **Devices** do projeto → **Link App Account** → **Add App Account** → escaneia o QR code com o app SmartLife (aba **Me** → ícone de QR code no canto superior direito)
4. Confirma no celular — isso vincula os dispositivos da sua conta SmartLife ao projeto
5. Na aba **Authorization**, anota o **API Key (Client ID)** e o **API Secret (Client Secret)** do projeto

### 3. Gerar o `devices.json` com o tinytuya wizard

```bash
python -m tinytuya wizard
```

Ele vai pedir:
- **API Key** e **API Secret** (do passo anterior)
- Um **Device ID** qualquer registrado (aparece na aba Devices do painel), usado só como ponto de partida pra puxar a lista completa
- Se quiser, deixa ele escanear a rede local também (a tomada precisa estar **ligada na energia e conectada ao WiFi** nesse momento pra aparecer com IP)

Isso gera um `devices.json` na pasta atual, com o formato:

```json
[
  {
    "name": "AirFrier",
    "id": "abcdefghijklmnopqrstuv",
    "key": "sua_local_key_aqui",
    "ip": "192.168.x.x",
    "version": "3.3"
  }
]
```

Move (ou copia) esse arquivo pra dentro da pasta do projeto (`src/arauto-devices/`), junto dos módulos Python.

> **Se o dispositivo aparecer sem `"ip"`** (mensagem `No IP found` no wizard): não é bloqueante no modo cloud — os campos `"ip"` e `"key"` (local key) não são usados pra controlar o dispositivo nesse modo, só o `"id"` importa. Eles continuam no arquivo por serem gerados automaticamente pelo wizard, mas ficam ociosos.

### 4. Confirmar o `tinytuya.json` (credenciais da Cloud API)

O mesmo `tinytuya wizard` do passo anterior também gera um `tinytuya.json` na pasta atual, com `apiKey`, `apiSecret` e região — é esse arquivo que o modo cloud usa pra autenticar a cada chamada. Confirma que ele está na mesma pasta dos módulos Python (`src/arauto-devices/`), junto do `devices.json`.

Esse arquivo é tão sensível quanto o `devices.json` (dá acesso de controle à sua conta Tuya) — mantém ele fora do controle de versão (ver seção de Segurança).

## Uso

### Modo direto (um comando por chamada)

```bash
python Cli.py list
python Cli.py status AirFrier
python Cli.py on AirFrier
python Cli.py off AirFrier
```

### Modo interativo (shell)

Rodando sem argumentos, entra num prompt onde você digita comandos em sequência sem precisar chamar `python Cli.py` toda vez:

```bash
python Cli.py
```
```
Modo interativo — digite um comando (list, on <nome>, off <nome>, status <nome>, exit)
>> list
>> status AirFrier
>> on AirFrier
>> exit
```

### Ajuda

```bash
python Cli.py --help
python Cli.py on --help
```

## Arquitetura

Camadas separadas por Command + Adapter + Repository, com injeção de dependência via interfaces (`CLI → Commands → DeviceController → CloudController/TuyaController`). Detalhamento completo — tabela de componentes, comparação Local vs Cloud, estrutura de arquivos, erros comuns e o que ficou fora do escopo — está em [`docs/arauto-devices-documentacao.md`](docs/arauto-devices-documentacao.md).

## Segurança

No modo cloud (padrão atual), o arquivo mais sensível é o **`tinytuya.json`** — ele contém `apiKey`/`apiSecret`, que dão controle total sobre os dispositivos vinculados à sua conta Tuya IoT Platform, de qualquer lugar com internet (não só na sua rede local, diferente da `local_key` do modo local). Trata esse arquivo com o mesmo cuidado que uma senha de conta.

O `devices.json` continua guardando `id`, `key` (local key) e `ip` — não usados pelo modo cloud, mas mantidos porque o wizard gera tudo junto. Se algum dia você voltar a usar o modo local (`TuyaController.py`), esses campos voltam a importar.

Não versiona nenhum dos dois em repositórios públicos. Se precisar compartilhar prints de tela ou colar em algum lugar, revoga e gera credenciais novas depois por precaução — tanto o API Secret quanto a `local_key` (essa última resetando e repareando o dispositivo).

Crie um `.gitignore` na raiz do projeto com pelo menos:

```
.venv/
devices.json
tinytuya.json
snapshot.json
tuya-raw.json
__pycache__/
*.pyc
```

O `.venv/` fica de fora porque é recriável a qualquer momento com `requirements.txt` (ver seção de Instalação) — versionar a pasta inteira deixaria o repositório pesado e amarrado ao seu sistema operacional específico.
