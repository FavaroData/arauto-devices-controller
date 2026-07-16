# SmartLife CLI — Glossário: Técnico ↔ Simples

Cada termo do design vem com o nome técnico e, do lado, o que ele significa em português claro — como se fosse explicado sem jargão.

---

## Padrões de projeto (design patterns)

| Termo técnico | Tradução simples |
|---|---|
| **Design Pattern** | Uma "receita" já testada por outros programadores pra resolver um problema comum de organização de código. Não é lei, é um jeito conhecido de arrumar a casa. |
| **Command Pattern** | Em vez de "fazer a ação na hora", você transforma a ação numa caixinha (objeto) que sabe se executar sozinha depois. Tipo escrever um post-it "ligar tomada" em vez de já sair ligando — o post-it pode ser guardado, testado, repassado pra outra pessoa executar. |
| **Adapter Pattern** | Um "tradutor" entre duas coisas que falam línguas diferentes. Ex: seu código fala "turn_on()", mas o tinytuya só entende "set_status(True, switch=1)". O Adapter fica no meio traduzindo. Igual um adaptador de tomada de viagem — sua lâmpada não muda, só o plugue no meio muda. |
| **Repository Pattern** | Uma classe cuja única tarefa é "buscar e guardar dados", escondendo de onde eles vêm (arquivo, banco de dados, API). O resto do código pede "me dá o Device chamado X" sem saber nem se importar se isso veio de um JSON ou de um banco. |
| **Dependency Injection (Injeção de Dependência)** | Em vez de uma classe criar sozinha as coisas que ela precisa usar, você "entrega" (injeta) essas coisas prontas pra ela por fora. Tipo: em vez do Command criar seu próprio jeito de ligar a tomada, você entrega pra ele um `DeviceController` já pronto. Isso permite trocar por uma versão falsa (fake) na hora do teste. |

---

## Peças da arquitetura

| Termo técnico | Tradução simples |
|---|---|
| **`Device` (dataclass)** | Um "molde de ficha" — só guarda dados (nome, IP, chave), não faz nada sozinho. Pense numa ficha de cadastro em papel: ela não age, só registra informação. |
| **`dataclass`** | Um recurso do Python pra criar essas "fichas" rapidinho, sem escrever manualmente o código repetitivo de guardar cada campo. |
| **`DeviceRepository`** | O "arquivista" — vai lá no `devices.json`, lê os dados brutos, e devolve pra você fichas (`Device`) já prontas e organizadas. |
| **`DeviceController` (interface abstrata)** | Um "contrato" ou "cardápio de promessas": diz que qualquer coisa que controla um dispositivo precisa saber `turn_on`, `turn_off` e `get_status` — mas não diz *como* fazer isso. Só a lista de exigências. |
| **Interface / porta** | Sinônimo de "contrato" acima. É a fronteira entre duas partes do sistema — define o que passa por ali, sem expor o que tem do outro lado. |
| **`TuyaDeviceController` (implementação real)** | Quem de fato *cumpre* o contrato acima, usando o tinytuya por trás dos panos. É o "funcionário" que sabe a língua específica da Tuya. |
| **`Command` / `OnCommand` / `OffCommand`** | Cada ação que a CLI pode pedir (ligar, desligar, status) vira sua própria "caixinha" de comando, que sabe se executar (`execute()`). |
| **`CLI` (`argparse`)** | A "recepcionista" do programa — só recebe o que você digitou no terminal e decide qual Command chamar. Não sabe nada sobre tomadas ou tinytuya. |
| **`main()`** | O "montador" — é onde todas as peças concretas (Repository real, Controller real) são criadas e entregues (injetadas) pros Commands. |

---

## Tratamento de erros

| Termo técnico | Tradução simples |
|---|---|
| **`Exception`** | O jeito do Python de dizer "algo deu errado, para tudo e me avisa". |
| **`DeviceNotFoundError`** | Um erro "sob medida": significa especificamente "não achei esse dispositivo no arquivo" — mais claro do que um erro genérico. |
| **`DeviceControllerError`** | Outro erro sob medida: "algo deu errado tentando falar com o dispositivo de verdade" (rede, chave errada, etc). |
| **`try / except`** | "Tenta fazer isso; se der esse erro específico, faz aquilo em vez de travar o programa." |
| **Exceção de domínio** | Um erro criado por você, com nome que faz sentido pro *seu* problema (tomadas, dispositivos) — em vez de usar só os erros genéricos que o Python já vem com. |

---

## Testes

| Termo técnico | Tradução simples |
|---|---|
| **`FakeDeviceController`** | Uma versão "de mentirinha" do Controller real — não liga em nenhuma tomada de verdade, só anota "fui chamado com isso aqui". Serve pra testar a lógica sem precisar de hardware por perto. |
| **Teste unitário** | Um pequeno programa que verifica se *uma peça específica* do seu código faz o que deveria, sozinha, sem depender do resto funcionando. |
| **`assert`** | "Eu afirmo que isso é verdade — se não for, o teste falha e me avisa." |
| **CI (Integração Contínua)** | Um robô que roda seus testes automaticamente (ex: toda vez que você sobe código pro GitHub) — precisa que os testes não dependam de coisas físicas, tipo sua tomada estar ligada na rede. |

---

## Ideia central por trás de tudo

| Termo técnico | Tradução simples |
|---|---|
| **Separação de responsabilidades (Separation of Concerns)** | Cada peça faz *uma coisa só* e faz bem. O Repository só lê dados. O Controller só fala com o dispositivo. O Command só decide a ordem das coisas. Ninguém faz o trabalho dos outros. |
| **Acoplamento (coupling)** | O quanto uma peça do código "gruda" na outra. Quanto mais uma peça depende dos detalhes internos de outra, mais difícil trocar uma sem quebrar a outra — por isso você usa interfaces (contratos) em vez de depender direto do tinytuya em todo lugar. |
| **Baixo acoplamento** | O objetivo do design: peças que se conectam só pelo "contrato" (interface), então você pode trocar uma peça por dentro sem que as outras percebam. |

---

## Resumo de uma frase por peça

- **`Device`** → uma ficha de dados, nada mais.
- **`DeviceRepository`** → busca fichas no arquivo.
- **`DeviceController`** → a promessa de "sei ligar/desligar/checar status".
- **`TuyaDeviceController`** → quem cumpre essa promessa usando o tinytuya.
- **`Command`** → uma ação empacotada, pronta pra rodar.
- **`CLI`** → só traduz o que você digitou em um Command.
- **Exceções de domínio** → erros com nome específico do seu problema, não erro genérico.
- **`FakeDeviceController`** → uma versão de mentira pra testar sem hardware.
