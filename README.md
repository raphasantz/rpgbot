<p align="center">
  <h1 align="center">⚔️ MezzaRPG</h1>
  <p align="center">
    <strong>RPG de mesa online com IA — D&D 5ª Edição pelo navegador</strong><br>
    Crie personagens, forme party com até 5 jogadores, explore masmorras e enfrente criaturas em tempo real.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/fastapi-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/postgresql-16-336791?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/GPT--4o--mini-IA-412991?logo=openai&logoColor=white" alt="OpenAI">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## 📖 O que é?

MezzaRPG é um **RPG de texto online** inspirado em Dungeons & Dragons 5ª Edição. Você cria um personagem, entra numa party com seus amigos, e joga digitando o que quer fazer. A IA interpreta suas ações, rola os dados e narra o que acontece — como um mestre de RPG que nunca dorme.

**Jogue em:** [mezza.rednerds.com.br](https://mezza.rednerds.com.br)

---

## ✨ Funcionalidades

### 🎭 Criação de Personagem
- Escolha entre 12 raças (Humano, Elfo, Anão, Halfling, Meio-Elfo, Meio-Orc, Gnomio, Tiefling, Draconato, Aasimar, Goliath, Deep Gnome)
- 5 classes (Guerreiro, Mago, Clérigo, Ladino) com subclasses D&D 5e
- Sistema de atributos (STR, DEX, CON, INT, WIS, CHA) com rolagem automática
- Inventário, equipamento e gold

### ⚔️ Combate por Turnos
- Mecânicas completas de D&D 5e: d20, crítico (dano dobrado), falha crítica
- Iniciativa, ataques corpo-a-corpo e à distância
- Magias por classe (Bola de Fogo, Chama Sagrada, Onda Trovejante, etc.)
- Escalabilidade por tamanho da party (1-5 jogadores)
- Loot dividido entre o grupo

### 🏰 Aventuras
- **A Cidadela Sem Sol** — 57 salas, boss final épico (druida renegado + corrompidos)
- **A Mina Perdida de Phandelver** — Vila, lojas, NPCs, caverna com dragão
- **Castelo Dentefino** — Reduto goblin, hobgoblins de elite, Nothic
- Missões secundárias com recompensas (XP, ouro, itens)

### 🤖 IA como Mestre
- Narração ambiental via GPT-4o-mini
- Interpretação de ações em linguagem natural ("examinar a sala", "atacar o goblin")
- Chat com NPCs (vendedores, taverna, personagens)
- Geração de imagens de cena em momentos críticos (FAL.ai)

### 👥 Multiplayer
- Party de até 5 jogadores
- Tempo real via WebSocket
- Party Lock — trava de turno para evitar conflitos
- Sincronização automática de inventário e status

### 🛒 Loja
- Poções, armas, armaduras, escudos
- Compra e venda de itens
- Equipamento automaticamente aplicado ao personagem

### 🔐 Autenticação
- Cadastro e login com email/senha (bcrypt)
- OAuth2 com Google Login
- JWT para sessões seguras
- CSRF protection em todos os endpoints state-changing

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Browser)                   │
│  HTML/CSS/JS + WebSocket (tempo real) + Jinja2 templates │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP + WS
┌──────────────────────▼──────────────────────────────────┐
│                    FastAPI (Backend)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ Auth     │ │ Game     │ │ WebSocket│ │ CSRF       │  │
│  │ Routes   │ │ Routes   │ │ Manager  │ │ Middleware  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────────┘  │
│       │             │            │                        │
│  ┌────▼─────────────▼────────────▼────────────────────┐  │
│  │              Game Engine Layer                      │  │
│  │  combat_logic • dnd_5e_rules • action_resolver     │  │
│  │  ai_engine_web • game_helpers • mapa_engine         │  │
│  └────────────────────┬───────────────────────────────┘  │
│                       │                                  │
│  ┌────────────────────▼───────────────────────────────┐  │
│  │            OpenAI GPT-4o-mini API                   │  │
│  │     (narração • interpretação • NPC chat)           │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  PostgreSQL (Banco)                      │
│  jogadores • aventuras • campanhas • encontros          │
│  inimigos • cenas • interativos • missoes • npcs        │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Estrutura do Projeto

