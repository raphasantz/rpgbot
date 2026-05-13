import asyncio
import os
import random
import math
import logging
import json
import unicodedata
import string
import re
import traceback
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, ErrorEvent
from aiogram import F

from handlers.menus import router as menus_router
from handlers.exploracao import router as exploracao_router, lock_garbage_collector

# Configuração de Logs
logging.basicConfig(level=logging.INFO)

print("🔄 Carregando módulos do projeto...")
try:
    from database import get_db_session, engine, Base
    import models
    from models import Jogador, Campanha, Encontro, Inimigo, Cena, EstatisticasJogador, HistoricoPartida, Interativo, Missao, Npc, EncontroAleatorio, ObjetoDestrutivel
    from ai_engine import interpretar_acao, narrar_combate, decidir_atributo_teste, narrar_ambiente, gerar_imagem_sala
    from ui_utils import (
        XP_POR_NIVEL, HP_POR_CLASSE, INVENTARIO_POR_CLASSE, IMAGENS_INIMIGOS,
        calcular_modificador, rolar_atributo_4d6,
        processar_saque, obter_inventario_limpo, formatar_inventario_para_display,
        texto_saidas, teclado_saidas, resumo_status,
        menu_classes, menu_racas, menu_backgrounds,
        BACKGROUND_SKILLS, LOJA_CARVALHAL, MAGIAS_POR_CLASSE, ARMAS_DB, BONUS_RACA,
        gerar_loot_inimigo_comum, gerar_loot_bau, adicionar_ao_inventario
    )
    from combat_logic import processar_ataque_fisico, processar_ataque_objeto
    from mapa_engine import extrair_direcao
    from stats_manager import (
        get_or_create_estatisticas, iniciar_sessao, registrar_sala_visitada,
        registrar_combate_resultado, registrar_vitoria, registrar_derrota,
        registrar_teste, registrar_descanso_curto, calcular_taxa_sucesso,
        calcular_taxa_sucesso_testes, get_ultimas_partidas, calcular_tempo_jogo_formatado,
        get_rank_jogador, atualizar_estatistica
    )
    print("✅ Módulos carregados com sucesso!")
except Exception as e:
    print(f"❌ ERRO AO IMPORTAR MÓDULOS: {e}")
    import sys
    sys.exit(1)

class CriacaoPersonagem(StatesGroup):
    nome = State()
    sexo = State()
    raca = State()
    classe = State()
    background = State()
    atributos = State()

Base.metadata.create_all(bind=engine)

from sqlalchemy import text
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE jogadores ADD COLUMN IF NOT EXISTS hit_dice_max INTEGER DEFAULT 1"))
        conn.execute(text("ALTER TABLE jogadores ADD COLUMN IF NOT EXISTS hit_dice_atual INTEGER DEFAULT 1"))
    print("✅ Auto-migration: Colunas hit_dice verificadas/adicionadas.")
except Exception as e:
    print(f"⚠️ Aviso ao auto-migrar DB: {e}")

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(token=TOKEN)

dp = Dispatcher()
dp.include_router(menus_router)
dp.include_router(exploracao_router)

texto_introducao = (
    f"🎲 <b>A CIDADELA SEM SOL</b> 🎲\n\n"
    f"As nuvens cinzentas se acumulam sobre a Vila de Carvalhal..."
)

texto_manual = (
    f"📜 <b>O GUIA DO AVENTUREIRO</b> 📜\n"
    f"<i>Lê com atenção antes de dares o primeiro passo!</i>\n\n"
    f"🗣️ <b>LIBERDADE TOTAL</b>\n"
    f"Escreve o que desejas fazer como se estivesses numa mesa de RPG real.\n"
    f"• Ex: <i>\"Vou para a porta norte furtivamente\", \"Bebo a poção\", \"Tento arrombar o baú\"</i>.\n\n"
    f"⚔️ <b>COMBATE E ARMAMENTO</b>\n"
    f"Basta dizeres que vais atacar. O sistema usa a tua arma equipada.\n"
    f"Usa o comando <code>/equipar Nome da Arma ou Armadura</code> para trocar de equipamento do teu inventário. O bot ajustará a tua Defesa (CA) ou Dano dinamicamente!\n\n"
    f"🏃 <b>FUGA E SOBREVIVÊNCIA</b>\n"
    f"Se a morte for iminente, podes ditar <i>\"Fugir\"</i> ou <i>\"Recuar\"</i>. Terás de passar num teste de Destreza. Se falhares, levas dano nas costas. Se passares, voltas vivo para a sala anterior.\n\n"
    f"🎲 <b>TESTES DE HABILIDADE</b>\n"
    f"Podes pedir para rolar (Ex: <i>\"Faço um teste de Percepção\"</i>). Se tiveres essa perícia no teu Background, a tua Proficiência será somada automaticamente!\n\n"
    f"🛠️ <b>COMANDOS DO SISTEMA</b>\n"
    f"👤 /ficha - Ver HP, Ouro, XP, Atributos, Perícias e Equipamento\n"
    f"⚔️ /equipar - Escolher arma ou armadura ativa\n"
    f"🎒 /inventario - Ver a tua mochila e arma\n"
    f"🛒 /loja - Comprar itens (Apenas na Vila)\n"
    f"⚖️ /vender - Vender loot e equipamentos (Apenas na Vila)\n"
    f"📜 /missoes - Ver o teu diário de missões (NPCs)\n"
    f"🧘 /descansar - Recupera HP, Habilidades e cura Status\n"
    f"📊 /dashboard - Tuas estatísticas e o Ranking Global\n"
    f"🔄 /reset - Apagar personagem (Morte voluntária)\n\n"
    f"🤝 <b>SISTEMA DE GRUPO (PARTY)</b>\n"
    f"⚠️ <i>Lembrete: Não podes explorar as masmorras sem um grupo!</i>\n"
    f"👑 <b>/party criar</b> - Começa a tua própria saga e recebe um código.\n"
    f"🔗 <b>/party entrar [CÓDIGO]</b> - Junta-te aos teus amigos.\n\n"
    f"Boa sorte, aventureiro. A Cidadela não perdoa erros."
)

