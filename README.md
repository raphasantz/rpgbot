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