```
mesanerd/
├── app/                          # Backend FastAPI
│   ├── main.py                   # App entrypoint, middleware, CORS
│   ├── auth.py                   # JWT + password hashing (bcrypt)
│   ├── google_oauth.py           # OAuth2 Google provider
│   ├── database.py               # SQLAlchemy engine + session
│   ├── ws_manager.py             # WebSocket connection manager
│   ├── templates_config.py       # Jinja2 template loader
│   ├── routes/
│   │   ├── auth.py               # Login, register, forgot/reset password
│   │   └── game.py               # Todas as rotas de jogo (~2400 linhas)
│   ├── templates/                # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── login.html / register.html
│   │   ├── lobby.html            # Seleção de party
│   │   ├── character_create.html # Criação de personagem
│   │   ├── jogo.html             # Tela principal de jogo
│   │   ├── shop.html             # Loja
│   │   └── me.html               # Perfil do jogador
│   └── static/
│       ├── css/main.css
│       ├── js/main.js
│       └── imagens/cenas/        # Imagens geradas por DALL-E/FAL
│
├── action_resolver.py            # Interpretação de ações via GPT (~1700 linhas)
├── ai_engine_web.py              # Narração IA + geração de imagens
├── combat_logic.py               # Motor de combate por turnos
├── dnd_5e_rules.py               # Regras D&D 5e (magias, equipamento, raças)
├── game_helpers.py               # Utilitários (split loot, scaling, sanitização)
├── mapa_engine.py                # Mapa do mundo + movimentação
├── modelos_web.py                # SQLAlchemy ORM models (~14 classes)
├── db_loader.py                  # Seed do banco com dados de aventuras
│
├── db_export/                    # Dados JSON das aventuras
│   ├── aventuras.json
│   ├── bestiario_cidadela.json
│   ├── campanhas.json
│   └── aliados_e_npcs.json
│
├── seed_db.py                    # Script de seed do banco
├── seed_aventuras_v2.py          # Seed das aventuras
├── seed_encontros.py             # Seed dos encontros
│
├── pygame_ui.py                  # Protótipo desktop (CustomTkinter)
├── models.py                     # Models do protótipo desktop
├── database.py                   # DB do protótipo desktop
├── ui_utils.py                   # Utils do protótipo desktop
│
├── test_difficulty_scaling.py    # Testes: escalabilidade por party
├── test_loot_split.py            # Testes: divisão de loot
├── test_integration.py           # Testes de integração
├── test_openai.py                # Testes da API OpenAI
│
├── requirements-web.txt          # Dependências da versão web
├── requirements.txt              # Dependências do protótipo desktop
├── .env                          # Variáveis de ambiente (não committar!)
└── .gitignore
```

---

## 🚀 Setup

### Pré-requisitos

- Python 3.12+
- PostgreSQL 14+
- Conta OpenAI (API key)
- Conta Google Cloud (para OAuth)

### 1. Clone o repositório

```bash
git clone https://github.com/raphasantz/rpgbot.git
cd rpgbot
git checkout mesanerd
```

### 2. Instale as dependências

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-web.txt
```

### 3. Configure as variáveis de ambiente

Crie o arquivo `.env` na raiz do projeto:

```env
# Banco de dados PostgreSQL
DATABASE_URL=postgresql://usuario:senha@localhost:5432/mesanerd

# OpenAI (para narração e interpretação de ações)
OPENAI_API_KEY=sk-sua-chave-aqui

# Google OAuth (para login com Google)
GOOGLE_CLIENT_ID=seu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-seu-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Segurança
MEZZARPG_SECRET_KEY=chave-aleatoria-muito-grande-aqui
MEZZARPG_ENV=dev

# FAL.ai (para geração de imagens de cena)
FAL_KEY=sua-chave-fal-aqui
```

### 4. Crie o banco e rode o seed

```bash
# Criar banco (PostgreSQL)
createdb mesanerd

