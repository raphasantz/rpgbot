🎲 A CIDADELA SEM SOL & A MINA PERDIDA DE PHANDELVER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TELEGRAM RPG BOT (REDNERDS)
Um Mestre de Jogo automatizado, integrado ao Telegram, utilizando 
Inteligência Artificial para narração, classificação de intenções estrita e 
geração de imagens procedurais.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 ESTRUTURA DO PROJETO
O sistema é modular, dividido para facilitar a manutenção e escalabilidade:

    main.py: O coração do bot. Gerencia os manipuladores de comandos 
    (handlers), o ciclo de vida das mensagens do Aiogram e a máquina de 
    estados (FSM) para criação de personagens. Delega as ações de texto 
    para o motor de exploração.

    exploracao.py: O cérebro do loop de gameplay. Intercepta as ações 
    em texto livre do jogador e orquestra a resolução (combate, navegação, 
    interação, uso de itens). Inclui o "Leão de Chácara" (trava de turnos/anti-spam) 
    e delega cálculos matemáticos para o combat_logic e IA para o ai_engine.

    ai_engine.py: A camada de inteligência com "Prompt Blindado". Utiliza 
    o GPT-4o-mini estritamente como tradutor de intenções mecânicas (Combate, 
    Navegação, etc.), zerando alucinações narrativas. Possui extração de loot 
    nativa em JSON e cache com sensibilidade ao contexto (objetos da sala). 
    Também gerencia a geração de imagens de salas via DALL-E 3 com sanitização de conteúdo.

    models.py: Define o esquema do banco de dados (SQLAlchemy), incluindo 
    tabelas para Jogadores, Campanhas, Inimigos, Cenas, Missões, Aventuras,
    NPCs dinâmicos, Encontros Aleatórios, Objetos Destrutíveis e sistema 
    de Reputação. Inclui campos para Hit Dice, Hazards, Multiplicador de 
    Ameaça e Status Effects (Caído, Agarrado, Cobertura, etc.).

    combat_logic.py: Implementa a mecânica de dados (d20), cálculo de acertos 
    baseados na CA (Classe de Armadura) e processamento de dano. Resolve 
    matematicamente as Vantagens e Desvantagens geradas por Status Effects 
    e inclui suporte a vulnerabilidades/resistências de Objetos Destrutíveis.

    stats_manager.py: Gerencia o rastreamento de progresso, incluindo o 
    ranking global, total de kills, danos causados e histórico de sessões.

    ui_utils.py: Contém as constantes de D&D (XP, HP por classe, bónus de 
    raça, Dados de Vida), utilidades de inventário, loot dinâmico e menus 
    interativos. Inclui dicionário de Keywords de Classe para ativação
    de habilidades por linguagem natural.

    mapa_engine.py: Módulo especializado em processar direções (Norte, Sul, 
    etc.) usando IA para validar a movimentação pelo mapa. Possui fallback 
    para casos em que a IA não identifica a direção.

    database.py: Gerenciamento seguro de sessões com commit/rollback 
    automático, garantindo a integridade dos dados.

    popular_phandelver.py: Script de migração para povoar o banco de dados 
    com "A Mina Perdida de Phandelver" (33 salas, 24 tipos de inimigos, 
    55 encontros, 22 objetos interativos, 8 missões).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛡️ AVENTURAS DISPONÍVEIS

    🏰 A Cidadela Sem Sol (Nível 1-3)
    61 salas exploráveis. Uma fortaleza subterrânea onde o mal 
    despertou. Explore a ravina, o covil dos goblins e confronte 
    a Árvore Gulthias no coração do Bosque do Crepúsculo.

    ⛏️ A Mina Perdida de Phandelver (Nível 3-5)
    33 salas exploráveis. Uma emboscada na estrada, uma vila 
    em perigo e uma mina perdida que esconde segredos sombrios.
    Enfrente o dragão Venomfang e o insidioso Nezznar.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛠️ FUNCIONALIDADES PRINCIPAIS

    🎭 Criação de Personagem: Sistema guiado para escolha de 
    Raça, Classe e Background, com rolagem de atributos (4d6).
    Auto-Party: ao criar um personagem, um código de grupo é 
    gerado automaticamente, permitindo jogo solo imediato.
    Atributos iniciais incluem Dados de Vida (Hit Dice) baseados
    no nível do personagem.

    🤝 Sistema de Party (Multiplayer): Até 5 jogadores na mesma 
    campanha, com sincronização de salas, chat interno (/falar) 
    e nivelamento automático de XP para novos membros. Lock de 
    concorrência (asyncio.Lock) protege cada party.

    📖 Narração Dinâmica com Prólogo: A IA narra cada ação de 
    forma visceral. Ao entrar numa aventura, o jogador recebe o 
    prólogo (via tabela Aventura no banco de dados) com pausa 
    dramática antes da primeira sala.

    ⚔️ Combate por Turnos com Trava Anti-Spam: Sistema de iniciativa,
    habilidades de classe (Fúria, Smite, Ataque Furtivo) e revide 
    inimigo. O número de ataques por turno escala dinamicamente 
    com o tamanho da party. Possui "Trava de Turno" para evitar 
    mensagens duplicadas em conexões lentas. Lembretes visuais com 
    botões inline auxiliam cada jogador.

    🛡️ Ações Táticas de Combate:
        - Esquiva (Dodge): Use seu turno para impor desvantagem 
          em todos os ataques inimigos contra você.
        - Combate com Duas Armas: Personagens com estilo de 
          duas armas podem realizar um ataque secundário como 
          ação bônus (sem bónus de dano).
        - Ações de Preparar (Ready Action): Prepare um ataque 
          para ser executado quando um gatilho específico ocorrer.
        - Ajuda (Aid Another): Use sua ação para dar vantagem 
          no próximo ataque de um aliado.
        - Cobertura (+2 CA): Proteja-se atrás do cenário para 
          ganhar bónus de Classe de Armadura contra inimigos.
        - Manobras de Combate: Tente empurrar, agarrar, derrubar 
          ou desarmar inimigos com testes de Força ou Destreza. 
          Sucesso deixa o inimigo vulnerável (vantagem para o grupo).

    🧬 Status Effects (Condições Matemáticas): Sistema completo 
    que aplica Vantagens e Desvantagens diretas no motor de rolagem:
        - Caído (Prone): Ataques corpo a corpo contra ti têm 
          vantagem. Os teus ataques têm desvantagem. Gaste parte 
          do movimento para te levantares (ação livre narrativa).
        - Agarrado (Grappled): A tua velocidade é reduzida a 0. 
          Não podes navegar ou fugir. Usa uma Manobra bem sucedida 
          (CD 14) para te libertares.
        - Envenenado: Sofres dano por round enquanto o efeito durar.
        - Atordoado: Perdes a tua ação no turno atual.

    ⚡ Keywords de Classe: Habilidades avançadas ativadas por 
    linguagem natural. Exemplos:
        - Bárbaro: "temerário" → Ataque Temerário (vantagem)
        - Guerreiro: "estocar" → +2 no ataque
        - Paladino: "abjurar" → +5 de CA
        - Monge: "torrente" → Ataque extra sem custo
        - Ladino: "furtivo" → Ataque Furtivo ativado

    🏳️ Moral dos Inimigos: Inimigos inteligentes fogem ou 
    rendem-se quando o grupo está com 20% ou menos da vida total.
    Bosses são imunes a este efeito. A vitória é concedida com
    todas as recompensas normalmente.

    ⚔️ Ataque de Oportunidade: Ao tentar fugir de um combate,
    o inimigo realiza um ataque real (d20 + modificador) contra 
    a CA do herói. Críticos causam dano dobrado e podem ser fatais.

    🧱 Objetos Destrutíveis: Objetos do cenário (fechaduras, 
    jaulas, estátuas) possuem HP, CA e podem ser destruídos 
    com ataques normais ou arrombados com um teste de Força 
    (d20 + mod_str vs break_threshold). Vulnerabilidades e 
    resistências são respeitadas.

    ⚠️ Hazards de Terreno: Salas podem conter perigos passivos
    (estrepes, gases, chão em brasa) que causam dano ou exigem
    testes de resistência (DEX, STR, CON) ao entrar.

    ⭐ Sistema de Reputação com Facções: Suas ações no mundo 
    (completar missões, ajudar NPCs) aumentam sua reputação 
    com as facções locais. Heróis com alta reputação recebem 
    descontos na loja (10% com 25+ de reputação, 20% com 50+).

    🧙 NPCs Dinâmicos e Encontros Aleatórios: Personagens não 
    jogáveis reagem a itens do inventário e oferecem diálogos 
    especiais. Alguns concedem missões ou informações cruciais.
    Salas podem conter encontros aleatórios com chance 
    configurável, tornando cada exploração única e imprevisível.

    🎯 Sistema de Missões Aprimorado: Itens de missão têm 100% 
    de drop garantido ao derrotar o inimigo-alvo, evitando 
    frustrações com RNG. O progresso é rastreado automaticamente.

    🏞️ Exploração Visual: Cada sala gera uma imagem única via 
    DALL-E 3. As imagens são cacheadas no banco para não gerar 
    custos repetidos. O conteúdo é sanitizado para evitar 
    violações de políticas (gore, violência extrema).

    🛒 Economia Interativa: Loja e venda com botões inline. 
    O comando /inventario permite equipar ou usar itens 
    diretamente pelos botões, sem comandos manuais. Preços
    são afetados pela sua reputação na vila.

    🎲 Rolagem Pública de Dados: O comando /r (ou /roll) permite 
    rolagens fora de combate visíveis para toda a party, com 
    suporte a fórmulas como "2d6+3".

    🧘 Descansos Curtos e Longos: Na masmorra, use /descansar 
    para um Descanso Curto que gasta 1 Hit Dice e recupera
    HP baseado no seu modificador de Constituição. Na vila,
    o Descanso Longo restaura tudo, incluindo Hit Dice.
    O Guerreiro recupera Surto de Ação em descansos curtos.

    💀 Morte e Intervenção Divina: Permadeath com uma única 
    chance de ressurreição ("Intervenção Divina"). Penalidades 
    de classe balanceadas (perda de ouro e/ou itens).

    🥋 Escala do Monge: O dano desarmado do Monge escala 
    automaticamente com o nível (1d4 → 1d6 no 5º, 1d8 no 11º,
    1d10 no 17º), tanto ao equipar quanto ao subir de nível.

    🧠 IA Segura e Robusta: Sistema de validação de intenções 
    com whitelist que impede que outputs inválidos da IA quebrem 
    o bot. Cache de intenções sensível ao contexto (objetos 
    disponíveis na sala) para evitar falsos positivos.

    🛡️ Segurança e Persistência: Context manager com commit/
    rollback automático no banco de dados. Tratamento global 
    de erros com mensagens "lore-friendly" para o jogador.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 COMO RODAR

    1. Configure o arquivo .env com as chaves:
       - TELEGRAM_TOKEN
       - OPENAI_API_KEY
       - DATABASE_URL

    2. Para a Cidadela, execute o script setup_oficial.py.
       Para Phandelver, execute popular_phandelver.py.

    3. Inicie o bot com python main.py.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📜 COMANDOS DISPONÍVEIS

    /criar       - Inicia a jornada do herói.
    /ficha       - Status detalhados, atributos, Hit Dice e perícias.
    /party       - Cria ou entra em grupos.
    /codigo      - Recupera o código de convite da sua party.
    /inventario  - Gerencia itens e ouro (com botões interativos).
    /equipar     - Equipa uma arma ou armadura.
    /loja        - Abre o Empório de Carvalhal (compra com botões).
    /vender      - Vende itens do inventário (venda com botões).
    /missoes     - Exibe o diário de missões.
    /descansar   - Descanso Curto (masmorra) ou Longo (vila).
    /dashboard   - Estatísticas de combate e ranking.
    /r           - Rola dados (suporte a fórmulas como 2d6+3).
    /falar       - Envia mensagem para toda a party.
    /reset       - Apagar personagem (com confirmação).
    /guia        - Manual completo do aventureiro.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎮 AÇÕES NARRATIVAS (DIGA O QUE QUER FAZER)

    "Ataco o goblin com minha espada"
    "Ajudo o meu aliado no ataque"
    "Protejo-me atrás da coluna"
    "Tento empurrar o inimigo para o abismo"
    "Arrombo a fechadura com meu machado"
    "Preparo um ataque para quando o dragão pousar"
    "Esquivo dos ataques inimigos"
    "Fujo para a sala anterior"
    "Vasculho a sala em busca de tesouros"
    "Falo com o ferreiro da vila"
    "Levanto-me do chão e ataco"
    "Tento libertar-me do agarrão do inimigo"