# ── Manipuladores do Guia do Aventureiro ──
@dp.message(Command("guia", "ajuda", "manual"))
async def guia_handler(message: types.Message):
    await message.answer(texto_manual, parse_mode="HTML")

@dp.callback_query(F.data == "abrir_guia")
async def callback_abrir_guia(callback: types.CallbackQuery):
    await callback.message.answer(texto_manual, parse_mode="HTML")
    await callback.answer()

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == str(message.from_user.id)).first()
        if not jogador:
            await message.answer("🎲 Bem-vindo! Use /criar para começar.", reply_markup=ReplyKeyboardRemove())
            return
        
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first() if jogador.party_id else None
        if campanha:
            sala_atual = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()
            if sala_atual:
                if not sala_atual.imagem_url:
                    msg_temp = await message.answer("🎨 <i>O Mestre está a visualizar o local...</i>", parse_mode="HTML")
                    img_url = await gerar_imagem_sala(sala_atual.nome_sala, sala_atual.descricao_visual)
                    if img_url:
                        sala_atual.imagem_url = img_url
                    await msg_temp.delete()

                if sala_atual.imagem_url:
                    await message.answer_photo(photo=sala_atual.imagem_url)

                msg = (f"{texto_introducao}\n\n📍 <b>{sala_atual.nome_sala}</b>\n{sala_atual.descricao_visual}\n"
                       f"{texto_saidas(sala_atual)}\n{resumo_status(jogador)}")
                await message.answer(msg, parse_mode="HTML", reply_markup=teclado_saidas(sala_atual))

                # Botão inline do guia
                teclado_inline = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📜 Ler Guia do Aventureiro", callback_data="abrir_guia")]
                ])
                await message.answer("👇 <i>Primeira vez por aqui? Lê as regras:</i>", parse_mode="HTML", reply_markup=teclado_inline)
            else:
                await message.answer("⚠️ Sala não encontrada no banco. Use /reset.")
        else:
             await message.answer("⚠️ Ainda não estás numa Party. Usa <code>/party criar</code> ou <code>/party entrar [CÓDIGO]</code> para começares a aventura.", parse_mode="HTML")

@dp.message(Command("falar", "chat"))
async def falar_handler(message: types.Message):
    texto_mensagem = message.text.split(maxsplit=1)
    
    if len(texto_mensagem) < 2:
        return await message.answer("⚠️ Uso correto: <code>/falar [sua mensagem]</code>", parse_mode="HTML")
    
    mensagem_off = texto_mensagem[1]
    user_id = str(message.from_user.id)

    with get_db_session() as db:
        jogador_atual = db.query(Jogador).filter(Jogador.telefone == user_id).first()
        
        if not jogador_atual or not jogador_atual.party_id:
            return await message.answer("⚠️ Precisas de estar numa Party para usar o chat!")

        membros_party = db.query(Jogador).filter(Jogador.party_id == jogador_atual.party_id).all()
        
        if len(membros_party) <= 1:
            return await message.answer("🗣️ <i>Estás a falar sozinho... Não há mais ninguém na tua Party.</i>", parse_mode="HTML")

        texto_broadcast = f"💬 <b>[Off] {jogador_atual.nome}:</b> \"{mensagem_off}\""

        for membro in membros_party:
            if membro.telefone != user_id: 
                try:
                    await bot.send_message(chat_id=membro.telefone, text=texto_broadcast, parse_mode="HTML")
                except Exception as e:
                    print(f"Erro ao enviar chat para {membro.telefone}: {e}")
        
        await message.answer("<i>Mensagem enviada à party.</i>", parse_mode="HTML")