# Rodar o schema + seed de dados
python seed_db.py
python seed_aventuras_v2.py
python seed_encontros.py
```

### 5. Execute o servidor

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Acesse: [http://localhost:8000](http://localhost:8000)

---

## 🌐 Deploy em Produção

### Docker + Cloudflare Tunnel (recomendado)

O projeto foi projetado para rodar em VPS com:

- **OpenResty/Nginx** como reverse proxy
- **PostgreSQL** em container Docker
- **Cloudflare Tunnel** para HTTPS automático
- **Uvicorn** como ASGI server

```bash
# Produção (sem --reload)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
```

Variáveis de ambiente para produção:

```env
MEZZARPG_ENV=production
DATABASE_URL=postgresql://user:pass@db-host:5432/mesanerd
```

---

## 📡 API Endpoints

### Autenticação

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/login` | Página de login |
| POST | `/login` | Autenticar usuário |
| GET | `/register` | Página de cadastro |
| POST | `/register` | Criar conta |
| GET | `/forgot` | Esqueci minha senha |
| POST | `/forgot` | Enviar email de redefinição |
| GET | `/reset?token=...` | Página de redefinição |
| POST | `/reset` | Redefinir senha |
| GET | `/auth/google/login` | Iniciar OAuth Google |
| GET | `/auth/google/callback` | Callback OAuth Google |
| POST | `/logout` | Encerrar sessão |

### Jogo

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/lobby` | Seleção/criação de party |
| GET | `/character/create` | Criação de personagem |
| POST | `/character/create` | Criar personagem |
| GET | `/jogar/{party_id}` | Tela principal do jogo |
| WS | `/ws/{party_id}` | WebSocket do jogo (tempo real) |

### API do Jogo

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/acao` | Executar ação do jogador |
| POST | `/api/acao/interpretar` | Interpretar ação em linguagem natural |
| GET | `/api/status` | Status atual do jogador |
| GET | `/api/inventario` | Inventário do jogador |
| GET | `/api/stats` | Estatísticas detalhadas |
| GET | `/api/missoes` | Missões ativas |
| POST | `/api/equipar` | Equipar item |
| POST | `/api/vender` | Vender item |
| POST | `/api/dice` | Rolar dados (d4-d20) |
| POST | `/api/reset` | Resetar personagem |
| GET | `/api/dashboard` | Dashboard do jogador |

### Loja & IA

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/shop` | Página da loja |
| POST | `/shop/buy` | Comprar item |
| POST | `/api/taverna/chat` | Chat com taverna (IA) |
| POST | `/api/npc/chat` | Chat com NPC (IA) |
| POST | `/api/gerar-imagem-critica` | Gerar imagem de cena (FAL.ai) |
| GET | `/api/class-tips` | Dicas da classe do jogador |
| GET | `/api/class-tips/all` | Todas as dicas de classes |

### Missões

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/missao/concluir` | Concluir missão e receber recompensas |

---

## 🗄️ Modelos de Banco

| Modelo | Descrição |
|--------|-----------|
| `JogadorWeb` | Usuário (email, senha, personagem, inventário, stats) |
| `Aventura` | Aventura (nome, descrição, dificuldade) |
| `CampanhaWeb` | Campanha de um jogador (progresso, sala atual) |
| `Encontro` | Encontro dentro de uma aventura |
| `Inimigo` | Inimigo (HP, AC, ataque, XP, loot) |
| `Cena` | Sala/cena (descrição, interativos, saídas) |
| `Interativo` | Objeto/portal/NPC interativo na cena |
| `ObjetoDestrutivel` | Objeto que pode ser destruído |
| `EstatisticasJogador` | Stats detalhados (mortes, dano, heals) |
| `HistoricoPartida` | Log de partidas |
| `Missao` | Missão secundária (recompensas, objetivos) |
| `Npc` | NPCs da taverna/vila |
| `EncontroAleatorio` | Encontros aleatórios por região |

---

## 🔒 Segurança

O projeto passou por auditoria OWASP completa (junho 2026) com 13 findings corrigidos:

