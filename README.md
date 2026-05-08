# 🎲 Telegram RPG Bot (RedNerds)
> Um Mestre de Jogo automatizado integrado ao Telegram, combinando mecânicas clássicas de D&D 5e com a flexibilidade da linguagem natural.

O **RPG Bot** não é apenas um gerador de texto. É um motor de RPG semi-determinístico onde a Inteligência Artificial atua como ponte entre a imaginação do jogador e a matemática rígida de um sistema de combate por turnos. 

Atualmente suporta duas campanhas completas: **A Cidadela Sem Sol** (Níveis 1-3) e **A Mina Perdida de Phandelver** (Níveis 3-5).

---

## 🎮 Fluxo de Gameplay
Como o jogo funciona na prática:
1. **O jogador entra numa aventura:** O grupo é posicionado na primeira sala da masmorra.
2. **O sistema descreve a cena:** Uma imagem procedural e a descrição do ambiente são enviadas.
3. **O jogador escreve qualquer ação em texto livre:** Ex: *"Salto sobre a mesa e ataco o goblin com a minha espada!"*
4. **O sistema interpreta a intenção:** A IA traduz o texto livre para uma ação mecânica estrita (ex: `COMBATE`).
5. **O motor resolve a ação:** O sistema Python rola o d20, calcula a Classe de Armadura, aplica vantagens/desvantagens e desconta o HP.
6. **O resultado é narrado e persistido:** A consequência é descrita ao jogador e o estado do mundo é salvo na base de dados.

---

## ⚙️ Pipeline de Resolução Técnica
A arquitetura foi desenhada para reduzir drasticamente inconsistências e garantir que o estado do jogo é imutável perante alucinações de IA.

```text
Entrada do Jogador (Linguagem Natural)
       ↓
Classificação de Intenção (LLM com Whitelist Estrita)
       ↓
Validação Mecânica (Motor Python)
       ↓
Resolução Matemática (RNG, AC, Hit Dice, Status)
       ↓
Persistência Segura (SQLAlchemy / Transação ACID)
       ↓
Narração Final (Feedback ao Jogador)