@dp.message(Command("party"))
async def party_handler(message: types.Message):
    args = message.text.split()
    user_id = str(message.from_user.id)
    
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == user_id).first()
        if not jogador: return await message.answer("⚠️ Cria um personagem primeiro com /criar.")
        
        if len(args) < 2:
            return await message.answer("🤝 <b>SISTEMA DE LOBBY</b>\n\nCriar um grupo: <code>/party criar</code>\nEntrar num grupo: <code>/party entrar [CÓDIGO]</code>", parse_mode="HTML")
        
        acao = args[1].lower()
        
        if acao == "criar":
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            codigo_party = f"PTY-{codigo}"
            
            jogador.party_id = codigo_party
            nova_campanha = Campanha(
                party_id=codigo_party,
                host_id=user_id,
                cena_atual="carvalhal",
                estado_salas={},
                momento="inicio",
                tensao=0,
                turno_atual=1
            )
            db.add(nova_campanha)
            await message.answer(f"👑 <b>Party Criada!</b>\nO teu código secreto é: <code>{codigo_party}</code>\n\nDá este código aos teus amigos para eles usarem <code>/party entrar {codigo_party}</code>.", parse_mode="HTML")
            
        elif acao == "entrar":
            if len(args) < 3: return await message.answer("⚠️ Qual é o código? Ex: <code>/party entrar PTY-A1B2C</code>", parse_mode="HTML")
            codigo_alvo = args[2].upper()
            
            campanha = db.query(Campanha).filter(Campanha.party_id == codigo_alvo).first()
            if not campanha: return await message.answer("❌ Código de Party inválido ou não existe.")
            
            # --- NOVA CHECAGEM DE LIMITE DE JOGADORES ---
            membros_atuais = db.query(Jogador).filter(Jogador.party_id == codigo_alvo).count()
            if membros_atuais >= 5:
                return await message.answer("🚫 <b>A Taverna está cheia!</b> Esta party já atingiu o limite máximo de 5 jogadores.", parse_mode="HTML")
            # -------------------------------------------
            
            # ─── INÍCIO: SISTEMA DE NIVELAMENTO POR PARTY ───
            membros_existentes = db.query(Jogador).filter(Jogador.party_id == codigo_alvo, Jogador.telefone != user_id).all()
            
            if membros_existentes:
                xp_medio = sum([m.xp for m in membros_existentes]) // len(membros_existentes)
                
                if xp_medio > jogador.xp:
                    jogador.xp = xp_medio
                    niveis_subidos = 0
                    
                    while jogador.xp >= XP_POR_NIVEL.get(jogador.nivel + 1, 999999):
                        jogador.nivel += 1
                        jogador.hp_maximo += HP_POR_CLASSE.get(jogador.classe, 8) + jogador.mod_con
                        jogador.hp_atual = jogador.hp_maximo
                        
                        jogador.slots_magia_max += 1 
                        jogador.slots_magia = jogador.slots_magia_max
                        
                        jogador.hit_dice_max = getattr(jogador, 'hit_dice_max', 1) + 1
                        jogador.hit_dice_atual = jogador.hit_dice_max

                        nova_proficiencia = 2 + ((jogador.nivel - 1) // 4)
                        if nova_proficiencia > jogador.proficiencia:
                            jogador.proficiencia = nova_proficiencia
                            jogador.modificador_ataque = jogador.mod_dano + jogador.proficiencia
                        
                        # Correção de escala do Monge ao subir de nível pelo nivelamento
                        if jogador.classe.lower() == "monge" and "Desarmado" in getattr(jogador, 'arma_equipada', ''):
                            if jogador.nivel >= 17: jogador.dano_dado = "1d10"
                            elif jogador.nivel >= 11: jogador.dano_dado = "1d8"
                            elif jogador.nivel >= 5: jogador.dano_dado = "1d6"
                            else: jogador.dano_dado = "1d4"
                        
                        niveis_subidos += 1
                    
                    if niveis_subidos > 0:
                        await message.answer(f"📈 <b>TAVERNA MERCENÁRIA (Nivelamento)</b>\nO grupo contratou-te porque tens a mesma experiência que eles. \nEntraste com <b>{xp_medio} XP</b> e subiste para o <b>Nível {jogador.nivel}</b>!\n❤️ O teu HP Máximo escalou para {jogador.hp_maximo}.", parse_mode="HTML")
            # ─── FIM: SISTEMA DE NIVELAMENTO POR PARTY ───

            jogador.party_id = codigo_alvo
            jogador.cena_atual = campanha.cena_atual
            
            membros = db.query(Jogador).filter(Jogador.party_id == codigo_alvo).all()
            for membro in membros:
                if membro.telefone != user_id:
                    await bot.send_message(chat_id=membro.telefone, text=f"📯 <b>O experiente {jogador.classe} {jogador.nome} juntou-se à vossa Party!</b>", parse_mode="HTML")
            
            await message.answer(f"✅ <b>Entraste na Party {codigo_alvo}!</b>", parse_mode="HTML")
            
            intro = texto_introducao
            try:
                from models import Aventura
                aventura_id = getattr(campanha, 'aventura_ativa', 'cidadela')
                aventura = db.query(Aventura).filter(Aventura.id == aventura_id).first()
                if aventura and aventura.prologo:
                    intro = aventura.prologo
            except Exception:
                pass
            
            await message.answer(f"📖 {intro}", parse_mode="HTML")
            await asyncio.sleep(2)
            
            sala_party = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()
            if sala_party:
                if not sala_party.imagem_url:
                    msg_temp = await message.answer("🎨 <i>O Mestre está a visualizar o local...</i>", parse_mode="HTML")
                    img_url = await gerar_imagem_sala(sala_party.nome_sala, sala_party.descricao_visual)
                    if img_url:
                        sala_party.imagem_url = img_url
                    await msg_temp.delete()

                if sala_party.imagem_url:
                    await message.answer_photo(photo=sala_party.imagem_url)

                await message.answer(
                    f"📍 <b>{sala_party.nome_sala}</b>\n{sala_party.descricao_visual}\n"
                    f"{texto_saidas(sala_party)}\n{resumo_status(jogador)}",
                    parse_mode="HTML",
                    reply_markup=teclado_saidas(sala_party)
                )

@dp.message(Command("codigo", "party_id", "convite"))
async def codigo_handler(message: types.Message):
    user_id = str(message.from_user.id)
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == user_id).first()
        
        if not jogador or not jogador.party_id:
            return await message.answer("⚠️ Ainda não estás num grupo. Usa <code>/party criar</code> primeiro.", parse_mode="HTML")
            
        teclado_inline = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Compartilhar Código", switch_inline_query=f"Junta-te à minha party no RPG! Código: {jogador.party_id}")]
        ])
        
        await message.answer(
            f"👑 <b>O TEU CÓDIGO DE GRUPO</b> 👑\n\n"
            f"<code>{jogador.party_id}</code>\n\n"
            f"<i>Passa este código aos teus aliados. Eles devem usar <code>/party entrar {jogador.party_id}</code> para se juntarem a ti.</i>", 
            parse_mode="HTML",
            reply_markup=teclado_inline
        )

