<<<<<<< HEAD
# 🎲 Telegram RPG Bot (RedNerds)

> Um Mestre de Jogo automatizado integrado ao Telegram, combinando mecânicas clássicas de Dungeons & Dragons 5th Edition com a flexibilidade da linguagem natural.

O **RPG Bot** não é apenas um gerador de texto.
É um motor de RPG semi-determinístico onde a Inteligência Artificial atua como ponte entre a imaginação do jogador e a resolução matemática rígida de um sistema de combate por turnos.

A IA interpreta intenções e contextualiza ações, enquanto todas as regras críticas do jogo são resolvidas pelo motor Python.

---

# 🏰 Aventuras Disponíveis

## 🏰 A Cidadela Sem Sol (Nível 1–3)

61 salas exploráveis.
Uma fortaleza subterrânea esquecida onde o mal voltou a despertar. Explore ravinas, covis goblins e enfrente a Árvore Gulthias no coração do Bosque do Crepúsculo.

## ⛏️ A Mina Perdida de Phandelver (Nível 3–5)

33 salas exploráveis.
Uma emboscada na estrada leva os aventureiros até uma mina ancestral repleta de segredos, facções e criaturas perigosas. Enfrente Venomfang e o misterioso Nezznar.

---

# 🎮 Fluxo de Gameplay

O sistema foi desenhado para permitir interação em linguagem natural sem abrir mão de regras consistentes.

## Como o jogo funciona na prática

1. **O jogador entra numa aventura**
   O grupo é posicionado numa sala da masmorra.

2. **O sistema descreve o ambiente**
   O jogador recebe:

   * descrição narrativa
   * inimigos presentes
   * objetos interativos
   * imagem procedural da sala

3. **O jogador escreve ações em linguagem natural**
   Exemplos:

   * `"Ataco o goblin com a minha espada"`
   * `"Protejo-me atrás da coluna"`
   * `"Tento empurrar o inimigo para o abismo"`

4. **A IA interpreta a intenção mecânica**
   O texto é convertido para ações válidas do sistema:

   * COMBATE
   * MANOBRA
   * NAVEGAÇÃO
   * INTERAÇÃO
   * COBERTURA
   * DESCANSO
   * etc.

5. **O motor resolve matematicamente a ação**
   O sistema:

   * rola dados
   * calcula Classe de Armadura
   * aplica vantagens/desvantagens
   * valida estados e condições
   * executa dano
   * persiste o estado do combate

6. **O resultado é narrado ao jogador**
   A consequência da ação é descrita e o estado do mundo é atualizado.

---

# ⚙️ Pipeline de Resolução

A arquitetura foi desenhada para impedir que a IA altere diretamente as regras do jogo.

```text
Entrada do Jogador (Linguagem Natural)
                ↓
Interpretação de Intenção (LLM)
                ↓
Normalização para Ação Mecânica
                ↓
Validação de Turno / Estado
                ↓
Resolução Matemática
(d20, AC, Status, RNG)
                ↓
Persistência Transacional
(SQLAlchemy / ACID)
                ↓
Narração Contextual
```

---

# 🧠 Filosofia da Arquitetura

O sistema segue um modelo híbrido:

| Camada         | Responsabilidade              |
| -------------- | ----------------------------- |
| IA             | Interpretar linguagem natural |
| Motor Python   | Resolver regras e matemática  |
| Banco de Dados | Persistir o estado do mundo   |
| Telegram       | Interface de interação        |

A IA nunca executa regras diretamente.
Todo cálculo crítico é resolvido deterministicamente pelo motor Python.

---

# ⚔️ Principais Mecânicas

## ⚔️ Combate por Turnos

* Sistema de iniciativa
* Ataques de oportunidade
* Revide inimigo
* Escalonamento por tamanho da party
* Trava anti-spam e validação de turno

---

## 🛡️ Ações Táticas

* Esquiva (Dodge)
* Cobertura (+2 AC)
* Ajuda (Aid Another)
* Preparar ação (Ready Action)
* Combate com duas armas
* Manobras:

  * empurrar
  * derrubar
  * agarrar
  * desarmar

---

## 🧬 Status Effects

Condições afetam matematicamente o sistema de combate:

| Condição   | Efeito                       |
| ---------- | ---------------------------- |
| Caído      | vantagem melee contra o alvo |
| Agarrado   | velocidade reduzida a 0      |
| Envenenado | dano por turno               |
| Atordoado  | perde a ação                 |

---

## 🏳️ Moral dos Inimigos

Inimigos inteligentes podem:

* fugir
* render-se
* reorganizar comportamento

Bosses são imunes.

---

## 🧱 Objetos Destrutíveis

Portas, estátuas, jaulas e fechaduras possuem:

* HP
* Classe de Armadura
* Resistências
* Vulnerabilidades

Podem ser:

* destruídos
* arrombados
* manipulados

---

## ⚠️ Hazards de Terreno

Salas podem conter:

* gases
* fogo
* armadilhas
* estrepes
* pisos perigosos

Exigem testes de resistência:

* STR
* DEX
* CON

---

# 🤝 Multiplayer e Progressão

## 👥 Sistema de Party

* até 5 jogadores
* sincronização de salas
* chat interno
* compartilhamento de progresso

---

## ⭐ Sistema de Reputação

As ações do grupo afetam facções locais:

* descontos
* diálogos especiais
* desbloqueios narrativos

---

## 🎯 Sistema de Missões

* progresso automático
* drops garantidos para objetivos críticos
* rastreamento persistente

---

## 🧘 Descanso Curto e Longo

### Descanso Curto

* consome Hit Dice
* recupera HP

### Descanso Longo

* restaura:

  * HP
  * habilidades
  * Hit Dice

---

# 🏞️ Exploração Visual

Cada sala pode gerar:

* imagem procedural
* ambientação visual
* descrição contextual

As imagens:

* são cacheadas
* possuem sanitização de conteúdo
* evitam custos repetidos de geração

---

# 🧠 Inteligência Artificial

## O que a IA faz

* interpreta intenções
* contextualiza narrativa
* auxilia exploração
* extrai estruturas em JSON

## O que a IA NÃO faz

* alterar regras
* calcular dano
* decidir resultados críticos
* modificar estado diretamente

---

# 🧱 Stack Técnica

* Python 3.13
* Aiogram 3
* SQLAlchemy
* AsyncIO
* OpenAI API
* PostgreSQL / SQLite
* DALL·E 3

---

# 📁 Estrutura do Projeto

```text
📦 raiz_do_projeto
 ┣ 📜 main.py
 ┣ 📜 exploracao.py
 ┣ 📜 ai_engine.py
 ┣ 📜 combat_logic.py
 ┣ 📜 models.py
 ┣ 📜 database.py
 ┣ 📜 mapa_engine.py
 ┣ 📜 stats_manager.py
 ┣ 📜 ui_utils.py
 ┣ 📜 popular_phandelver.py
 ┗ 📂 handlers/
    ┣ 📜 gerais.py
    ┣ 📜 inventario.py
    ┣ 📜 jogador.py
    ┣ 📜 criacao.py
    ┗ 📜 classe.py
```

---

# 🚀 Como Rodar

## 1. Configure o `.env`

```env
TELEGRAM_TOKEN=
OPENAI_API_KEY=
DATABASE_URL=
```

---

## 2. Popule a base de dados

### Para A Cidadela Sem Sol

```bash
python setup_oficial.py
```

### Para Phandelver

```bash
python popular_phandelver.py
```

---

## 3. Inicie o bot

```bash
python main.py
```

---

# 📜 Comandos Disponíveis

| Comando       | Função                   |
| ------------- | ------------------------ |
| `/criar`      | Cria personagem          |
| `/ficha`      | Exibe atributos e status |
| `/party`      | Cria ou entra em grupos  |
| `/inventario` | Gerencia itens           |
| `/equipar`    | Equipa armas e armaduras |
| `/loja`       | Abre a loja              |
| `/vender`     | Vende itens              |
| `/missoes`    | Diário de missões        |
| `/descansar`  | Descanso curto/longo     |
| `/dashboard`  | Estatísticas             |
| `/r`          | Rolagem de dados         |
| `/falar`      | Chat da party            |
| `/reset`      | Remove personagem        |
| `/guia`       | Manual do aventureiro    |

---

# 🎭 Exemplos de Ações

```text
"Ataco o goblin com minha espada"
"Ajudo o meu aliado no ataque"
"Protejo-me atrás da coluna"
"Tento empurrar o inimigo para o abismo"
"Arrombo a fechadura com meu machado"
"Preparo um ataque para quando o dragão pousar"
"Esquivo dos ataques inimigos"
"Fujo para a sala anterior"
"Levanto-me do chão e ataco"
"Tento libertar-me do agarrão do inimigo"
```

---

# 🔮 Roadmap

* [ ] Sistema avançado de magia
* [ ] Bosses multi-fase
* [ ] NPCs com memória contextual
* [ ] Dungeon procedural
* [ ] Sistema climático
* [ ] Eventos globais persistentes
* [ ] Combate PvP opcional
* [ ] Suporte a múltiplas campanhas simultâneas

---

# 📌 Estado Atual do Projeto

O projeto encontra-se em desenvolvimento ativo, com foco em:

* estabilidade do combate
* consistência mecânica
* expansão de campanhas
* melhoria do motor de resolução

---

