# ⚔️ MezzaRPG

## O que é?

É um **RPG de texto online**, tipo aquele RPG de mesa que você joga com os amigos, só que pelo navegador. Você cria um personagem, entra num grupo com seus amigos, e joga digitando o que quer fazer. A IA interpreta o que você digita e narra o que acontece — tipo um mestre de RPG que nunca dorme.

## Como funciona?

Você cria seu personagem (guerreiro, mago, clérigo, ladino, etc.) e entra numa party com até **5 jogadores**. A party começa numa taverna, e de lá você escolhe qual aventura quer seguir.

Você digita suas ações em linguagem normal — tipo "examinar a sala", "atacar o goblin", "ir para norte", "comprar poção" — e o jogo interpreta, rola os dados, e te narra o resultado. Igual jogar D&D numa mesa, só que online.

## As Aventuras

**🏰 A Cidadela Sem Sol** — Uma cidadela subterrânea abandonada tomada por goblins, kobolds e criaturas sombrias. Você explora salas com armadilhas, enigmas, portas secretas e bosses. O boss final é épico — um druida renegado que plantou uma árvore amaldiçoada, e você enfrenta ele + os corrompidos ao mesmo tempo. 57 salas pra explorar.

**⛏️ A Mina Perdida de Phandelver** — Você começa numa vila, visita lojas e tavernas, conversa com NPCs, e depois parte pra uma caverna cheia de goblins, lobos e até um filhote de dragão. Tem até um mago vilão escondido no porão de uma mansão abandonada.

**🏯 Castelo Dentefino** — O reduto goblin propriamente dito, com guardas de elite (hobgoblins), um gnomo preso que vira aliado, e um Nothic — uma criatura horripilante que guarda segredos.

## As Mecânicas

O jogo segue as regras de **Dungeons & Dragons 5ª edição**:

- Combate por turnos — rola um d20 e compara com a defesa do inimigo
- Crítico = dano dobrado, falha = errou tudo
- Cada classe tem magia própria (raio de fogo, chama sagrada, onda trovejante...)
- Tem loja pra comprar poções, armas e armaduras
- Level up conforme você derrota inimigos
- Os inimigos escalam de acordo com o tamanho do grupo (se vocês são 2, é mais fácil; se são 5, é mais difícil)
- O loot (ouro e itens) é dividido entre o grupo

## Multiplayer

Você joga com seus amigos em tempo real. Cada um digita sua ação, o jogo resolve na ordem de iniciativa, e todo mundo vê o resultado na hora. TemParty Lock pra ninguém bagunçar a vez do outro.

## Detalhes técnicos (pra quem curte)

- Backend: Python + FastAPI
- Banco: PostgreSQL
- IA: GPT-4o-mini (narração + interpretação de ações)
- Frontend: HTML/CSS/JS com WebSocket pra tempo real
- Auth: JWT + Google Login
- Deploy: VPS + Docker + Cloudflare Tunnel
- Tem um protótipo desktop offline também (CustomTkinter)

---

**MezzaRPG** — RPG de mesa, mas pela internet. ⚔️🎲