@dp.message(Command("r", "roll"))
async def rolar_dados_handler(message: types.Message):
    user_id = str(message.from_user.id)
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == user_id).first()
        if not jogador or not jogador.party_id:
            await message.answer("⚠️ Precisas de estar numa party para rolar dados.")
            return

        arg = message.text.replace("/r", "").replace("/roll", "").strip()
        if not arg:
            await message.answer("🎲 Uso: `/r 2d6+3` ou `/r 1d20`", parse_mode="HTML")
            return

        match = re.match(r'(\d+)d(\d+)(?:([+-])(\d+))?', arg.lower().replace(' ', ''))
        if not match:
            await message.answer("❌ Formato inválido. Exemplo: `/r 2d6+3`")
            return

        qtd = int(match.group(1))
        faces = int(match.group(2))
        sinal = match.group(3)
        bonus = int(match.group(4)) if match.group(4) else 0

        # BLINDAGEM DE ROLAGEM AQUI
        if not (1 <= qtd <= 100) or not (2 <= faces <= 1000):
            await message.answer("⚠️ Use no mínimo 1 dado e máximo 100 dados. As faces devem ser entre 2 e 1000.")
            return

        rolagens = [random.randint(1, faces) for _ in range(qtd)]
        total = sum(rolagens)
        if sinal == '+':
            total += bonus
        elif sinal == '-':
            total -= bonus

        detalhes = ", ".join(map(str, rolagens))
        texto = f"🎲 <b>{jogador.nome}</b> rolou {arg}\n📊 Rolagens: [{detalhes}]"
        if sinal:
            texto += f"\n✨ Total: {total} (com {sinal}{bonus})"
        else:
            texto += f"\n✨ Total: {total}"

        membros = db.query(Jogador).filter(Jogador.party_id == jogador.party_id).all()
        for m in membros:
            try:
                await bot.send_message(chat_id=m.telefone, text=texto, parse_mode="HTML")
            except Exception:
                pass