# 🧙 Objetivo do Projeto

Criar uma experiência de RPG jogável diretamente no Telegram, mantendo:

* liberdade narrativa
* regras previsíveis
* persistência de mundo
* combate consistente
* interação natural em texto livre
=======
# 🎲 Telegram RPG Bot (RedNerds)

> Um Mestre de Jogo automatizado integrado ao Telegram, combinando mecânicas clássicas de Dungeons & Dragons 5th Edition com a flexibilidade da linguagem natural.

O **RPG Bot** não é apenas um gerador de texto. É um motor de RPG determinístico orientado a eventos, onde a Inteligência Artificial atua **exclusivamente** como ponte entre a imaginação do jogador e a resolução matemática rígida de um sistema de combate por turnos.

A IA interpreta intenções e extrai dados estruturados (JSON Mode), enquanto **todas** as regras críticas do jogo (Iniciativa, HP, Dano, Game Over, Perigos de Terreno) são resolvidas pelo motor interno em Python.

---

# 🏰 Aventuras Disponíveis

## 🏰 A Cidadela Sem Sol (Nível 1–3)

61 salas exploráveis. Uma fortaleza subterrânea esquecida onde o mal voltou a despertar. Explore ravinas, covis goblins e enfrente a Árvore Gulthias no coração do Bosque do Crepúsculo.

## ⛏️ A Mina Perdida de Phandelver (Nível 3–5)

33 salas exploráveis. Uma emboscada na estrada leva os aventureiros até uma mina ancestral repleta de segredos, facções e criaturas perigosas. Enfrente Venomfang e o misterioso Nezznar.

---

# 🎮 Fluxo de Gameplay

O sistema foi desenhado para permitir interação em linguagem natural sem abrir mão de regras D&D 5e consistentes.

## Como o jogo funciona na prática

1. **Ação em Linguagem Natural:** O jogador envia algo como `"Tento empurrar o goblin para o abismo e puxo a minha espada!"`.
2. **Extração de Intenção (IA):** O `ai_engine.py` traduz o texto para um formato JSON estrito (ex: `{"intencao": "MANOBRA", "manobra": "empurrar", "alvo": "goblin"}`).
3. **O Cérebro Determinístico:** O `action_resolver.py` intercepta o JSON. Ele rola a iniciativa, verifica se o jogador está atordoado ou envenenado, rola o d20 de Força vs CD do monstro e aplica o resultado matemático puro.
4. **Resolução de Turno & Retaliação:** O motor processa o ataque de oportunidade inimigo (caso seja fuga) ou a retaliação do turno dos monstros vivos na sala.
5. **Narração Cinematográfica:** Os números frios voltam para a IA apenas para ganhar "sabor" narrativo.
6. **Interface (Telegram):** O `exploracao.py` junta tudo, exibe o HP, verifica mortes (Game Over) e atualiza os botões de navegação.

---

# ⚙️ Pipeline de Resolução (A Nova Arquitetura)

A arquitetura foi recentemente refatorada para impedir **completamente** que a IA altere as regras do jogo (zero alucinações de HP ou de loot).

```text
Entrada do Jogador (Linguagem Natural) no Telegram
                ↓
[ ai_engine.py ] Interpretação e Extração (Strict JSON)
                ↓
[ action_resolver.py ] Validação de Status (Atordoado, Caído)
                ↓
[ combat_logic.py ] Resolução Matemática (d20, Modificadores, CA)
                ↓
[ action_resolver.py ] Ações Inimigas / Iniciativa / Hazards (Armadilhas)
                ↓
Persistência Transacional (SQLAlchemy / PostgreSQL)
                ↓
[ ai_engine.py ] Narração Contextual do Resultado Matemático
                ↓
[ exploracao.py ] Renderização da UI, Triggers de Morte e Imagens

```

---

# 🧠 Filosofia da Arquitetura

O sistema segue um modelo de isolamento de domínios:

| Camada | Módulo Principal | Responsabilidade |
| --- | --- | --- |
| **Interface** | `exploracao.py` | Trava assíncrona (Locks), UI, botões, Game Over |
| **Tradução** | `ai_engine.py` | Extrair intenção (JSON) e dar sabor ao texto |
| **Cérebro** | `action_resolver.py` | Roteamento, iniciativa, vida, veneno, navegação |
| **Matemática** | `combat_logic.py` | Fórmulas D&D brutas, CA, críticos, vantagem |
| **Estado** | `models.py` | Modelos ACID, inventário, missões, party |

---

# ⚔️ Principais Mecânicas Implementadas

## ⚔️ Combate por Turnos

* **Iniciativa Real:** Rolada a cada embate para definir a ordem das ações.
* **Ataques de Oportunidade:** Inimigos atacam automaticamente se o jogador tentar fugir de uma sala hostil.
* **Sistema Anti-Spam (Locks):** Jogadores numa mesma *party* não podem atropelar as ações uns dos outros.

