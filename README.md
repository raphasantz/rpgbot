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