@dp.message(Command("descansar", "descanso"))
async def descansar_handler(message: types.Message):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == str(message.from_user.id)).first()
        if not jogador: return await message.answer("⚠️ Não tens nenhum personagem ativo. Usa /criar.")
        
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first() if getattr(jogador, 'party_id', None) else None
        
        if campanha and campanha.cena_atual != "carvalhal":
            # Descanso Curto usando Hit Dice
            if jogador.hit_dice_atual > 0:
                jogador.hit_dice_atual -= 1
                cura = max(1, (jogador.hp_maximo // 4) + jogador.mod_con)
                jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
                
                # O Guerreiro recupera as suas habilidades com Descansos Curtos
                if jogador.classe.lower() == "guerreiro":
                    jogador.slots_magia = min(jogador.slots_magia_max, jogador.slots_magia + 1)
                
                await message.answer(f"🏕️ <b>Descanso Curto:</b> O teu grupo montou acampamento rapidamente nas trevas.\n❤️ Curaste {cura} HP.\n🎲 <b>Hit Dice restantes:</b> {jogador.hit_dice_atual}/{jogador.hit_dice_max}\n{resumo_status(jogador)}", parse_mode="HTML")
            else:
                await message.answer("⚠️ <b>Exausto!</b> Não tens mais Hit Dice (Dados de Vida) para gastar! Precisas de regressar à Vila de Carvalhal para um Descanso Longo.", parse_mode="HTML")
        else:
            # Descanso Longo Seguro na Vila
            jogador.hp_atual = jogador.hp_maximo
            jogador.slots_magia = jogador.slots_magia_max
            jogador.hit_dice_atual = getattr(jogador, 'hit_dice_max', 1)
            jogador.status_efeitos = []
            await message.answer(f"🛌 <b>Descanso Longo em Carvalhal.</b>\nEstás quente e seguro. O teu HP, Magia, Habilidades e Hit Dice foram totalmente restaurados. Quaisquer condições foram curadas.\n{resumo_status(jogador)}", parse_mode="HTML")

@dp.message(Command("dashboard", "stats", "estatisticas"))
async def dashboard_handler(message: types.Message):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == str(message.from_user.id)).first()
        if not jogador: return await message.answer("⚠️ Use /criar para começar.")
        stats = get_or_create_estatisticas(db, str(message.from_user.id))
        rank = get_rank_jogador(db, str(message.from_user.id))
        ultimas_partidas = get_ultimas_partidas(db, str(message.from_user.id), limite=3)
        taxa_acerto = calcular_taxa_sucesso(stats)
        taxa_testes = calcular_taxa_sucesso_testes(stats)
        total_ataques = stats.total_ataques_acertados + stats.total_ataques_errados
        progresso = min(100, int(((jogador.xp - XP_POR_NIVEL.get(jogador.nivel, 0)) / (XP_POR_NIVEL.get(jogador.nivel + 1, 355000) - XP_POR_NIVEL.get(jogador.nivel, 0))) * 100)) if (XP_POR_NIVEL.get(jogador.nivel + 1, 355000) - XP_POR_NIVEL.get(jogador.nivel, 0)) > 0 else 100
        barras = int(progresso / 10)
        barra_progresso = "█" * barras + "░" * (10 - barras)
        texto = (f"📊 <b>DASHBOARD DE {jogador.nome.upper()}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                 f"📈 <b>PROGRESSO</b>\nNível: {jogador.nivel}\nXP: {jogador.xp} [{barra_progresso}] {progresso}%\nOuro: {jogador.gold} PO\n\n"
                 f"🏆 <b>RANKING</b>\nPosição: #{rank['posicao']} de {rank['total_jogadores']}\n\n"
                 f"⚔️ <b>ESTATÍSTICAS</b>\nKills: {stats.inimigos_derrotados}\nAtaques: {stats.total_ataques_acertados}/{total_ataques} ({taxa_acerto:.1f}%)\nCríticos: {stats.criticos_acertados} | Dano: {stats.danos_causados_total}\n\n")
        if ultimas_partidas:
            texto += "📜 <b>HISTÓRICO</b>\n" + "".join([f"{'🏆' if p.resultado=='vitoria' else '💀'} {p.resultado.title()} - {p.inimigos_derrotados} kills\n" for p in ultimas_partidas])
        await message.answer(texto, parse_mode="HTML")

@dp.message(Command("reset"))
async def reset_handler(message: types.Message):
    teclado_confirmacao = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Sim, apagar tudo", callback_data="confirmar_reset"),
            InlineKeyboardButton(text="❌ Não, mudei de ideias", callback_data="cancelar_reset")
        ]
    ])
    await message.answer("⚠️ <b>ATENÇÃO!</b>\nIsto apagará <b>PERMANENTEMENTE</b> o teu personagem, inventário, missões e estatísticas da base de dados.\n\nTens a certeza absoluta?", parse_mode="HTML", reply_markup=teclado_confirmacao)

