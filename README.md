# 🎲 Telegram RPG Bot (RedNerds)
> Um Mestre de Jogo automatizado integrado ao Telegram, combinando mecânicas clássicas de D&D 5e com a flexibilidade da linguagem natural.

O **RPG Bot** não é apenas um gerador de texto. É um motor de RPG semi-determinístico onde a Inteligência Artificial atua como ponte entre a imaginação do jogador e a matemática rígida de um sistema de combate por turnos. 

Atualmente suporta duas campanhas completas: **A Cidadela Sem Sol** (Níveis 1-3) e **A Mina Perdida de Phandelver** (Níveis 3-5).

---

## 🎮 Fluxo de Gameplay
Como o jogo funciona na prática:
1. **O jogador entra numa aventura:** O grupo é posicionado na primeira sala da masmorra.
2. **O sistema descreve a cena:** Uma imagem procedural e a descrição do ambiente são enviadas.
3. **O jogador escreve ações em linguagem natural:** Ex: *"Salto sobre a mesa e ataco o goblin com a minha espada!"*
4. **O sistema interpreta a intenção:** A IA traduz a linguagem natural para uma intenção mecânica estrita (ex: `COMBATE`). *O sistema prioriza ações compatíveis com as regras implementadas do motor de jogo.*
5. **O motor resolve a ação:** A IA nunca executa regras diretamente. Todo o cálculo crítico é resolvido pelo motor Python (rolagem de d20, cálculo de CA, vantagens/desvantagens e HP).
6. **O resultado é narrado e persistido:** A consequência é descrita ao jogador e o estado do mundo é salvo na base de dados.

---

## ⚙️ Pipeline de Resolução Técnica
A arquitetura foi desenhada para impedir que respostas da IA alterem diretamente as regras do jogo, garantindo consistência mecânica.

```text
Entrada do Jogador (Linguagem Natural)
       ↓
Interpretação de Intenção (LLM com Whitelist Estrita)
       ↓
Normalização para Ação Mecânica
       ↓
Validação de Turno / Estado (Motor Python)
       ↓
Resolução Matemática (d20, AC, Status, RNG)
       ↓
Persistência Transacional (SQLAlchemy / ACID)
       ↓
Narração Contextual (Feedback ao Jogador)