| Severidade | Finding | Status |
|------------|---------|--------|
| 🔴 Crítico | Stored XSS via nome de personagem (cross-user) | ✅ Corrigido |
| 🟠 Alto | XSS via respostas de IA renderizadas como HTML | ✅ Corrigido |
| 🟠 Alto | Sem rate limit em geração de imagem (abuso FAL.ai) | ✅ Corrigido |
| 🟠 Alto | Race condition em conclusão de missão | ✅ Corrigido |
| 🟠 Alto | Sem timeout na chamada síncrona OpenAI | ✅ Corrigido |
| 🟡 Médio | 29 print() em produção → logger estruturado | ✅ Corrigido |
| 🟡 Médio | CORS com wildcards → métodos/headears restritos | ✅ Corrigido |
| 🟡 Médio | Nome sem max_length no Form | ✅ Corrigido |
| 🟡 Médio | Substring matching em equipar/vender | ✅ Corrigido |
| 🟡 Médio | OAuth vazava exceção na URL | ✅ Corrigido |
| 🔵 Baixo | FAL.ai safety checker desabilitado | ✅ Corrigido |
| 🔵 Baixo | SessionMiddleware https_only quebrava dev | ✅ Corrigido |
| 🔵 Baixo | Política de senha fraca (6 chars) | ✅ Corrigido |

### Medidas de segurança implementadas:

- **Sanitização de input**: `sanitize_user_text()` remove HTML e trunca texto
- **Sanitização de output IA**: `_sanitize_ai_html()` com whitelist de tags seguras
- **CSRF protection**: Token httponly em todos os endpoints state-changing
- **Rate limiting**: RateLimiter por IP em endpoints críticos
- **Password hashing**: bcrypt com salt via passlib
- **JWT**: Tokens assinados com expiração
- **CORS restritivo**: Apenas GET/POST, Content-Type + X-CSRF-Token
- **SELECT FOR UPDATE**: Anti race condition em operações financeiras
- **Input validation**: Pydantic models + max_length em Forms
- **Logging estruturado**: Zero print() em produção

---

## 🧪 Testes

```bash
# Todos os testes
pytest

# Com verbose
pytest -v

# Testes específicos
pytest test_difficulty_scaling.py -v  # Escalabilidade por party
pytest test_loot_split.py -v          # Divisão de loot
pytest test_integration.py -v         # Integração geral
```

---

## 🎮 Mecânicas do Jogo

### Combate
- **Turnos**: Cada jogador escolhe ação → sistema resolve por iniciativa
- **Ataque**: `d20 + modificador > AC do inimigo` = acerto
- **Dano**: Arma + modificador de atributo (STR para corpo-a-corpo, DEX para à distância)
- **Crítico**: No natural 20, dano dobrado
- **Falha crítica**: No natural 1, miss automático

### Classes
| Classe | Atributo Principal | Magia Exemplo |
|--------|-------------------|---------------|
| Guerreiro | STR | Golpe Extra |
| Mago | INT | Bola de Fogo, Mísseis Mágicos |
| Clérigo | WIS | Chama Sagrada, Escudo da Fé |
| Ladino | DEX | Punhalada Afiada, Passos Sombrios |

### Escalabilidade
O jogo ajusta automaticamente:
- **HP dos inimigos**: Base × (0.6 + 0.4 × num_jogadores)
- **Dano**: Proporcional ao tamanho da party
- **Loot**: Dividido igualmente entre membros

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.12 + FastAPI |
| Banco | PostgreSQL 16 + SQLAlchemy 2.0 |
| IA | OpenAI GPT-4o-mini (narração + ações) |
| Imagens | FAL.ai (FLUX Schnell) |
| Frontend | HTML/CSS/JS + Jinja2 |
| Tempo Real | WebSocket (FastAPI native) |
| Auth | JWT + bcrypt + Google OAuth2 |
| Deploy | Uvicorn + Docker + Cloudflare Tunnel |
| Segurança | OWASP audit, CSRF, rate limiting |

---

## 📄 Licença

Este é um projeto pessoal. Todos os direitos reservados.

---

<p align="center">
  <strong>MezzaRPG</strong> — RPG de mesa, mas pela internet. ⚔️🎲
</p>