@dp.callback_query(F.data == "confirmar_reset")
async def callback_confirmar_reset(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    with get_db_session() as db:
        db.query(Jogador).filter(Jogador.telefone == user_id).delete()
        db.query(Campanha).filter(Campanha.host_id == user_id).delete()
        db.query(EstatisticasJogador).filter(EstatisticasJogador.jogador_telefone == user_id).delete()
        db.query(HistoricoPartida).filter(HistoricoPartida.jogador_telefone == user_id).delete()
        db.query(Missao).filter(Missao.jogador_telefone == user_id).delete()
    
    await bot.send_message(chat_id=user_id, text="🌩️ <b>Dados e Estatísticas resetados.</b>\nA tua lenda chegou ao fim. Usa /criar para recomeçar.", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await callback.message.delete()
    await callback.answer()

@dp.callback_query(F.data == "cancelar_reset")
async def callback_cancelar_reset(callback: types.CallbackQuery):
    await callback.message.edit_text("🛡️ <b>Reset cancelado.</b>\nO teu herói ainda tem muitas batalhas para travar!", parse_mode="HTML")
    await callback.answer()

@dp.message(Command("criar"))
async def iniciar_criacao(message: types.Message, state: FSMContext):
    await message.answer("⚔️ Qual será o <b>nome</b> do herói?", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await state.set_state(CriacaoPersonagem.nome)

@dp.message(CriacaoPersonagem.nome)
async def processar_nome(message: types.Message, state: FSMContext):
    await state.update_data(nome=message.text)
    # Criar um teclado simples para o sexo
    teclado_sexo = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Masculino"), KeyboardButton(text="Feminino")],
            [KeyboardButton(text="Não Binário")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Qual é o <b>sexo/gênero</b> do seu herói?", reply_markup=teclado_sexo, parse_mode="HTML")
    await state.set_state(CriacaoPersonagem.sexo)

@dp.message(CriacaoPersonagem.sexo)
async def processar_sexo(message: types.Message, state: FSMContext):
    await state.update_data(sexo=message.text)
    await message.answer("Escolha sua <b>Raça</b>:", reply_markup=menu_racas(), parse_mode="HTML")
    await state.set_state(CriacaoPersonagem.raca)

@dp.message(CriacaoPersonagem.raca)
async def processar_raca(message: types.Message, state: FSMContext):
    await state.update_data(raca=message.text)
    await message.answer("Escolha sua <b>Classe</b>:", reply_markup=menu_classes(), parse_mode="HTML")
    await state.set_state(CriacaoPersonagem.classe)

@dp.message(CriacaoPersonagem.classe)
async def processar_classe(message: types.Message, state: FSMContext):
    await state.update_data(classe=message.text)
    await message.answer("Escolha seu <b>Background</b>:", reply_markup=menu_backgrounds(), parse_mode="HTML")
    await state.set_state(CriacaoPersonagem.background)

@dp.message(CriacaoPersonagem.background)
async def processar_background(message: types.Message, state: FSMContext):
    await state.update_data(background=message.text)
    rolagens = sorted([rolar_atributo_4d6() for _ in range(6)], reverse=True)
    rolagens_texto = ", ".join(map(str, rolagens))
    exemplo = f"{rolagens[0]} {rolagens[1]} {rolagens[2]} {rolagens[3]} {rolagens[4]} {rolagens[5]}"
    texto_instrucao = (f"🎲 <b>Seus Dados:</b> {rolagens_texto}\n\n"
                       f"Distribua esses valores para formar o seu herói! Digite os 6 números na ordem abaixo separados por espaços.\n\n"
                       f"<b>Ordem obrigatória:</b>\nSTR | DEX | CON | INT | WIS | CHA\n\n📝 <b>Exemplo:</b> <code>{exemplo}</code>")
    await message.answer(texto_instrucao, parse_mode="HTML")
    await state.set_state(CriacaoPersonagem.atributos)

@dp.message(CriacaoPersonagem.atributos)
async def processar_atributos(message: types.Message, state: FSMContext):
    try:
        partes = message.text.replace(",", " ").split()
        if len(partes) != 6: 
            return await message.answer("❌ Por favor, envie exatamente 6 números separados por espaço. (Exemplo: 15 14 13 12 10 8)")
        val = []
        for v in partes:
            if not v.strip().isdigit(): 
                return await message.answer("❌ Valores inválidos! Escreve apenas números. (Exemplo: 15 14 13 12 10 8)")
            val.append(int(v))

        user_data = await state.get_data()
        
        raca_escolhida = user_data.get('raca', 'Humano')
        bonus_raca = BONUS_RACA.get(raca_escolhida, [0, 0, 0, 0, 0, 0])
        val = [val[i] + bonus_raca[i] for i in range(6)]
        
        mods = [calcular_modificador(v) for v in val]
        classe = user_data['classe']
        hp_base = HP_POR_CLASSE.get(classe, 8) 
        inv_lista = INVENTARIO_POR_CLASSE.get(classe, ["Adaga", "Tochas", "Rações"])
        ca_inicial = 10 + mods[1] 
        if classe in ["Guerreiro", "Paladino"]: ca_inicial = 18
        elif classe in ["Patrulheiro", "Ladino", "Bárbaro"]: ca_inicial = 11 + mods[1] 
        elif classe in ["Clérigo"]: ca_inicial = 18

        slots_iniciais = 2 
        
        user_id = str(message.from_user.id)
        arma_inicial = next((item for item in inv_lista if any(a.lower() in item.lower() for a in ARMAS_DB.keys())), "Desarmado")
        armadura_inicial = next((item for item in inv_lista if any(x in item for x in ["Armadura", "Cota", "Peitoral"])), "Trajes Comuns")
        if any("Escudo" in i for i in inv_lista): armadura_inicial += " & Escudo"

        dados_jogador = {
            "nome": user_data['nome'], "raca": raca_escolhida, "classe": classe, "background": user_data['background'],
            "sexo": user_data.get('sexo', 'Desconhecido'),
            "hp_maximo": hp_base + mods[2], "hp_atual": hp_base + mods[2],
            "str_val": val[0], "dex_val": val[1], "con_val": val[2], "int_val": val[3], "wis_val": val[4], "cha_val": val[5],
            "mod_str": mods[0], "mod_dex": mods[1], "mod_con": mods[2], "mod_int": mods[3], "mod_wis": mods[4], "mod_cha": mods[5],
            "modificador_ataque": (mods[1] + 2 if classe in ["Ladino", "Bardo", "Monge", "Patrulheiro"] else mods[0] + 2),
            "modificador_defesa": ca_inicial, "proficiencia": 2, "gold": 15, "inventario": inv_lista,
            "arma_equipada": arma_inicial, "armadura_equipada": armadura_inicial,
            "slots_magia": slots_iniciais, "slots_magia_max": slots_iniciais,
            "dano_dado": ("1d12" if classe == "Bárbaro" else "1d10" if classe in ["Guerreiro", "Paladino"] else "1d8" if classe in ["Patrulheiro", "Ladino", "Clérigo", "Bardo", "Monge"] else "1d6"),
            "mod_dano": (mods[1] if classe in ["Ladino", "Bardo", "Monge", "Patrulheiro"] else mods[0]),
            "status_efeitos": [],
            "hit_dice_max": 1, "hit_dice_atual": 1,
            "descanso_curto_disponivel": True, "nivel": 1, "xp": 0,
            "cena_atual": "carvalhal", "cena_anterior": None
        }

        with get_db_session() as db:
            jogador = db.query(Jogador).filter(Jogador.telefone == user_id).first()
            if jogador:
                for key, value in dados_jogador.items(): setattr(jogador, key, value)
            else:
                novo_jogador = Jogador(telefone=user_id, **dados_jogador)
                db.add(novo_jogador)
                jogador = novo_jogador

            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            codigo_party = f"PTY-{codigo}"
            
            jogador.party_id = codigo_party
            
            nova_campanha = Campanha(
                party_id=codigo_party,
                host_id=user_id,
                cena_atual="carvalhal",
                estado_salas={},
                momento="inicio",
                tensao=0,
                turno_atual=1
            )
            db.add(nova_campanha)

            iniciar_sessao(db, user_id)
            registrar_sala_visitada(db, user_id, "carvalhal")
            sala = db.query(Cena).filter(Cena.cod_sala == "carvalhal").first()
            await state.clear()
            
            dica_classe = ""
            _cls = classe.lower()
            
            if _cls == "bárbaro":
                dica_classe = "\n\n😡 <b>DICA:</b> Tu és um Bárbaro! Digita que entras em 'Fúria' no combate para dar bônus de dano e receber apenas metade do dano dos inimigos! Gasta Usos."
            elif _cls == "paladino":
                dica_classe = "\n\n✨ <b>DICA:</b> Tu és um Paladino! Digita 'Destruição Divina' (Smite) ao atacar para gastar Uso e dar dano radiante extra."
            elif _cls == "ladino":
                dica_classe = "\n\n🗡️ <b>DICA:</b> Tu és um Ladino! Ataca 'furtivamente' ou 'pelas costas' para causar Ataque Furtivo (dano extra)."
            elif _cls == "druida":
                dica_classe = "\n\n🐾 <b>DICA:</b> Tu és um Druida! Digita que usas 'Forma Selvagem' (ou viras urso/lobo) para gastar Uso, curar HP e atacar com garras (+2d6)."
            elif _cls == "monge":
                dica_classe = "\n\n🥋 <b>DICA:</b> Tu és um Monge! Usa <code>/equipar Desarmado</code> para lutar com Artes Marciais (usa Destreza e o dano escala com seu nível)."
            elif _cls == "guerreiro":
                dica_classe = "\n\n⚔️ <b>DICA:</b> Tu és um Guerreiro! Gasta Usos com 'Retomar o Fôlego' para curar HP, ou 'Surto de Ação' para atacar duas vezes!"
            elif _cls == "patrulheiro":
                dica_classe = "\n\n🏹 <b>DICA:</b> Tu és um Patrulheiro! Usa 'Marca do Caçador' num inimigo para que todos os teus ataques contra ele deem +1d6 de dano extra."
            elif _cls == "clérigo":
                dica_classe = "\n\n✝️ <b>DICA:</b> Tu és um Clérigo! Usa 'Canalizar Divindade' para dar dano radiante nos monstros e curar-te. Gasta Usos de Magia."
            elif _cls == "mago":
                dica_classe = "\n\n📖 <b>DICA:</b> Tu és um Mago! Se fores atacado, dita 'Escudo Arcano' para gastar um Slot e aumentar a tua CA em +5 instantaneamente."
            elif _cls == "bruxo":
                dica_classe = "\n\n👁️ <b>DICA:</b> Tu és um Bruxo! Usa a tua 'Maldição' (Hex) para que todos os teus ataques causem +1d6 de dano necrótico extra."
            elif _cls == "bardo":
                dica_classe = "\n\n🎸 <b>DICA:</b> Tu és um Bardo! Insulta os teus inimigos com 'Zombaria Viciosa' para que o próximo ataque deles tenha desvantagem."
            elif _cls == "feiticeiro":
                dica_classe = "\n\n🔮 <b>DICA:</b> Tu és um Feiticeiro! Usa 'Metamagia' para duplicar o teu feitiço e atingir os inimigos com o dobro da força."
            elif _cls == "artífice":
                dica_classe = "\n\n⚙️ <b>DICA:</b> Tu és um Artífice! Usa as tuas invenções e infusões mágicas para fortalecer armas e armaduras. Dita 'Retornar à Vida' para curar ou 'Explosão Arcana' para atacar à distância."
            
            if sala:
                if not sala.imagem_url:
                    msg_temp = await message.answer("🎨 <i>O Mestre está a visualizar o local...</i>", parse_mode="HTML")
                    img_url = await gerar_imagem_sala(sala.nome_sala, sala.descricao_visual)
                    if img_url:
                        sala.imagem_url = img_url
                    await msg_temp.delete()
                    
                if sala.imagem_url:
                    await message.answer_photo(photo=sala.imagem_url)

                await message.answer(f"✨ <b>{user_data['nome']}</b> despertou.{dica_classe}\n\n{texto_introducao}\n\n📍 <b>{sala.nome_sala}</b>\n{sala.descricao_visual}\n{texto_saidas(sala)}\n{resumo_status(jogador)}", parse_mode="HTML", reply_markup=teclado_saidas(sala))

        teclado_inline = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📜 Ler Guia do Aventureiro", callback_data="abrir_guia")]
        ])
        await message.answer(f"👇 <i>Antes de partir, que tal conferir as regras?</i>\n\n👑 <b>O teu código de Party é:</b> <code>{codigo_party}</code>\n<i>(Passa este código aos teus amigos se quiseres que eles entrem na tua sessão usando /party entrar)</i>", parse_mode="HTML", reply_markup=teclado_inline)

    except Exception as e:
        logging.error(f"Erro na criação de personagem: {e}", exc_info=True)
        await message.answer("❌ Ocorreu um erro ao criar o personagem. Tenta novamente.")

@dp.error()
async def global_error_handler(event: ErrorEvent):
    logging.error("🚨 ERRO CRÍTICO CAPTURADO PELO HANDLER GLOBAL 🚨")
    logging.error(f"Exceção: {event.exception}")
    logging.error(traceback.format_exc())
    
    msg_erro = "🛠️ <b>Anomalia Mágica Detectada!</b>\n<i>Os tecidos da realidade (banco de dados) oscilaram. Os Monges Arquivistas já foram notificados para consertar este feitiço. Tenta fazer a tua ação novamente num minuto.</i>"

    try:
        if event.update.message:
            await event.update.message.answer(msg_erro, parse_mode="HTML")
        elif event.update.callback_query:
            await event.update.callback_query.message.answer(msg_erro, parse_mode="HTML")
    except Exception as fallback_error:
        logging.error(f"Falha ao enviar mensagem de erro para o usuário: {fallback_error}")

async def main():
    asyncio.create_task(lock_garbage_collector())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())