## 🛡️ Status Effects e Hazards

Condições afetam matematicamente o sistema em tempo real:

* **Caído:** Desvantagem em ataques.
* **Agarrado:** Velocidade 0 (bloqueia navegação até sucesso em manobra).
* **Envenenado:** Recebe dano passivo no início de cada turno.
* **Atordoado:** O jogador perde a ação da rodada.
* **Hazards de Terreno:** Testes automáticos (DEX, CON, STR) ao entrar em salas com armadilhas, veneno ou fogo.

## 🧱 Objetos Destrutíveis & Interativos

Portas, estátuas, baús e fechaduras possuem:

* HP, Classe de Armadura (CA).
* **Vulnerabilidades:** (Ex: Esqueletos sofrem dano dobrado para armas de contusão).
* **Interações:** Testes de Perícia baseados em atributos (`mod_dex`, `mod_str`).

---

# 🤝 Multiplayer e Progressão

* **Sistema de Party:** Até 5 jogadores, sincronização de salas e trava de turnos mútua.
* **Sistema de Missões:** Progresso automático, rastreamento de itens de missão persistente no inventário (Ex: Dentes de Goblin para o Ferreiro).
* **Dashboard e Estatísticas:** `stats_manager.py` mantém um histórico de taxa de acerto, tempo de jogo, monstros derrotados e ranking de XP.

---

# 🧱 Stack Técnica

* **Linguagem:** Python 3.10+
* **Framework Bot:** Aiogram 3.x (Totalmente Assíncrono)
* **Banco de Dados:** SQLAlchemy 2.0 com `asyncpg` (PostgreSQL)
* **IA:** OpenAI API (GPT-4o-mini para JSON e Narração, DALL-E 3 para geração de cenários)
* **Gerenciamento de Estado:** Sistema de Locks na memória (`asyncio.Lock`) para evitar condições de corrida no multiplayer.

---

# 📁 Estrutura do Projeto

```text
📦 raiz_do_projeto
 ┣ 📜 main.py                  # Entrypoint, inicialização e rotas genéricas
 ┣ 📜 exploracao.py            # Loop principal do jogo, UI e Game Over
 ┣ 📜 action_resolver.py       # O Cérebro: Regras D&D, iniciativa e roteamento
 ┣ 📜 ai_engine.py             # JSON Mode estrito, DALL-E 3 e narração
 ┣ 📜 combat_logic.py          # Matemática isolada de combate e objetos
 ┣ 📜 models.py                # Schema do banco de dados
 ┣ 📜 database.py              # Conexões assíncronas
 ┣ 📜 mapa_engine.py           # Fallback de processamento espacial/direcional
 ┣ 📜 stats_manager.py         # Histórico, ranking e dashboard
 ┣ 📜 ui_utils.py              # Constantes (XP, Magias) e formatação de texto
 ┗ 📂 handlers/                # Rotas secundárias (Criação, Menus, Ficha)

```

---

# 🚀 Como Rodar

## 1. Configure o `.env`

```env
TELEGRAM_TOKEN=seu_token_aqui
OPENAI_API_KEY=sua_chave_aqui
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

```

## 2. Inicie o banco e popule a aventura

A própria inicialização do `main.py` roda as migrações assíncronas automaticamente (`Base.metadata.create_all`). Para injetar os mapas:

```bash
python setup_oficial.py
# ou
python popular_phandelver.py

```

## 3. Inicie o motor

```bash
python main.py

```

---

# 📜 Comandos Disponíveis

| Comando | Função |
| --- | --- |
| `/criar` | Cria o seu personagem |
| `/ficha` | Exibe atributos, HP e status atual |
| `/party` | Cria ou entra num grupo multiplayer |
| `/inventario` | Mostra equipamentos e itens de missão |
| `/equipar` | Equipa armas/armaduras (altera stats) |
| `/missoes` | Exibe o Diário de Missões ativas |
| `/dashboard` | Exibe as estatísticas e ranking global |
| `/descansar` | Gasta Hit Dice para curar (ou Full HP) |
| `/falar` | Envia mensagens seguras para a party |

---

# 🔮 Roadmap

* [x] Conversão estrita de IA para Motor Matemático (Action Resolver).
* [x] Sistema de Party e Bloqueio de Concorrência (Async Locks).
* [ ] Sistema avançado de Inventário com Pesos.
* [ ] Bosses com múltiplas fases.
* [ ] Dungeon crawling procedural (geração infinita de mapas).
* [ ] Sistema climático e eventos globais no hub principal.
>>>>>>> 39e774fc8edc1899de851f9f287639d320f8e080
