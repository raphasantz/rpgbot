"""
pygame_ui.py — Janela desktop (CustomTkinter) estilo ZMUD/Nethack.

PROTÓTIPO: reusa combat_logic (motor de combate) e o db_loader (JSONs).
Sem SQL, sem Telegram, sem IA. Pura diversão local.

RODAR:
    pip install customtkinter pillow
    python pygame_ui.py             # modo padrão: tenta banco, fallback offline
    python pygame_ui.py --offline   # modo offline forçado (sem banco, sem .env)
    python pygame_ui.py --reset     # apaga save local e cria personagem novo

VIBE:
    Janela única, layout fixo, vibe roguelike (Nethack / DF).
    Imagem da sala em cima, log narrativo, botões contextuais, status bar.
"""
from __future__ import annotations

# For\u00e7a UTF-8 no console (evita crash de emoji no .exe Windows)
import sys
import io
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

import asyncio
import json
import os
import random
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional

# DB wrapper (usa os mesmos models/database do Telegram)
import db_desktop

# Metadados do App
APP_NOME = "Mesanerd"
APP_VERSAO = "1.0.0"
APP_DESCRICAO = "RPG Bot Desktop — Cidadela Sem Sol + Mina Perdida de Phandelver"
APP_AUTOR = "Rafael"
APP_REPO_URL = "https://github.com/raphasantz/rpgbot"
APP_UPDATE_URL = f"{APP_REPO_URL}/releases/latest/download/version.json"
APP_DOWNLOAD_URL = f"{APP_REPO_URL}/releases/latest"

# Motor do jogo (reusa do bot Telegram, sem modificação)
from combat_logic import processar_ataque_fisico, processar_ataque_objeto
from ui_utils import LOJA_CARVALHAL, calcular_ca_final, calcular_modificadores_ataque
from db_loader import (
    get_cena, get_inimigo, get_npc, get_npc_da_cena,
    get_encontros_vivos, ENCONTROS_POR_SALA, CENAS, INIMIGOS, NPCS,
)
from imagens_config import url_para, CACHE_DIR

# =============================================================================
# FLAGS DE LINHA DE COMANDO
# =============================================================================
MODO_OFFLINE = "--offline" in sys.argv
MODO_RESET = "--reset" in sys.argv

if MODO_OFFLINE:
    print("[pygame_ui] [OFFLINE] Modo OFFLINE forcado (sem banco, sem .env)")
if MODO_RESET:
    print("[pygame_ui] [RESET] Flag --reset ativa (vai apagar save local)")

# CustomTkinter + PIL
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont


# =============================================================================
# MOCK DO JOGADOR (substitui o Jogador SQL no protótipo)
# =============================================================================
# CARREGAR JOGADOR ATIVO DO BANCO (usa db_desktop - mesmo esquema do Telegram)
# =============================================================================
def carregar_jogador_ativo() -> Optional[dict]:
    """
    Tenta carregar o jogador ativo:
    1. PostgreSQL real (se --offline NÃO foi passado, .env existe, E --reset NÃO foi passado)
    2. Save JSON local (saves/jogador_atual.json)
    3. None (vai usar o demo Sir Lancelot)

    Retorna dict com {"campanha": ..., "jogador": ...} ou None.
    """
    # Se --reset foi passado, ignora banco e save local, força demo
    if MODO_RESET:
        print("[pygame_ui] [RESET] Ignorando banco e save, forçando demo Sir Lancelot")
        return None

    # Tenta carregar via db_desktop (PostgreSQL + fallback local)
    telefone = None
    if not MODO_OFFLINE:
        # Tenta achar jogador salvo local pra pegar o telefone
        save_atual = Path(__file__).parent / "saves" / "jogador_atual.json"
        if save_atual.exists():
            try:
                with open(save_atual, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                telefone = dados.get("telefone")
            except Exception:
                pass

    if telefone:
        dados = db_desktop.carregar_jogador_completo(telefone=telefone)
        if dados:
            fonte = "banco real" if not MODO_OFFLINE else "save local (offline)"
            print(f"[pygame_ui] ✅ {dados['jogador'].get('nome', '?')} carregado de {fonte}")
            return dados

    # Fallback: save local genérico
    save_path = Path(__file__).parent / "saves" / "jogador_atual.json"
    if save_path.exists():
        try:
            with open(save_path, "r", encoding="utf-8") as f:
                dados_jogador = json.load(f)
            return {
                "campanha": {
                    "host_id": dados_jogador.get("telefone", "local"),
                    "cena_atual": dados_jogador.get("cena_atual", "carvalhal"),
                    "estado_salas": dados_jogador.get("estado_salas", {}),
                },
                "jogador": dados_jogador,
            }
        except Exception as e:
            print(f"[pygame_ui] ⚠️ Erro lendo save local: {e}")

    if MODO_OFFLINE:
        print("[pygame_ui] 🎮 Modo offline + sem save local → demo Sir Lancelot")
    else:
        print("[pygame_ui] ⚠️ Banco off, sem save local → demo Sir Lancelot")
    return None


# =============================================================================
class MockJogador:
    """Tem os mesmos campos que o Jogador do models.py. Duck typing.

    Pode receber dados crus de uma row do PostgreSQL (dict) ou usar defaults."""

    def __init__(self, dados_db: Optional[dict] = None, nome: str = "Aventureiro", classe: str = "Guerreiro"):
        # Defaults: sempre atribui nome/classe (mesmo sem dados_db)
        self.telefone = dados_db.get("telefone", "local-dev") if dados_db else "local-dev"
        self.party_id = dados_db.get("party_id") if dados_db else None
        self.party_id = self.party_id or "PTY-LOCAL"
        self.nome = dados_db.get("nome", nome) if dados_db else nome
        self.classe = dados_db.get("classe", classe) if dados_db else classe
        self.nivel = dados_db.get("nivel", 1) if dados_db else 1
        self.xp = 0

        # HP / Defesa
        self.hp_atual = dados_db.get("hp_atual", 14) if dados_db else 14
        self.hp_maximo = dados_db.get("hp_maximo", 14) if dados_db else 14
        self.modificador_defesa = dados_db.get("modificador_defesa", 16) if dados_db else 16
        self.modificador_ataque = dados_db.get("modificador_ataque", 4) if dados_db else 4

        # Atributos
        self.str_val = dados_db.get("str", 14) if dados_db else 14
        self.mod_str = dados_db.get("mod_str", 2) if dados_db else 2
        self.dex_val = dados_db.get("dex", 12) if dados_db else 12
        self.mod_dex = dados_db.get("mod_dex", 1) if dados_db else 1
        self.con_val = dados_db.get("con", 14) if dados_db else 14
        self.mod_con = dados_db.get("mod_con", 2) if dados_db else 2
        self.int_val = dados_db.get("int", 10) if dados_db else 10
        self.mod_int = dados_db.get("mod_int", 0) if dados_db else 0
        self.wis_val = dados_db.get("wis", 12) if dados_db else 12
        self.mod_wis = dados_db.get("mod_wis", 1) if dados_db else 1
        self.cha_val = dados_db.get("cha", 10) if dados_db else 10
        self.mod_cha = dados_db.get("mod_cha", 0) if dados_db else 0

        # Combate
        self.arma_equipada = dados_db.get("arma_equipada", "Espada Longa") if dados_db else "Espada Longa"
        self.armadura_equipada = dados_db.get("armadura_equipada", "Cota de Malha") if dados_db else "Cota de Malha"
        self.dano_dado = dados_db.get("dano_dado", "1d8") if dados_db else "1d8"
        self.mod_dano = dados_db.get("mod_dano", 2) if dados_db else 2
        self.proficiencia = dados_db.get("proficiencia", 2) if dados_db else 2

        # Inventário (pode vir como string JSON do banco ou lista do demo)
        if dados_db:
            inv_raw = dados_db.get("inventario", "[]")
            if isinstance(inv_raw, str):
                try:
                    self.inventario = json.loads(inv_raw)
                except (json.JSONDecodeError, TypeError):
                    self.inventario = []
            else:
                self.inventario = inv_raw or []
            self.gold = dados_db.get("gold", 0) or 0
        else:
            self.gold = 20
            self.inventario = ["Espada Longa", "Cota de Malha", "Poção de Cura"]

        # Status / recursos
        self.status_efeitos: list[str] = []
        self.slots_magia = dados_db.get("slots_magia", 0) if dados_db else 0
        self.slots_magia_max = dados_db.get("slots_magia_max", 0) if dados_db else 0
        self.hit_dice_atual = dados_db.get("hit_dice_atual", 1) if dados_db else 1
        self.hit_dice_max = dados_db.get("hit_dice_max", 1) if dados_db else 1
        # cena_atual: vem do banco se disponível, senão default
        self.cena_atual = dados_db.get("cena_atual", "taverna") if dados_db else "taverna"

    def __repr__(self):
        return f"<MockJogador {self.nome} HP={self.hp_atual}/{self.hp_maximo} CA={self.modificador_defesa}>"


# =============================================================================
# CACHE DE IMAGENS (1ª vez baixa, depois disco)
# =============================================================================
# =============================================================================
# TELA INICIAL — MENU PRINCIPAL
# =============================================================================
class MainMenu(ctk.CTkFrame):
    """Tela inicial do jogo: Novo Jogo, Carregar Jogo, Entrar na Partida, Configurações."""
    
    def __init__(self, master, on_novo_jogo, on_carregar_jogo, on_entrar_partida, on_config):
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        
        # Container centralizado
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Título
        ctk.CTkLabel(
            container, 
            text="🎲 MEZZARPG", 
            font=ctk.CTkFont(size=42, weight="bold"),
            text_color="#C9A84C"
        ).pack(pady=(0, 5))
        
        ctk.CTkLabel(
            container,
            text="Cidadela Sem Sol + Mina Perdida de Phandelver",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        ).pack(pady=(0, 10))
        
        # Status de conexão PostgreSQL
        from db_desktop import conexao_status_texto, TEM_POSTGRES
        status_texto = conexao_status_texto()
        status_cor = "#4CAF50" if "🟢" in status_texto else ("#FF9800" if "🟡" in status_texto else "#F44336")
        
        status_frame = ctk.CTkFrame(container, fg_color="transparent")
        status_frame.pack(pady=(0, 15))
        
        ctk.CTkLabel(
            status_frame,
            text="🗄️ Banco:",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(side="left", padx=(0, 5))
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text=status_texto,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=status_cor
        )
        self.status_label.pack(side="left")
        
        # Botão para testar conexão
        ctk.CTkButton(
            status_frame,
            text="🔄 Testar",
            width=70,
            height=24,
            font=ctk.CTkFont(size=10),
            command=self._atualizar_status_conexao
        ).pack(side="left", padx=(10, 0))
        
        # Botões principais
        btn_style = {
            "width": 320,
            "height": 56,
            "font": ctk.CTkFont(size=16, weight="bold"),
            "corner_radius": 12
        }
        
        ctk.CTkButton(
            container, text="🎮  NOVO JOGO",
            fg_color="#2E7D32", hover_color="#1B5E20",
            command=on_novo_jogo, **btn_style
        ).pack(pady=10)
        
        ctk.CTkButton(
            container, text="📂  CARREGAR JOGO",
            fg_color="#1565C0", hover_color="#0D47A1",
            command=on_carregar_jogo, **btn_style
        ).pack(pady=10)
        
        ctk.CTkButton(
            container, text="🔗  ENTRAR NA PARTIDA",
            fg_color="#6A1B9A", hover_color="#4A148C",
            command=on_entrar_partida, **btn_style
        ).pack(pady=10)
        
        ctk.CTkButton(
            container, text="⚙️  CONFIGURAÇÕES",
            fg_color="gray", hover_color="#424242",
            command=on_config, **btn_style
        ).pack(pady=10)
        
        # Versão no rodapé
        ctk.CTkLabel(
            container,
            text=f"v{APP_VERSAO}  •  {APP_AUTOR}",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        ).pack(pady=(30, 0))
    
    def _atualizar_status_conexao(self):
        """Atualiza o label de status da conexão PostgreSQL."""
        from db_desktop import conexao_status_texto, TEM_POSTGRES
        self.status_label.configure(text="🔄 Testando...")
        self.update()
        
        # Testa sincronamente (rápido) - mostra resultado direto
        from db_desktop import conexao_status_texto
        novo_status = conexao_status_texto()
        self._atualizar_label(novo_status)
    
    def _atualizar_label(self, novo_status: str):
        status_cor = "#4CAF50" if "🟢" in novo_status else ("#FF9800" if "🟡" in novo_status else "#F44336")
        self.status_label.configure(text=novo_status, text_color=status_cor)


# =============================================================================
# WIZARD DE CRIAÇÃO DE PERSONAGEM
# =============================================================================
class CharacterCreator(ctk.CTkToplevel):
    """Wizard modal fullscreen para criação de personagem em 6 passos."""
    
    STEPS = [
        ("nome", "🎭  Nome"),
        ("raca", "🧬  Raça"),
        ("classe", "⚔️  Classe"),
        ("background", "📜  Background"),
        ("atributos", "🎲  Atributos"),
        ("confirmar", "✅  Confirmar")
    ]
    
    RACAS = [
        ("Humano", "👤", "+1 em todos"),
        ("Elfo", "🧝", "+2 DEX"),
        ("Anão", "⛏️", "+2 CON"),
        ("Halfling", "🧝‍♀️", "+2 DEX"),
        ("Draconato", "🐉", "+2 FOR, +1 CHA"),
        ("Meio-Orc", "🏋️", "+2 FOR, +1 CON"),
        ("Meio-Elfo", "🧝‍♂️", "+2 CHA, +1 DEX/CON"),
        ("Tiefling", "😈", "+1 INT, +2 CHA"),
        ("Gnomo", "🔧", "+2 INT"),
    ]
    
    CLASSES = [
        ("Bárbaro", "😡", "1d12 HP, Fúria"),
        ("Bardo", "🎵", "1d8 HP, Magias, Inspiração"),
        ("Bruxo", "🟣", "1d8 HP, Pacto, Invocações"),
        ("Clérigo", "✨", "1d8 HP, Domínio, Magias divinas"),
        ("Druida", "🌿", "1d8 HP, Forma Selvagem, Magias"),
        ("Feiticeiro", "🔮", "1d6 HP, Metamagia, Origem"),
        ("Guerreiro", "⚔️", "1d10 HP, Estilo, Ação Extra"),
        ("Ladino", "🗡️", "1d8 HP, Ataque Furtivo, Astúcia"),
        ("Mago", "☄️", "1d6 HP, Livro de Magias, Recuperação Arcana"),
        ("Monge", "🥋", "1d8 HP, Artes Marciais, Ki"),
        ("Paladino", "⚔️✨", "1d10 HP, Juramento, Smite"),
        ("Patrulheiro", "🏹", "1d10 HP, Estilo, Marca do Caçador"),
        ("Artífice", "⚙️", "1d8 HP, Infusões, Ferramentas"),
    ]
    
    BACKGROUNDS = [
        ("Acólito", "⛪", "Religião, Intuição"),
        ("Criminoso", "🕵️", "Furtividade, Enganação"),
        ("Herói do Povo", "🛡️", "Adestrar Animais, Sobrevivência"),
        ("Nobre", "👑", "História, Persuasão"),
        ("Sábio", "📚", "Arcanismo, História"),
        ("Soldado", "⚔️", "Atletismo, Intimidação"),
        ("Forasteiro", "🏔️", "Atletismo, Sobrevivência"),
    ]
    
    def __init__(self, master, on_complete):
        super().__init__(master)
        self.on_complete = on_complete
        self.title("Criar Personagem")
        self.geometry("900x700")
        self.minsize(800, 600)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        # Dados do personagem
        self.data = {
            "nome": "", "sexo": "Masculino", "raca": "Humano",
            "classe": "Guerreiro", "background": "Soldado",
            "atributos": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
            "atributos_rolados": []
        }
        
        self.current_step = 0
        self._build_ui()
        self._show_step(0)
    
    def _build_ui(self):
        # Header com progresso
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=15)
        
        self.step_labels = []
        for i, (key, label) in enumerate(self.STEPS):
            lbl = ctk.CTkLabel(
                header, text=label,
                font=ctk.CTkFont(size=11, weight="bold" if i == 0 else "normal"),
                text_color="#C9A84C" if i == 0 else "gray"
            )
            lbl.pack(side="left", padx=5)
            self.step_labels.append(lbl)
            if i < len(self.STEPS) - 1:
                ctk.CTkLabel(header, text="→", text_color="gray").pack(side="left", padx=5)
        
        # Container dos steps
        self.steps_container = ctk.CTkFrame(self, fg_color="transparent")
        self.steps_container.pack(fill="both", expand=True, padx=30, pady=10)
        
        # Cria frames de cada step (inicialmente hidden)
        self.step_frames = {}
        for key, _ in self.STEPS:
            frame = ctk.CTkFrame(self.steps_container, fg_color="transparent")
            self.step_frames[key] = frame
            self._build_step_frame(key, frame)
        
        # Footer com botões navegação
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=15)
        
        self.btn_voltar = ctk.CTkButton(
            footer, text="← Voltar", width=120,
            command=self._prev_step, fg_color="gray"
        )
        self.btn_voltar.pack(side="left")
        
        self.btn_proximo = ctk.CTkButton(
            footer, text="Próximo →", width=120,
            fg_color="#2E7D32", hover_color="#1B5E20",
            command=self._next_step
        )
        self.btn_proximo.pack(side="right")
        
        self.btn_finalizar = ctk.CTkButton(
            footer, text="✅ Criar Personagem", width=180,
            fg_color="#C9A84C", hover_color="#A8883C", text_color="black",
            command=self._finish
        )
        self.btn_finalizar.pack(side="right", padx=10)
        self.btn_finalizar.pack_forget()  # só mostra no último step
    
    def _build_step_frame(self, key, frame):
        if key == "nome":
            self._build_step_nome(frame)
        elif key == "raca":
            self._build_step_raca(frame)
        elif key == "classe":
            self._build_step_classe(frame)
        elif key == "background":
            self._build_step_background(frame)
        elif key == "atributos":
            self._build_step_atributos(frame)
        elif key == "confirmar":
            self._build_step_confirmar(frame)
    
    def _build_step_nome(self, frame):
        ctk.CTkLabel(frame, text="Qual será o nome do herói?", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        ctk.CTkLabel(frame, text="Escolha um nome que ecoará pelos corredores da Cidadela.", text_color="gray").pack(pady=(0, 20))
        
        self.entry_nome = ctk.CTkEntry(frame, width=300, height=40, font=ctk.CTkFont(size=14), placeholder_text="Ex: Thorin, Elara, Kaelen...")
        self.entry_nome.pack(pady=10)
        self.entry_nome.bind("<Return>", lambda e: self._next_step())
        self.entry_nome.focus()
        
        self.lbl_nome_erro = ctk.CTkLabel(frame, text="", text_color="red", font=ctk.CTkFont(size=11))
        self.lbl_nome_erro.pack(pady=5)
    
    def _build_step_raca(self, frame):
        ctk.CTkLabel(frame, text="Escolha a raça do seu herói", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        ctk.CTkLabel(frame, text="Cada raça concede bônus de atributos únicos.", text_color="gray").pack(pady=(0, 20))
        
        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.raca_buttons = {}
        for i, (nome, emoji, bonus) in enumerate(self.RACAS):
            row = i // 3
            col = i % 3
            btn = ctk.CTkButton(
                grid, text=f"{emoji}\n{nome}\n{bonus}",
                width=220, height=110,
                font=ctk.CTkFont(size=13),
                fg_color="#1E1E1E", hover_color="#2E7D32",
                command=lambda n=nome: self._select_raca(n)
            )
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.raca_buttons[nome] = btn
        
        for c in range(3):
            grid.grid_columnconfigure(c, weight=1)
    
    def _build_step_classe(self, frame):
        ctk.CTkLabel(frame, text="Escolha a classe do seu herói", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        ctk.CTkLabel(frame, text="Define seu estilo de jogo, HP, magias e habilidades.", text_color="gray").pack(pady=(0, 20))
        
        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.classe_buttons = {}
        for i, (nome, emoji, desc) in enumerate(self.CLASSES):
            row = i // 4
            col = i % 4
            btn = ctk.CTkButton(
                grid, text=f"{emoji}\n{nome}\n{desc}",
                width=190, height=110,
                font=ctk.CTkFont(size=12),
                fg_color="#1E1E1E", hover_color="#1565C0",
                command=lambda n=nome: self._select_classe(n)
            )
            btn.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.classe_buttons[nome] = btn
        
        for c in range(4):
            grid.grid_columnconfigure(c, weight=1)
    
    def _build_step_background(self, frame):
        ctk.CTkLabel(frame, text="Qual a origem do seu herói?", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        ctk.CTkLabel(frame, text="Concede perícias e define sua história pregressa.", text_color="gray").pack(pady=(0, 20))
        
        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.bg_buttons = {}
        for i, (nome, emoji, pericias) in enumerate(self.BACKGROUNDS):
            row = i // 3
            col = i % 3
            btn = ctk.CTkButton(
                grid, text=f"{emoji}\n{nome}\n{pericias}",
                width=220, height=110,
                font=ctk.CTkFont(size=13),
                fg_color="#1E1E1E", hover_color="#6A1B9A",
                command=lambda n=nome: self._select_background(n)
            )
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.bg_buttons[nome] = btn
        
        for c in range(3):
            grid.grid_columnconfigure(c, weight=1)
    
    def _build_step_atributos(self, frame):
        ctk.CTkLabel(frame, text="Distribua seus atributos", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        
        # Rola 4d6 drop lowest
        if not self.data["atributos_rolados"]:
            from ui_utils import rolar_atributo_4d6
            self.data["atributos_rolados"] = sorted([rolar_atributo_4d6() for _ in range(6)], reverse=True)
        
        rolados = self.data["atributos_rolados"]
        rolados_texto = ", ".join(map(str, rolados))
        ctk.CTkLabel(frame, text=f"🎲 Seus dados (4d6 drop lowest): {rolados_texto}", 
                    font=ctk.CTkFont(size=13), text_color="#C9A84C").pack(pady=(0, 10))
        ctk.CTkLabel(frame, text="Digite os 6 valores na ordem: STR  DEX  CON  INT  WIS  CHA",
                    text_color="gray").pack(pady=(0, 10))
        ctk.CTkLabel(frame, text=f"Exemplo: {rolados[0]} {rolados[1]} {rolados[2]} {rolados[3]} {rolados[4]} {rolados[5]}",
                    font=ctk.CTkFont(size=11), text_color="gray").pack(pady=(0, 20))
        
        self.entry_atributos = ctk.CTkEntry(frame, width=500, height=40, font=ctk.CTkFont(size=14), 
                                           placeholder_text="Ex: 15 14 13 12 10 8")
        self.entry_atributos.pack(pady=10)
        self.entry_atributos.bind("<Return>", lambda e: self._validar_atributos())
        self.entry_atributos.focus()
        
        self.lbl_attr_erro = ctk.CTkLabel(frame, text="", text_color="red", font=ctk.CTkFont(size=11))
        self.lbl_attr_erro.pack(pady=5)
        
        # Preview dos mods
        self.frame_preview = ctk.CTkFrame(frame, fg_color="transparent")
        self.frame_preview.pack(pady=15, fill="x")
        self.lbl_preview = ctk.CTkLabel(self.frame_preview, text="", font=ctk.CTkFont(size=12), justify="left")
        self.lbl_preview.pack()
    
    def _build_step_confirmar(self, frame):
        ctk.CTkLabel(frame, text="Confira sua ficha", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        
        # Scrollable frame para ficha
        scroll = ctk.CTkScrollableFrame(frame, height=400)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.lbl_ficha = ctk.CTkLabel(scroll, text="", font=ctk.CTkFont(size=12), justify="left", anchor="w")
        self.lbl_ficha.pack(fill="x", padx=10, pady=10)
    
    def _show_step(self, index):
        self.current_step = index
        
        # Esconde todos
        for frame in self.step_frames.values():
            frame.pack_forget()
        
        # Mostra o atual
        key, _ = self.STEPS[index]
        self.step_frames[key].pack(fill="both", expand=True)
        
        # Atualiza labels do header
        for i, lbl in enumerate(self.step_labels):
            if i == index:
                lbl.configure(text_color="#C9A84C", font=ctk.CTkFont(size=11, weight="bold"))
            elif i < index:
                lbl.configure(text_color="green", font=ctk.CTkFont(size=11))
            else:
                lbl.configure(text_color="gray", font=ctk.CTkFont(size=11))
        
        # Atualiza botões
        self.btn_voltar.configure(state="normal" if index > 0 else "disabled")
        self.btn_proximo.pack(side="right") if index < len(self.STEPS) - 1 else self.btn_proximo.pack_forget()
        self.btn_finalizar.pack(side="right", padx=10) if index == len(self.STEPS) - 1 else self.btn_finalizar.pack_forget()
        
        # Ações específicas por step
        if key == "confirmar":
            self._atualizar_ficha()
        elif key == "atributos":
            self._atualizar_preview_atributos()
    
    def _select_raca(self, nome):
        self.data["raca"] = nome
        for n, btn in self.raca_buttons.items():
            btn.configure(fg_color="#2E7D32" if n == nome else "#1E1E1E")
        self.after(200, self._next_step)
    
    def _select_classe(self, nome):
        self.data["classe"] = nome
        for n, btn in self.classe_buttons.items():
            btn.configure(fg_color="#1565C0" if n == nome else "#1E1E1E")
        self.after(200, self._next_step)
    
    def _select_background(self, nome):
        self.data["background"] = nome
        for n, btn in self.bg_buttons.items():
            btn.configure(fg_color="#6A1B9A" if n == nome else "#1E1E1E")
        self.after(200, self._next_step)
    
    def _validar_atributos(self):
        try:
            partes = self.entry_atributos.get().replace(",", " ").split()
            if len(partes) != 6:
                raise ValueError("Precisa de 6 números")
            vals = [int(v) for v in partes]
            if any(v < 3 or v > 18 for v in vals):
                raise ValueError("Valores devem ser entre 3 e 18")
            
            # Verifica se é permutação dos dados rolados
            rolados = sorted(self.data["atributos_rolados"])
            if sorted(vals) != rolados:
                self.lbl_attr_erro.configure(text="⚠️ Use exatamente os valores rolados (ordem livre)")
                return
            
            # Aplica bônus racial
            from ui_utils import BONUS_RACA
            bonus = BONUS_RACA.get(self.data["raca"], [0]*6)
            attrs_final = [vals[i] + bonus[i] for i in range(6)]
            mods = [(v - 10) // 2 for v in attrs_final]
            
            attr_nomes = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
            self.data["atributos"] = dict(zip(attr_nomes, attrs_final))
            self.data["modificadores"] = dict(zip(attr_nomes, mods))
            
            self.lbl_attr_erro.configure(text="✅ Atributos válidos!", text_color="green")
            self.after(300, self._next_step)
            
        except ValueError as e:
            self.lbl_attr_erro.configure(text=f"❌ {e}")
    
    def _atualizar_preview_atributos(self):
        if not self.data.get("atributos"):
            self.lbl_preview.configure(text="")
            return
        
        from ui_utils import HP_POR_CLASSE, calcular_modificador
        attrs = self.data["atributos"]
        mods = self.data.get("modificadores", {k: calcular_modificador(v) for k,v in attrs.items()})
        classe = self.data["classe"]
        hp_base = HP_POR_CLASSE.get(classe, 8)
        hp_max = hp_base + mods["CON"]
        
        txt = f"HP: {hp_max}  |  "
        txt += "  ".join([f"{k}: {attrs[k]} ({mods[k]:+d})" for k in ["STR","DEX","CON","INT","WIS","CHA"]])
        self.lbl_preview.configure(text=txt)
    
    def _atualizar_ficha(self):
        attrs = self.data.get("atributos", {})
        mods = self.data.get("modificadores", {})
        classe = self.data["classe"]
        raca = self.data["raca"]
        bg = self.data["background"]
        
        from ui_utils import HP_POR_CLASSE, INVENTARIO_POR_CLASSE
        hp_base = HP_POR_CLASSE.get(classe, 8)
        hp_max = hp_base + mods.get("CON", 0)
        inv = INVENTARIO_POR_CLASSE.get(classe, [])
        
        txt = f"""🎭  NOME: {self.data['nome']}
🧬  RAÇA: {raca}
⚔️  CLASSE: {classe} (Nível 1)
📜  BACKGROUND: {bg}

❤️  HP MÁXIMO: {hp_max}

📊  ATRIBUTOS:
   STR: {attrs.get('STR',10)} ({mods.get('STR',0):+d})    DEX: {attrs.get('DEX',10)} ({mods.get('DEX',0):+d})    CON: {attrs.get('CON',10)} ({mods.get('CON',0):+d})
   INT: {attrs.get('INT',10)} ({mods.get('INT',0):+d})    WIS: {attrs.get('WIS',10)} ({mods.get('WIS',0):+d})    CHA: {attrs.get('CHA',10)} ({mods.get('CHA',0):+d})

🎒  EQUIPAMENTO INICIAL:
"""
        for item in inv:
            txt += f"   • {item}\n"
        
        # Código da party
        import random, string
        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        txt += f"\n🔗  CÓDIGO DA PARTY: PTY-{codigo}"
        txt += f"\n\n💾 Será salvo em saves/jogador_{self.data['nome'].lower()}.json"
        
        self.data["party_code"] = f"PTY-{codigo}"
        self.lbl_ficha.configure(text=txt)
    
    def _prev_step(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)
    
    def _next_step(self):
        key, _ = self.STEPS[self.current_step]
        
        # Valida step atual
        if key == "nome":
            nome = self.entry_nome.get().strip()
            if not nome:
                self.lbl_nome_erro.configure(text="❌ Digite um nome")
                return
            if len(nome) < 2:
                self.lbl_nome_erro.configure(text="❌ Nome muito curto")
                return
            self.data["nome"] = nome
            self.lbl_nome_erro.configure(text="")
        
        elif key == "raca" and not self.data["raca"]:
            return
        elif key == "classe" and not self.data["classe"]:
            return
        elif key == "background" and not self.data["background"]:
            return
        elif key == "atributos":
            if not self.data.get("atributos"):
                self.lbl_attr_erro.configure(text="❌ Digite os 6 atributos")
                return
        
        if self.current_step < len(self.STEPS) - 1:
            self._show_step(self.current_step + 1)
    
    def _finish(self):
        # Salva o personagem
        self._salvar_personagem()
        self.destroy()
        self.on_complete(self.data)
    
    def _salvar_personagem(self):
        import json
        from pathlib import Path
        from ui_utils import HP_POR_CLASSE, INVENTARIO_POR_CLASSE, ARMAS_DB, LOJA_CARVALHAL, calcular_modificador
        
        attrs = self.data["atributos"]
        mods = self.data.get("modificadores", {k: calcular_modificador(v) for k,v in attrs.items()})
        classe = self.data["classe"]
        hp_base = HP_POR_CLASSE.get(classe, 8)
        hp_max = hp_base + mods["CON"]
        inv = INVENTARIO_POR_CLASSE.get(classe, [])
        
        # Arma/armadura inicial
        arma_inicial = next((i for i in inv if any(a.lower() in i.lower() for a in ARMAS_DB.keys())), "Desarmado")
        armadura_inicial = next((i for i in inv if any(x in i for x in ["Armadura","Cota","Peitoral","Couro"])), "Trajes Comuns")
        if any("Escudo" in i for i in inv):
            armadura_inicial += " & Escudo"
        
        # CA base
        ca_base = 10 + mods["DEX"]
        if classe in ["Guerreiro", "Paladino", "Clérigo"]:
            ca_base = 16 if "Cota" in armadura_inicial or "Peitoral" in armadura_inicial else 14
        elif classe in ["Patrulheiro", "Ladino", "Bárbaro"]:
            ca_base = 11 + mods["DEX"]
        
        save_data = {
            "nome": self.data["nome"],
            "raca": self.data["raca"],
            "classe": classe,
            "background": self.data["background"],
            "sexo": self.data["sexo"],
            "nivel": 1,
            "xp": 0,
            "hp_maximo": hp_max,
            "hp_atual": hp_max,
            "str_val": attrs["STR"], "mod_str": mods["STR"],
            "dex_val": attrs["DEX"], "mod_dex": mods["DEX"],
            "con_val": attrs["CON"], "mod_con": mods["CON"],
            "int_val": attrs["INT"], "mod_int": mods["INT"],
            "wis_val": attrs["WIS"], "mod_wis": mods["WIS"],
            "cha_val": attrs["CHA"], "mod_cha": mods["CHA"],
            "modificador_ataque": (mods["DEX"] + 2 if classe in ["Ladino","Bardo","Monge","Patrulheiro"] else mods["STR"] + 2),
            "modificador_defesa": ca_base,
            "proficiencia": 2,
            "gold": 15,
            "inventario": inv,
            "arma_equipada": arma_inicial,
            "armadura_equipada": armadura_inicial,
            "dano_dado": ("1d12" if classe=="Bárbaro" else "1d10" if classe in ["Guerreiro","Paladino"] else "1d8" if classe in ["Patrulheiro","Ladino","Clérigo","Bardo","Monge"] else "1d6"),
            "mod_dano": (mods["DEX"] if classe in ["Ladino","Bardo","Monge","Patrulheiro"] else mods["STR"]),
            "slots_magia": 2 if classe in ["Bardo","Bruxo","Clérigo","Druida","Feiticeiro","Mago","Paladino","Patrulheiro","Artífice"] else 0,
            "slots_magia_max": 2 if classe in ["Bardo","Bruxo","Clérigo","Druida","Feiticeiro","Mago","Paladino","Patrulheiro","Artífice"] else 0,
            "hit_dice_max": 1, "hit_dice_atual": 1,
            "status_efeitos": [],
            "cena_atual": "carvalhal",
            "party_id": self.data.get("party_code", "PTY-LOCAL"),
            "telefone": f"local-{self.data['nome'].lower()}"
        }
        
        saves_dir = Path(__file__).parent / "saves"
        saves_dir.mkdir(exist_ok=True)
        save_path = saves_dir / f"jogador_{self.data['nome'].lower()}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        print(f"[pygame_ui] 💾 Personagem salvo local: {save_path}")
        
        # Salva no PostgreSQL se online
        if not MODO_OFFLINE:
            # Adiciona telefone formatado pro banco
            save_data["telefone"] = f"local-{self.data['nome'].lower()}"
            # Salva assincrono (não bloqueia UI)
            import threading
            def _save_async():
                try:
                    party_id = self.master._salvar_personagem_no_banco(save_data)
                    if party_id:
                        print(f"[pygame_ui] ✅ Personagem salvo no PostgreSQL: {party_id}")
                        # Atualiza o código da party no save local
                        save_data["party_id"] = party_id
                        with open(save_path, "w", encoding="utf-8") as f:
                            json.dump(save_data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"[pygame_ui] Erro thread banco: {e}")
            threading.Thread(target=_save_async, daemon=True).start()
    
    def _on_cancel(self):
        if self.current_step > 0:
            if not ctk.CTkInputDialog(text="Sair sem salvar? Progresso será perdido.", title="Confirmar").get_input():
                return
        self.destroy()


# =============================================================================
# TELA: ENTRAR NA PARTIDA
# =============================================================================
class PartyJoin(ctk.CTkToplevel):
    """Tela para entrar em uma party existente via código."""
    
    def __init__(self, master, on_join):
        super().__init__(master)
        self.on_join = on_join
        self.title("Entrar na Partida")
        self.geometry("500x350")
        self.minsize(500, 350)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._build_ui()
    
    def _build_ui(self):
        ctk.CTkLabel(self, text="🔗  ENTRAR NA PARTIDA", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(25, 10))
        ctk.CTkLabel(self, text="Digite o código da party (ex: PTY-A7K9M)", text_color="gray").pack(pady=(0, 20))
        
        self.entry_codigo = ctk.CTkEntry(self, width=300, height=45, font=ctk.CTkFont(size=16), placeholder_text="PTY-XXXXX")
        self.entry_codigo.pack(pady=10)
        self.entry_codigo.bind("<Return>", lambda e: self._tentar_entrar())
        self.entry_codigo.focus()
        
        self.lbl_status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12))
        self.lbl_status.pack(pady=10)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(btn_frame, text="Entrar", width=140, fg_color="#2E7D32", hover_color="#1B5E20",
                     command=self._tentar_entrar).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancelar", width=140, fg_color="gray",
                     command=self.destroy).pack(side="left", padx=10)
    
    def _tentar_entrar(self):
        codigo = self.entry_codigo.get().strip().upper()
        if not codigo.startswith("PTY-"):
            codigo = "PTY-" + codigo
        
        if len(codigo) != 9:
            self.lbl_status.configure(text="❌ Código inválido (formato: PTY-XXXXX)", text_color="red")
            return
        
        self.lbl_status.configure(text="🔍 Buscando party...", text_color="#C9A84C")
        self.update()
        
        # Tenta carregar save local primeiro
        from pathlib import Path
        import json
        save_path = Path(__file__).parent / "saves" / f"party_{codigo}.json"
        
        if save_path.exists():
            try:
                with open(save_path, "r", encoding="utf-8") as f:
                    party_data = json.load(f)
                self.lbl_status.configure(text="✅ Party encontrada localmente!", text_color="green")
                self.after(500, lambda: self._sucesso(party_data))
                return
            except Exception:
                pass
        
        # Tenta banco online se não for modo offline
        if not MODO_OFFLINE:
            try:
                import asyncio, asyncpg
                from dotenv import load_dotenv
                load_dotenv(Path(__file__).parent / ".env")
                db_url = os.environ.get("DATABASE_URL")
                
                if db_url:
                    async def _fetch():
                        conn = await asyncpg.connect(db_url)
                        try:
                            camp = await conn.fetchrow(
                                "SELECT * FROM campanhas WHERE party_id = $1", codigo
                            )
                            if camp:
                                membros = await conn.fetch(
                                    "SELECT * FROM jogadores WHERE party_id = $1", codigo
                                )
                                return dict(camp), [dict(m) for m in membros]
                            return None, []
                        finally:
                            await conn.close()
                    
                    camp, membros = asyncio.run(_fetch())
                    if camp:
                        self.lbl_status.configure(text="✅ Party encontrada no servidor!", text_color="green")
                        self.after(500, lambda: self._sucesso({"campanha": camp, "membros": membros}))
                        return
            except Exception as e:
                print(f"[PartyJoin] Erro banco: {e}")
        
        self.lbl_status.configure(text="❌ Party não encontrada (local nem online)", text_color="red")
    
    def _sucesso(self, party_data):
        self.destroy()
        self.on_join(party_data)


# =============================================================================
# TELA: CARREGAR JOGO (Save Games)
# =============================================================================
class TelaCarregarJogo(ctk.CTkToplevel):
    """Tela para escolher um jogo salvo (load game)."""

    def __init__(self, master, on_select):
        super().__init__(master)
        self.on_select = on_select
        self.title("Carregar Jogo")
        self.geometry("800x600")
        self.minsize(700, 500)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._build_ui()
        self._carregar_saves()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(header, text="📂  CARREGAR JOGO", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        # Lista scrollable
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # Botões footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=15)

        ctk.CTkButton(footer, text="➕ Novo Jogo", width=160, fg_color="#2E7D32",
                     command=self._novo_jogo).pack(side="left")
        ctk.CTkButton(footer, text="Fechar", width=100, fg_color="gray",
                     command=self.destroy).pack(side="right")

    def _carregar_saves(self):
        from pathlib import Path
        import json
        from datetime import datetime

        saves_dir = Path(__file__).parent / "saves"
        if not saves_dir.exists():
            self._mostrar_vazio()
            return

        saves = []
        for f in saves_dir.glob("jogador_*.json"):
            # Pula jogador_atual.json (save ativo da sessão)
            if f.name == "jogador_atual.json":
                continue
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                data["_save_path"] = str(f)  # Converte Path para string (JSON serializável)
                # Tenta ler mtime do arquivo como fallback de "último save"
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                data["_save_time"] = mtime.strftime("%d/%m/%Y %H:%M")
                saves.append(data)
                print(f"[DEBUG] Save encontrado: {data.get('nome', '?')} ({f.name})", flush=True)
            except Exception as e:
                print(f"[DEBUG] Erro lendo {f.name}: {e}", flush=True)
                pass

        # Ordena por mais recente primeiro (usa xp como proxy, ou nome)
        saves.sort(key=lambda s: s.get("xp", 0), reverse=True)

        if not saves:
            self._mostrar_vazio()
            return

        # Limpa cards existentes
        for widget in self.scroll.winfo_children():
            widget.destroy()

        for save in saves:
            self._add_save_card(save)
        
        # Força renderização no Windows
        self.scroll.update_idletasks()
        self.update_idletasks()

    def _mostrar_vazio(self):
        ctk.CTkLabel(self.scroll, text="Nenhum jogo salvo encontrado.\nClique em 'Novo Jogo' para começar uma aventura.",
                    text_color="gray", font=ctk.CTkFont(size=14), justify="center").pack(pady=80)

    def _add_save_card(self, save):
        card = ctk.CTkFrame(self.scroll, fg_color="#1E1E1E", corner_radius=10)
        card.pack(fill="x", pady=8, padx=5)

        # Info principal (linha 1: nome, classe, nível)
        info1 = ctk.CTkFrame(card, fg_color="transparent")
        info1.pack(fill="x", padx=15, pady=(12, 4))

        classe_emoji = {
            "Bárbaro": "😡", "Bardo": "🎵", "Bruxo": "🟣", "Clérigo": "✨",
            "Druida": "🌿", "Feiticeiro": "🔮", "Guerreiro": "⚔️",
            "Ladino": "🗡️", "Mago": "☄️", "Monge": "🥋", "Paladino": "⚔️✨",
            "Patrulheiro": "🏹", "Artífice": "⚙️"
        }.get(save.get("classe", ""), "❓")

        ctk.CTkLabel(info1, text=f"{classe_emoji}  {save.get('nome','?')}",
                    font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")

        ctk.CTkLabel(info1, text=f"  Nv.{save.get('nivel',1)}  {save.get('classe','?')}  {save.get('raca','?')}",
                    text_color="gray", font=ctk.CTkFont(size=13)).pack(side="left", padx=10)

        ctk.CTkLabel(info1, text=f"❤️  {save.get('hp_atual','?')}/{save.get('hp_maximo','?')}  🛡️ CA {save.get('modificador_defesa','?')}",
                    text_color="#C9A84C", font=ctk.CTkFont(size=12)).pack(side="left", padx=10)

        # Info secundária (linha 2: localização, ouro, último save)
        info2 = ctk.CTkFrame(card, fg_color="transparent")
        info2.pack(fill="x", padx=15, pady=(0, 4))

        cena_nome = save.get('cena_atual', 'carvalhal')
        from db_loader import CENAS
        cena_info = CENAS.get(cena_nome, {})
        local_display = cena_info.get('nome_sala', cena_nome)

        ctk.CTkLabel(info2, text=f"📍  {local_display}",
                    text_color="gray", font=ctk.CTkFont(size=11)).pack(side="left")

        ctk.CTkLabel(info2, text=f"💰  {save.get('gold',0)} PO",
                    text_color="#FFD700", font=ctk.CTkFont(size=11)).pack(side="left", padx=15)

        ctk.CTkLabel(info2, text=f"⭐  {save.get('xp',0)} XP",
                    text_color="#9C27B0", font=ctk.CTkFont(size=11)).pack(side="left", padx=15)

        save_time = save.get("_save_time", "?")
        ctk.CTkLabel(info2, text=f"🕐  Último save: {save_time}",
                    text_color="gray", font=ctk.CTkFont(size=10)).pack(side="right")

        # Botões ação
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(4, 10))

        ctk.CTkButton(btn_frame, text="▶ Continuar", width=120, fg_color="#2E7D32", height=34,
                     command=lambda s=save: self._selecionar(s)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🗑️ Excluir", width=100, height=34, fg_color="#C62828",
                     command=lambda s=save: self._excluir(s)).pack(side="left", padx=5)

    def _selecionar(self, save):
        print(f"[DEBUG] TelaCarregarJogo._selecionar: {save.get('nome', '?')}", flush=True)
        self.destroy()
        self.on_select(save)

    def _novo_jogo(self):
        self.destroy()
        self.on_select({"_action": "novo"})

    def _excluir(self, save):
        from tkinter import messagebox
        from pathlib import Path
        if messagebox.askyesno("Excluir save", f"Excluir '{save['nome']}' permanentemente?"):
            try:
                save_path = save.get("_save_path")
                if isinstance(save_path, str):
                    save_path = Path(save_path)
                if not save_path or not save_path.exists():
                    messagebox.showerror("Erro", "Arquivo de save não encontrado.")
                    return
                # Verifica se não é o save atual
                if save_path.name == "jogador_atual.json":
                    messagebox.showerror("Erro", "Não pode excluir o save da sessão ativa.")
                    return
                save_path.unlink()
                self._carregar_saves()  # refresh
            except PermissionError:
                messagebox.showerror("Erro", "Arquivo em uso. Feche o jogo e tente novamente.")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao excluir: {e}")


# =============================================================================
# TELA: CONFIGURAÇÕES (placeholder)
# =============================================================================
class SettingsScreen(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Configurações")
        self.geometry("500x400")
        self.transient(master)
        self.grab_set()
        
        ctk.CTkLabel(self, text="⚙️  CONFIGURAÇÕES", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=25)
        ctk.CTkLabel(self, text="Em breve: volume, gráficos, controles, conta...", text_color="gray").pack(pady=20)
        
        ctk.CTkButton(self, text="Fechar", width=120, command=self.destroy).pack(pady=20)


# =============================================================================
# CACHE DE IMAGENS (1ª vez baixa, depois disco)
# =============================================================================
def _cache_path(url: str) -> Path:
    nome = abs(hash(url))
    return CACHE_DIR / f"{nome}.jpg"


def _placeholder_imagem(titulo: str, emoji: str, cor_fundo: tuple = (40, 40, 60), size=(600, 350)) -> Image.Image:
    """Gera um placeholder visual quando a imagem não baixa."""
    img = Image.new("RGB", size, cor_fundo)
    draw = ImageDraw.Draw(img)

    # Tenta carregar uma fonte maior; cai pra default se não tiver
    try:
        font_titulo = ImageFont.truetype("arial.ttf", 36)
        font_emoji = ImageFont.truetype("seguiemj.ttf", 120)
    except Exception:
        font_titulo = ImageFont.load_default()
        font_emoji = ImageFont.load_default()

    # Emoji gigante no centro
    bbox = draw.textbbox((0, 0), emoji, font=font_emoji)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size[0] - w) / 2, (size[1] - h) / 2 - 30), emoji, font=font_emoji, fill=(200, 200, 220))

    # Título embaixo
    bbox2 = draw.textbbox((0, 0), titulo, font=font_titulo)
    w2 = bbox2[2] - bbox2[0]
    draw.text(((size[0] - w2) / 2, size[1] - 60), titulo, font=font_titulo, fill=(220, 220, 240))
    return img


def carregar_imagem(url: str, titulo: str = "", emoji: str = "🏰", size: tuple = None) -> Image.Image:
    """
    Carrega imagem (cache em disco). Se falhar, gera placeholder procedural.
    """
    if size is None:
        size = TAMANHO_IMAGEM

    if not url or "PLACEHOLDER" in url:
        return _placeholder_imagem(titulo or "Sem imagem", emoji, size=size)

    cache = _cache_path(url)
    if cache.exists():
        try:
            return Image.open(cache).convert("RGB").resize(size)
        except Exception:
            pass  # cache corrompido, baixa de novo

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        img.save(cache, "JPEG", quality=85)
        return img.resize(size)
    except Exception as e:
        print(f"[img] falhou baixar {url}: {e}")
        return _placeholder_imagem(titulo, emoji, size=size)


# =============================================================================
# FRAME RESPONSIVO PARA BOTÕES (quebra linha automática)
# =============================================================================
class ResponsiveButtonFrame(ctk.CTkFrame):
    """Frame que organiza botões em grid responsivo, quebrando linha conforme largura."""
    
    def __init__(self, master, min_button_width=100, button_height=32, 
                 padding=4, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.min_button_width = min_button_width
        self.button_height = button_height
        self.padding = padding
        self.buttons = []  # (widget, texto_original)
        self._resize_job = None
        self.bind("<Configure>", self._on_resize)
        self.grid_columnconfigure(0, weight=1)
        
    def add_button(self, text, command, width=None, **kwargs):
        """Adiciona botão. Se width=None, usa min_button_width."""
        btn_width = width or self.min_button_width
        btn = ctk.CTkButton(
            self, text=text, command=command, 
            width=btn_width, height=self.button_height, **kwargs
        )
        self.buttons.append((btn, text, btn_width))
        self._reflow()
        return btn
    
    def clear(self):
        for btn, _, _ in self.buttons:
            btn.destroy()
        self.buttons.clear()
    
    def _on_resize(self, event):
        """Debounce do resize para reflow."""
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(50, self._reflow)
    
    def _reflow(self):
        """Reorganiza botões em grid baseado na largura disponível."""
        if not self.buttons:
            return
        
        container_width = self.winfo_width() - 20
        if container_width < 50:
            return
            
        btn_width = self.buttons[0][2]
        cols = max(1, container_width // (btn_width + self.padding * 2))
        
        for i, (btn, _, _) in enumerate(self.buttons):
            row = i // cols
            col = i % cols
            btn.grid(row=row, column=col, padx=self.padding, pady=self.padding, sticky="ew")
        
        for c in range(cols):
            self.grid_columnconfigure(c, weight=1)


# =============================================================================
# JANELA PRINCIPAL
# =============================================================================

TAMANHO_IMAGEM = (640, 360)
TITULO_JANELA = "RPG Bot — Cidadela Sem Sol (Protótipo Desktop)"


class RPGApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(TITULO_JANELA)
        self.geometry("800x900")
        # Força DPI awareness no Windows ANTES de configurar a janela
        if sys.platform == "win32":
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                try:
                    windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Força geometry após mainloop iniciar
        self.after(10, self._forcar_geometry)

        # Estado do jogo (preenchido após escolha no menu)
        self.jogador = None
        self._cena_inicial = "carvalhal"
        self.estado_salas = {}
        self.cena_atual: Optional[dict] = None
        self.inimigo_atual: Optional[dict] = None
        self.hp_grupo_inimigo: int = 0
        self.hp_max_inimigo: int = 1

        # Mostra menu principal
        self._mostrar_menu()

    def _mostrar_menu(self):
        """Mostra a tela inicial do menu."""
        # Limpa widgets existentes
        for widget in self.winfo_children():
            widget.destroy()
        
        self.main_menu = MainMenu(
            self,
            on_novo_jogo=self._novo_jogo,
            on_carregar_jogo=self._abrir_carregar_jogo,
            on_entrar_partida=self._abrir_entrar_partida,
            on_config=self._abrir_config
        )

    def _novo_jogo(self):
        """Inicia wizard de criação de personagem."""
        self.main_menu.destroy()
        CharacterCreator(self, on_complete=self._apos_criar_personagem)

    def _apos_criar_personagem(self, char_data):
        """Callback quando personagem é criado."""
        # Carrega o save recém-criado
        from pathlib import Path
        import json
        save_path = Path(__file__).parent / "saves" / f"jogador_{char_data['nome'].lower()}.json"
        with open(save_path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        
        self._iniciar_jogo_com_dados(dados)

    def _abrir_entrar_partida(self):
        """Abre tela para entrar em party existente."""
        self.main_menu.destroy()
        PartyJoin(self, on_join=self._apos_entrar_partida)

    def _apos_entrar_partida(self, party_data):
        """Callback quando party é encontrada."""
        # Se tem membros, abre tela de carregar jogo filtrada pela party
        party_id = party_data.get("campanha", {}).get("party_id") or party_data.get("party_id")
        if party_data.get("membros"):
            self.main_menu.destroy()
            TelaCarregarJogo(self, on_select=lambda s: self._apos_selecionar_save_com_party(s, party_id))
        else:
            # Party vazia - cria personagem novo nessa party
            CharacterCreator(self, on_complete=lambda c: self._criar_em_party(c, party_id))

    def _apos_selecionar_save_com_party(self, save_data, party_id):
        """Callback quando save é selecionado dentro de uma party."""
        if save_data.get("_action") == "novo":
            CharacterCreator(self, on_complete=lambda c: self._criar_em_party(c, party_id))
        else:
            save_data["party_id"] = party_id
            self._iniciar_jogo_com_dados(save_data)

    def _criar_em_party(self, char_data, party_id):
        """Cria personagem e adiciona à party existente."""
        from pathlib import Path
        import json
        save_path = Path(__file__).parent / "saves" / f"jogador_{char_data['nome'].lower()}.json"
        with open(save_path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        dados["party_id"] = party_id
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)

        # Se online, atualiza no banco também
        if not MODO_OFFLINE:
            telefone = dados.get("telefone", f"local-{dados['nome'].lower()}")
            db_desktop.entrar_party_no_banco(party_id, telefone)

        self._iniciar_jogo_com_dados(dados)

    def _abrir_carregar_jogo(self):
        """Abre tela para carregar jogo salvo."""
        self.main_menu.destroy()
        TelaCarregarJogo(self, on_select=self._apos_selecionar_save)

    def _apos_selecionar_save(self, save_data):
        """Callback quando save é selecionado."""
        # Garante que a janela principal está visível e pronta
        self.deiconify()
        self.update_idletasks()
        
        if save_data.get("_action") == "novo":
            CharacterCreator(self, on_complete=self._apos_criar_personagem)
        else:
            self._iniciar_jogo_com_dados(save_data)

    def _abrir_config(self):
        """Abre tela de configurações."""
        SettingsScreen(self)

    def _iniciar_jogo_com_dados(self, dados_jogador):
        """Inicializa o jogo com os dados do personagem selecionado/criado."""
        import json
        from pathlib import Path

        print(f"[DEBUG] _iniciar_jogo_com_dados: {dados_jogador.get('nome', '?')}", flush=True)
        
        # Garante que a janela principal está visível e no topo
        self.deiconify()
        self.lift()
        self.focus_force()
        self.update_idletasks()
        
        self.jogador = MockJogador(dados_db=dados_jogador)
        self._cena_inicial = dados_jogador.get("cena_atual", "carvalhal")

        estado_salas_raw = dados_jogador.get("estado_salas", {})
        if isinstance(estado_salas_raw, str):
            try:
                self.estado_salas = json.loads(estado_salas_raw)
            except Exception:
                self.estado_salas = {}
        elif isinstance(estado_salas_raw, dict):
            self.estado_salas = estado_salas_raw
        else:
            self.estado_salas = {}

        # Sincroniza tudo (salva local + PostgreSQL)
        db_desktop.sincronizar_tudo(dados_jogador, self._cena_inicial, self.estado_salas)

        print(f"[pygame_ui] ✅ {self.jogador.nome} ({self.jogador.classe}) carregado | cena={self._cena_inicial} | party={self.jogador.party_id}")

        # Build UI do jogo
        try:
            print("[DEBUG] Chamando _build_ui()...", flush=True)
            self._build_ui()
            print("[DEBUG] _build_ui() OK", flush=True)
        except Exception as e:
            print(f"[ERRO] _build_ui falhou: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return
            
        # Força layout e renderização COMPLETA no Windows
        self.update_idletasks()
        self.deiconify()
        self.update()  # FORÇA redraw imediato
            
        try:
            print(f"[DEBUG] Chamando ir_para({self._cena_inicial})...", flush=True)
            self.ir_para(self._cena_inicial)
            print("[DEBUG] ir_para() OK", flush=True)
        except Exception as e:
            print(f"[ERRO] ir_para falhou: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return

        # Segundo update forçado após ir_para
        self.update_idletasks()
        self.update()

        # Foco robusto no chat (Windows + CustomTkinter)
        def _focar_chat():
            try:
                self.entrada_texto.focus_force()
                self.entrada_texto.icursor("end")
            except Exception:
                pass
        self.after(50, _focar_chat)
        self.after(200, _focar_chat)
        self.after(500, _focar_chat)
        self.after(2000, self._check_update_async)

    def _salvar_personagem_no_banco(self, save_data: dict) -> Optional[str]:
        """Salva personagem no PostgreSQL (chamado por CharacterCreator em thread)."""
        if MODO_OFFLINE:
            return None
        try:
            return db_desktop.criar_personagem_no_banco(save_data)
        except Exception as e:
            print(f"[pygame_ui] Erro salvando no banco: {e}")
            return None

    def _check_update_async(self):
        """Verifica update em background após 2s de carregamento."""
        try:
            from update_check import check_for_update
            result = check_for_update(APP_UPDATE_URL, APP_VERSAO)
            if result and result.get("update_disponivel"):
                # Agenda popup pro main thread
                self.after(0, lambda: self._show_update_popup(result))
        except Exception as e:
            print(f"[pygame_ui] Update check falhou: {e}")

    def _show_update_popup(self, info: dict):
        """Popup de update: changelog + botão 'Baixar'."""
        popup = ctk.CTkToplevel(self)
        popup.title(f"Atualização disponível — v{info['nova_versao']}")
        popup.geometry("450x400")
        popup.transient(self)
        popup.grab_set()

        ctk.CTkLabel(
            popup,
            text=f"Nova versão disponível!",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=10)

        ctk.CTkLabel(
            popup,
            text=f"Tu tens: v{info['versao_local']}  →  Nova: v{info['nova_versao']}",
            font=ctk.CTkFont(size=13),
        ).pack(pady=5)

        ctk.CTkLabel(
            popup,
            text=f"Data de lançamento: {info.get('release_date', '?')}",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack()

        ctk.CTkLabel(popup, text="─" * 50).pack(pady=10, fill="x", padx=20)

        ctk.CTkLabel(
            popup,
            text="O que há de novo:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(anchor="w", padx=20)

        changelog_text = ctk.CTkTextbox(popup, height=120, font=ctk.CTkFont(size=11))
        changelog_text.pack(fill="both", expand=True, padx=20, pady=5)
        changelog_text.insert("1.0", info.get("changelog", "Sem notas."))
        changelog_text.configure(state="disabled")

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=10)

        def baixar():
            webbrowser.open(info.get("download_url", APP_DOWNLOAD_URL))
            popup.destroy()

        ctk.CTkButton(
            btn_frame, text="Baixar agora", fg_color="#2E7D32", hover_color="#1B5E20",
            command=baixar,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame, text="Depois", fg_color="gray",
            command=popup.destroy,
        ).pack(side="left", padx=5)

    # ── LAYOUT ─────────────────────────────────────────────────────────────

    def _forcar_geometry(self):
        """Força a geometry após mainloop iniciar (necessário no Windows/customtkinter)."""
        try:
            self.geometry("800x900")
        except Exception:
            pass
        try:
            self.minsize(600, 500)
        except Exception:
            pass
        # Force update
        self.update_idletasks()

    def _build_ui(self):
        # Configura tamanho mínimo da janela
        self.minsize(600, 500)
        
        # Imagem no topo - responsiva
        self.frame_imagem = ctk.CTkFrame(self, height=360)
        self.frame_imagem.pack(fill="x", padx=10, pady=(10, 5))
        self.frame_imagem.pack_propagate(False)  # mantém altura fixa
        self.label_imagem = ctk.CTkLabel(self.frame_imagem, text="")
        self.label_imagem.pack(expand=True, fill="both")
        # Bind para redimensionar imagem quando janela muda
        self.bind("<Configure>", self._on_window_resize)
        self._img_url_atual = None
        self._img_titulo_atual = None
        self._img_emoji_atual = None
        self._img_atual = None
        
        # Força placeholder inicial se não tiver URL
        self.after(100, self._garantir_placeholder_inicial)

        # Log narrativo
        self.frame_log = ctk.CTkFrame(self)
        self.frame_log.pack(fill="both", expand=True, padx=10, pady=5)
        ctk.CTkLabel(self.frame_log, text="📜 Diário de Bordo", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.log_text = ctk.CTkTextbox(self.frame_log, wrap="word", font=ctk.CTkFont(size=13), state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        # Bind mouse wheel for scrolling
        self.log_text.bind("<MouseWheel>", lambda e: self.log_text._parent_canvas.yview_scroll(int(-1*(e.delta/120)), "units") if hasattr(self.log_text, "_parent_canvas") else None)
        # Also bind to the internal canvas if accessible
        def _on_mousewheel(e):
            try:
                self.log_text._parent_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
            except Exception:
                pass
        self.log_text.bind("<MouseWheel>", _on_mousewheel)
        self.log_text.bind("<Button-4>", lambda e: self.log_text._parent_canvas.yview_scroll(-1, "units"))  # Linux scroll up
        self.log_text.bind("<Button-5>", lambda e: self.log_text._parent_canvas.yview_scroll(1, "units"))   # Linux scroll down

        # Frame de direções - RESPONSIVO
        self.frame_direcoes = ctk.CTkFrame(self)
        self.frame_direcoes.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.frame_direcoes, text="🚪 Caminhos", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.botoes_direcoes_frame = ResponsiveButtonFrame(self.frame_direcoes, min_button_width=90, button_height=30)
        self.botoes_direcoes_frame.pack(fill="x", padx=10, pady=5)

        # Frame de ações fixas + contextuais - RESPONSIVO
        self.frame_acoes = ctk.CTkFrame(self)
        self.frame_acoes.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.frame_acoes, text="⚔️ Ações", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.botoes_acoes_frame = ResponsiveButtonFrame(self.frame_acoes, min_button_width=100, button_height=30)
        self.botoes_acoes_frame.pack(fill="x", padx=10, pady=5)

        # Frame de text-box (comando livre)
        self.frame_comando = ctk.CTkFrame(self)
        self.frame_comando.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.frame_comando, text="💬 Fala com o narrador (ou digita 'norte'/'sul' pra mover)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))
        entrada_frame = ctk.CTkFrame(self.frame_comando, fg_color="transparent")
        entrada_frame.pack(fill="x", padx=10, pady=5)
        self.entrada_texto = ctk.CTkEntry(entrada_frame, placeholder_text="Ex: examino o pedestal, vou pro norte, abro o bau...", takefocus=True)
        self.entrada_texto.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entrada_texto.bind("<Return>", self._on_enter_comando)  # Enter envia
        self.entrada_texto.focus_set()  # foco automático pro chat
        self.entrada_texto.bind("<Button-1>", lambda e: self.entrada_texto.focus_force())
        ctk.CTkButton(entrada_frame, text="▶ Enviar", width=100, command=self._enviar_comando).pack(side="left")

        # Status bar
        self.status_bar = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("gray85", "gray20"),
            corner_radius=0,
        )
        self.status_bar.pack(fill="x", side="bottom", ipady=10)

        # Força layout final
        self.update_idletasks()

    # ── LOG ────────────────────────────────────────────────────────────────

    def _atualizar_imagem(self):
        """Atualiza a imagem da sala com tamanho responsivo ao frame."""
        if not self._img_url_atual:
            return
        frame_w = self.frame_imagem.winfo_width()
        frame_h = self.frame_imagem.winfo_height()
        if frame_w < 100 or frame_h < 50:
            return
        target_w = frame_w - 20
        target_h = int(target_w * 9 / 16)
        if target_h > frame_h - 20:
            target_h = frame_h - 20
            target_w = int(target_h * 16 / 9)
        size = (max(100, target_w), max(60, target_h))
        
        img = carregar_imagem(self._img_url_atual, titulo=self._img_titulo_atual, 
                              emoji=self._img_emoji_atual, size=size)
        self._img_atual = ctk.CTkImage(light_image=img, dark_image=img, size=size)
        self.label_imagem.configure(image=self._img_atual, text="")

    def _on_window_resize(self, event):
        """Callback ao redimensionar janela - atualiza imagem."""
        if event.widget == self:
            self.after(50, self._atualizar_imagem)

    def _garantir_placeholder_inicial(self):
        """Gera placeholder inicial se ainda não tiver imagem."""
        if not self._img_atual and self._img_url_atual:
            self._atualizar_imagem()
        elif not self._img_atual and not self._img_url_atual:
            # Fallback: placeholder genérico
            from imagens_config import url_para
            self._img_url_atual = url_para("cena", "carvalhal")
            self._img_titulo_atual = "Vila de Carvalhal"
            self._img_emoji_atual = "🏰"
            self._atualizar_imagem()

    def log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        # Ensure scrollregion updated for mouse wheel
        self.log_text.update_idletasks()

    # ── NAVEGAÇÃO ──────────────────────────────────────────────────────────
    def ir_para(self, cod_sala: str):
        cena = get_cena(cod_sala)
        if not cena:
            self.log(f"⚠️  Sala '{cod_sala}' não existe no banco.")
            return

        self.cena_atual = cena
        self.jogador.cena_atual = cod_sala
        self.inimigo_atual = None

        # Imagem - guarda info para resize responsivo
        url = url_para("cena", cod_sala)
        emoji = "🏰" if cod_sala == "carvalhal" else "🗡️"
        self._img_url_atual = url
        self._img_titulo_atual = cena["nome_sala"]
        self._img_emoji_atual = emoji
        self._atualizar_imagem()
        self.title(f"{TITULO_JANELA} — {cena['nome_sala']}")

        # Log
        self.log(f"📍 {cena['nome_sala']}\n{cena['descricao_visual']}")

        # Verifica encontros vivos
        encontros = get_encontros_vivos(cod_sala, self.estado_salas)
        if encontros:
            enc = encontros[0]
            self.inimigo_atual = get_inimigo(enc["nome_inimigo"])
            # Desktop é single-player: SEM difficulty scaling (jogador único = baseline)
            self.hp_grupo_inimigo = self.inimigo_atual["hp_max"] * enc["quantidade"] if self.inimigo_atual else 0
            self.hp_max_inimigo = self.inimigo_atual["hp_max"] if self.inimigo_atual else 1
            self.log(f"⚠️  AMEAÇA: {enc['quantidade']}x {enc['nome_inimigo']} (CA {self.inimigo_atual['ca']}, HP {self.hp_grupo_inimigo})")

        # Aplica hazards da sala (canônico, do game_helpers)
        hazards = cena.get("hazards", [])
        if hazards:
            from game_helpers import aplicar_hazards
            narrativa_hz = aplicar_hazards(self.jogador, hazards)
            if narrativa_hz:
                self.log(f"⚠️  HAZARDS:{narrativa_hz}")
                # se morreu por hazard, resgate canônico
                if self.jogador.hp_atual == 0:
                    from game_helpers import aplicar_morte_resgate
                    class _FakeC:
                        cena_atual = cod_sala
                        em_combate = True
                    aplicar_morte_resgate(self.jogador, _FakeC())
                    self.ir_para("carvalhal")
                    self.jogador.hp_atual = self.jogador.hp_maximo
                    return

        # Verifica NPCs (heurística: nomes Meepo/Erky/Sharwyn são da Cidadela)
        # Pra protótipo, sempre tenta mostrar NPCs conhecidos
        self._atualizar_botoes()
        self._auto_save(silencioso=True)  # salva após navegar

    # ── BOTÕES ─────────────────────────────────────────────────────────────
    def _limpar_frame(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    def _atualizar_botoes(self):
        # Usa clear() do ResponsiveButtonFrame
        self.botoes_direcoes_frame.clear()
        self.botoes_acoes_frame.clear()

        # Direções
        if self.cena_atual and self.cena_atual.get("conexoes"):
            for direcao, destino in self.cena_atual["conexoes"].items():
                self.botoes_direcoes_frame.add_button(
                    f"🚪 {direcao.title()}",
                    lambda d=destino: self.ir_para(d),
                    width=90
                )

        # Ações contextuais
        if self.inimigo_atual:
            self.botoes_acoes_frame.add_button(
                "⚔️ Atacar", self.atacar, width=100,
                fg_color="#8B0000", hover_color="#A52A2A"
            )
            self.botoes_acoes_frame.add_button(
                "🏃 Fugir", self.fugir, width=100
            )

        # Ações fixas
        self.botoes_acoes_frame.add_button("👁️ Vasculhar", self.vasculhar, width=100)
        self.botoes_acoes_frame.add_button("💬 Falar", self.falar_npc, width=100)
        self.botoes_acoes_frame.add_button("🎒 Inventário", self.ver_inventario, width=100)
        self.botoes_acoes_frame.add_button("🛌 Descansar", self.descansar, width=100)
        self.botoes_acoes_frame.add_button("📊 Status", self.ver_status, width=100)
        self.botoes_acoes_frame.add_button("💾 Salvar", lambda: self._auto_save(silencioso=False), width=100,
            fg_color="#2E7D32", hover_color="#1B5E20")
        self.botoes_acoes_frame.add_button("🗡️ Equipar", self.equipar_popup, width=100,
            fg_color="#4A148C", hover_color="#6A1B9A")
        self.botoes_acoes_frame.add_button("💰 Loja", self.loja_popup, width=100,
            fg_color="#E65100", hover_color="#EF6C00")
        self.botoes_acoes_frame.add_button("🧙 Criar", self.criar_personagem_wizard, width=100,
            fg_color="#37474F", hover_color="#546E7A")

        self._atualizar_status()

    def _atualizar_status(self):
        cena_nome = self.cena_atual["nome_sala"] if self.cena_atual else "???"
        hp_pct = self.jogador.hp_atual / max(1, self.jogador.hp_maximo)
        cor = "🟢" if hp_pct > 0.66 else "🟡" if hp_pct > 0.33 else "🔴"
        
        # Texto completo
        texto_completo = (
            f" {cor}  ❤️  {self.jogador.hp_atual}/{self.jogador.hp_maximo}    "
            f"🛡️  CA {self.jogador.modificador_defesa}    "
            f"🪙  {self.jogador.gold} PO    "
            f"⭐  Nv {self.jogador.nivel} ({self.jogador.xp} XP)    "
            f"📍  {cena_nome}"
        )
        # Texto compacto para janelas pequenas
        texto_compacto = (
            f"{cor} ❤️{self.jogador.hp_atual}/{self.jogador.hp_maximo} "
            f"🛡️{self.jogador.modificador_defesa} 🪙{self.jogador.gold} ⭐{self.jogador.nivel}"
        )
        
        # Ajusta fonte baseado na largura
        try:
            largura = self.winfo_width()
            if largura < 700:
                self.status_bar.configure(text=texto_compacto, font=ctk.CTkFont(size=11, weight="bold"))
            else:
                self.status_bar.configure(text=texto_completo, font=ctk.CTkFont(size=13, weight="bold"))
        except Exception:
            self.status_bar.configure(text=texto_completo)

    def _auto_save(self, silencioso: bool = False):
        """
        Salva o estado do jogador no PostgreSQL + JSON local via db_desktop.
        Chamado após cada ação significativa.
        Inclui o estado_salas (inimigos derrotados, baús abertos, etc.).
        """
        if not hasattr(self, 'jogador') or not self.jogador:
            return
        try:
            # Converte MockJogador para dict compatível
            dados = {
                "telefone": self.jogador.telefone,
                "party_id": self.jogador.party_id,
                "nome": self.jogador.nome,
                "raca": self.jogador.raca,
                "classe": self.jogador.classe,
                "background": getattr(self.jogador, 'background', ''),
                "sexo": getattr(self.jogador, 'sexo', ''),
                "nivel": self.jogador.nivel,
                "xp": self.jogador.xp,
                "hp_atual": self.jogador.hp_atual,
                "hp_maximo": self.jogador.hp_maximo,
                "str_val": self.jogador.str_val, "mod_str": self.jogador.mod_str,
                "dex_val": self.jogador.dex_val, "mod_dex": self.jogador.mod_dex,
                "con_val": self.jogador.con_val, "mod_con": self.jogador.mod_con,
                "int_val": self.jogador.int_val, "mod_int": self.jogador.mod_int,
                "wis_val": self.jogador.wis_val, "mod_wis": self.jogador.mod_wis,
                "cha_val": self.jogador.cha_val, "mod_cha": self.jogador.mod_cha,
                "modificador_ataque": self.jogador.modificador_ataque,
                "modificador_defesa": self.jogador.modificador_defesa,
                "proficiencia": self.jogador.proficiencia,
                "gold": self.jogador.gold,
                "inventario": self.jogador.inventario,
                "arma_equipada": self.jogador.arma_equipada,
                "armadura_equipada": self.jogador.armadura_equipada,
                "dano_dado": self.jogador.dano_dado,
                "mod_dano": self.jogador.mod_dano,
                "slots_magia": self.jogador.slots_magia,
                "slots_magia_max": self.jogador.slots_magia_max,
                "hit_dice_atual": self.jogador.hit_dice_atual,
                "hit_dice_max": self.jogador.hit_dice_max,
                "status_efeitos": self.jogador.status_efeitos,
                "cena_atual": self.jogador.cena_atual,
                "cena_anterior": getattr(self.jogador, 'cena_anterior', None),
            }
            result = db_desktop.sincronizar_tudo(dados, self.cena_atual["cod_sala"] if self.cena_atual else "carvalhal", self.estado_salas)
            if not silencioso:
                local = "✅" if result else "❌"
                self.log(f"💾 Save: local ✅ | banco {'✅' if result else '❌'}")
        except Exception as e:
            if not silencioso:
                self.log(f"❌ Erro ao salvar: {e}")

    # ── TEXT-BOX: COMANDO LIVRE ─────────────────────────────────────────────
    DIRECOES_RAPIDAS = {
        "norte": "norte", "n": "norte", "ir pro norte": "norte", "vou pro norte": "norte",
        "sul": "sul", "s": "sul", "ir pro sul": "sul", "vou pro sul": "sul",
        "leste": "leste", "e": "leste", "ir pro leste": "leste", "vou pro leste": "leste",
        "oeste": "oeste", "o": "oeste", "ir pro oeste": "oeste", "vou pro oeste": "oeste",
        "cima": "cima", "subir": "cima", "subo": "cima", "ir pra cima": "cima",
        "baixo": "baixo", "descer": "baixo", "desço": "baixo", "ir pra baixo": "baixo",
        "voltar": None,  # heurística: primeira conexão
    }

    def _on_enter_comando(self, event=None):
        """Handler do Enter na text-box."""
        self._enviar_comando()

    def _enviar_comando(self):
        """Lê o texto da text-box e decide: direção rápida, ação local, ou IA."""
        texto = self.entrada_texto.get().strip()
        if not texto:
            return
        self.entrada_texto.delete(0, "end")
        self.log(f"💬 > {texto}")

        texto_lower = texto.lower().strip()

        # 1. Tenta direção rápida
        direcao = self.DIRECOES_RAPIDAS.get(texto_lower)
        if direcao is not None:
            # direção específica
            if self.cena_atual and self.cena_atual.get("conexoes", {}).get(direcao):
                self.ir_para(self.cena_atual["conexoes"][direcao])
                return
            elif direcao is None or not self.cena_atual:
                # "voltar" ou sem direção
                conexoes = self.cena_atual.get("conexoes", {}) if self.cena_atual else {}
                if conexoes:
                    primeira = list(conexoes.values())[0]
                    self.ir_para(primeira)
                    return
                self.log("⚠️  Não há para onde ir daqui.")
                return
            else:
                self.log(f"⚠️  Sem saída pra {direcao} daqui.")
                return

        # 2. Ações simples que não precisam de IA
        if texto_lower in ("atacar", "ataque", "mata", "matar", "bater"):
            self.atacar()
            return
        if texto_lower in ("fugir", "foge", "foge!", "corre", "correr", "recuar"):
            self.fugir()
            return
        if texto_lower in ("vasculhar", "olhar", "examinar sala", "examinar"):
            self.vasculhar()
            return
        if texto_lower in ("falar", "conversar", "dialogar"):
            self.falar_npc()
            return
        if texto_lower in ("descansar", "dorme", "repousar"):
            self.descansar()
            return
        if texto_lower in ("status", "ficha"):
            self.ver_status()
            return
        if texto_lower in ("inventario", "mochila", "itens", "inv"):
            self.ver_inventario()
            return
        if texto_lower in ("salvar", "save"):
            self._auto_save(silencioso=False)
            return

        # 3. Ação livre — tenta parser local primeiro, depois IA
        if not self._interpretar_local(texto):
            self._interpretar_com_ia(texto)

    def _interpretar_local(self, texto: str) -> bool:
        """Parser local de texto livre — retorna True se processou, False se não entendeu."""
        import re
        t = texto.lower().strip()
        
        # Movimento: "vou pro norte", "vou north", "andar sul", "ir leste", "caminho oeste"
        mov_match = re.search(r'\b(vou|ir|andar|caminho|mover)\s+(pro\s+|para\s+)?(norte|sul|leste|oeste|nordeste|noroeste|sudeste|sudoeste)\b', t)
        if mov_match:
            direcao = mov_match.group(3)
            if self.cena_atual and self.cena_atual.get("conexoes", {}).get(direcao):
                self.ir_para(self.cena_atual["conexoes"][direcao])
            else:
                self.log(f"⚠️  Não dá pra ir {direcao} daqui.")
            return True
        
        # Atalho direção direta: "norte", "sul", "leste", "oeste"
        if t in ("norte", "sul", "leste", "oeste", "nordeste", "noroeste", "sudeste", "sudoeste"):
            if self.cena_atual and self.cena_atual.get("conexoes", {}).get(t):
                self.ir_para(self.cena_atual["conexoes"][t])
            else:
                self.log(f"⚠️  Não tem saída pra {t}.")
            return True
        
        # Examinar/olhar: "examino o pedestal", "olho a porta", "examinar", "olhar", "inspecionar", "vasculhar", "procurar"
        if re.search(r'\b(examin\w*|olhar|olho|inspecion|procurar)\b', t):
            self.vasculhar()
            return True
        
        # Falar com NPC: "falo com", "falar com", "conversar com", "dialogar"
        if re.search(r'\b(falar|falo|conversar|dialogar)\b', t):
            self.falar_npc()
            return True
        
        # Abrir: "abro o bau", "abrir baú", "abro a porta", "abre"
        if re.search(r'\b(abr[io]|abre|abrir)\b', t):
            self.vasculhar()  # trata como vasculhar
            return True
        
        # Pegar item: "pego a espada", "pegar poçao", "pego item", "apanhar"
        if re.search(r'\b(peg[ao]|pegar|apanhar)\b', t):
            self.log("💡 Use o botão de ações ou digite 'vasculhar' pra ver itens na sala.")
            return True
        
        # Ajudar/socorrer NPC
        if re.search(r'\b(ajudar|socorrer|curar)\b', t):
            self.falar_npc()
            return True
        
        return False

    def _interpretar_com_ia(self, texto: str):
        """
        Manda o texto pra OpenAI interpretar como intenção de jogo,
        executa a mecânica correspondente, e narra o resultado.
        Fallback gracioso se IA off.
        RODA EM THREAD SEPARADA para não travar a UI.
        """
        import threading
        
        def _worker():
            try:
                from ai_engine import interpretar_acao_json, narrar_ambiente
                import asyncio
                
                contexto_sala = (
                    f"Jogador: {self.jogador.nome} ({self.jogador.classe}) "
                    f"HP={self.jogador.hp_atual}/{self.jogador.hp_maximo}. "
                    f"Cena atual: {self.cena_atual['nome_sala'] if self.cena_atual else '???'}. "
                    f"Inimigo presente: {self.inimigo_atual['nome'] if self.inimigo_atual else 'nenhum'}."
                )
                descricao_sala = self.cena_atual.get("descricao_visual", "") if self.cena_atual else ""
                
                # Roda async numa nova event loop na thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                resultado = loop.run_until_complete(interpretar_acao_json(texto, contexto_sala))
                intencao = resultado.get("intencao", "OUTRO").upper()
                
                # Agenda execução da mecânica na UI thread
                self.after(0, lambda: self._processar_ia_resultado(texto, resultado, intencao, descricao_sala))
                
                loop.close()
                
            except Exception as e:
                self.after(0, lambda: self.log(f"⚠️ IA não disponível: {e}"))
                self.after(0, lambda: self.log(f"💡 (ação livre '{texto}' — narrador local ativado)"))
                # Fallback para narrador local
                self.after(0, lambda: self._narrador_local_fallback(texto))
        
        threading.Thread(target=_worker, daemon=True).start()

    def _narrador_local_fallback(self, texto: str):
        """Fallback narrador local quando IA falha."""
        import random
        acao_lower = texto.lower()
        jogador = self.jogador.nome
        descricao_sala = self.cena_atual.get("descricao_visual", "") if self.cena_atual else ""
        
        if any(w in acao_lower for w in ["examin", "olhar", "inspecion", "procurar", "vasculhar"]):
            templates = [
                f"{jogador} examina os arredores com atenção. {descricao_sala[:200]}... Nada de imediato chama a atenção, mas o instinto diz que há mais aqui.",
                f"Os olhos de {jogador} percorrem a sala. {descricao_sala[:200]}... Cada detalhe pode esconder uma pista ou perigo.",
            ]
        elif any(w in acao_lower for w in ["falar", "conversar", "dialogar"]):
            templates = [f"{jogador} inicia uma conversa. As palavras ecoam na {self.cena_atual['nome_sala'] if self.cena_atual else 'sala'}..."]
        elif any(w in acao_lower for w in ["abrir", "abro", "abre"]):
            templates = [f"{jogador} força a abertura. Range de madeira, poeira sobe... révélando o que há dentro."]
        elif any(w in acao_lower for w in ["pegar", "apanhar"]):
            templates = [f"{jogador} estende a mão e agarra o objeto. Peso familiar, promessa de utilidade."]
        elif any(w in acao_lower for w in ["norte", "sul", "leste", "oeste", "vou", "ir ", "andar"]):
            templates = [f"{jogador} segue pelo corredor. A névoa envolve os passos, a antecipação cresce."]
        elif any(w in acao_lower for w in ["atacar", "ataque", "bater", "golpear"]):
            templates = [f"{jogador} avança com {self.jogador.arma_equipada} em punho! O ar corta-se com o movimento."]
        else:
            templates = [
                f"{jogador} {texto.lower()}. O destino observa, silencioso.",
                f"A ação de {jogador} — '{texto}' — ecoa na {self.cena_atual['nome_sala'] if self.cena_atual else 'sala'}. Algo muda, imperceptível.",
            ]
        
        self.log(f"📖 {random.choice(templates)}")

    def _processar_ia_resultado(self, texto: str, resultado: dict, intencao: str, descricao_sala: str):
        """Processa resultado da IA na UI thread (chamado via self.after)."""
        self.log(f"🧠 [IA] intenção={intencao}")
        
        # ── MECÂNICA: age conforme a intenção ──
        if intencao == "NAVEGAR" and resultado.get("direcao"):
            if self.cena_atual and self.cena_atual.get("conexoes", {}).get(resultado["direcao"]):
                self.ir_para(self.cena_atual["conexoes"][resultado["direcao"]])
            else:
                self.log(f"⚠️  IA pediu pra ir pro {resultado['direcao']}, mas não tem saída.")
        elif intencao in ("COMBATE", "MANOBRA") and self.inimigo_atual:
            self.atacar()
        elif intencao == "DESCANSAR":
            self.descansar()
        elif intencao in ("INTERACAO", "OUTRO"):
            if intencao == "INTERACAO" and self.inimigo_atual is None and "fugir" not in texto.lower():
                self.vasculhar()
        
        # ── NARRATIVA: roda em thread separada ──
        self._gerar_narrativa_async(texto, descricao_sala)

    def _gerar_narrativa_async(self, texto: str, descricao_sala: str):
        """Gera narrativa em background thread."""
        import threading
        
        def _worker():
            try:
                from ai_engine import narrar_ambiente
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                narracao = loop.run_until_complete(narrar_ambiente(self.jogador.nome, texto, descricao_sala))
                loop.close()
                self.after(0, lambda: self.log(f"📖 {narracao}"))
            except Exception:
                pass  # se narrativa falhar, só segue
        
        threading.Thread(target=_worker, daemon=True).start()

    # ── AÇÕES ──────────────────────────────────────────────────────────────
    def _log_combate(self, linhas: list):
        """Log formatado estilo bloco de combate."""
        self.log("━" * 16)
        for linha in linhas:
            self.log(linha)
        self.log("━" * 16)

    def _formatar_resultado_combate(self, res, inimigo_nome: str):
        """Formata TurnoCombateResult pro layout limpo."""
        # Iniciativa (extraída da narrativa se houver, ou rolada)
        ini_jog = random.randint(1, 20) + self.jogador.mod_dex
        ini_inim = random.randint(1, 20) + 2
        self._log_combate([f"⚡ INICIATIVA: {self.jogador.nome} {ini_jog} vs {inimigo_nome} {ini_inim}"])

        # Ataque do jogador - extrai da narrativa
        narrativa = res.narrativa
        
        # Busca linhas do ataque do jogador
        import re
        # Padrão: 🎲 Dados: d20=[...] -> X vs CA Y ✅
        # ou: ⚔️ Surto de Ação: d20=... -> ... vs CA ... ✅
        atacar_match = re.search(r'(🎲 Dados:|⚔️ Surto de Ação:).*?(?:✅|❌)', narrativa)
        if atacar_match:
            linha_atk = atacar_match.group(0)
            # Limpa tags HTML
            linha_atk = linha_atk.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
            self._log_combate([linha_atk])
            
            # Próxima linha costuma ser o dano
            resto = narrativa[atacar_match.end():]
            dano_match = re.search(r'(💥 Dano:|💥 CRÍTICO! Dano:).*?(?=\\n|$)', resto)
            if dano_match:
                linha_dano = dano_match.group(0).replace('<b>', '').replace('</b>', '')
                self._log_combate([linha_dano])

        # Revide do inimigo
        revide_match = re.search(r'⚠️ ATAQUE INIMIGO:.*?(?=\\n\\n|\\n🤢|\\n🩸 Veneno|$)', narrativa, re.DOTALL)
        if revide_match:
            revide_texto = revide_match.group(0)
            # Limpa tags HTML e divide em linhas
            linhas_revide = []
            for linha in revide_texto.split('\n'):
                linha = linha.strip()
                if linha:
                    linha = linha.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
                    # Prefixa ataques com ⚔️
                    if 'Atk' in linha and ('Hit' in linha or 'Miss' in linha):
                        linha = f"⚔️ {linha}"
                    elif 'ATAQUE INIMIGO' in linha:
                        linha = f"⚠️ {linha}"
                    elif 'Dano total recebido' in linha:
                        linha = f"🩸 {linha}"
                    elif 'Fúria reduziu' in linha:
                        linha = f"🛡️ {linha}"
                    elif 'Envenenado' in linha:
                        linha = f"🤢 {linha}"
                    elif 'Caíste' in linha or 'inconsciente' in linha.lower():
                        linha = f"💀 {linha}"
                    elif 'Veneno:' in linha:
                        linha = f"🤢 {linha}"
                    linhas_revide.append(linha)
            if linhas_revide:
                self._log_combate(linhas_revide)

        # Level up / Vitória - extrai do final
        vitoria_match = re.search(r'(🏆|✨).*(?:XP|PO|LEVEL UP|Nv)', narrativa)
        if vitoria_match:
            vitoria_texto = vitoria_match.group(0).replace('<b>', '').replace('</b>', '')
            self._log_combate([vitoria_texto])

    def atacar(self):
        if not self.inimigo_atual:
            self.log("⚠️  Não há inimigo para atacar aqui.")
            return

        # Usa o motor completo do combat_logic (mesmo do Telegram)
        from combat_logic import resolver_turno_combate
        
        inimigo = self.inimigo_atual
        hp_grupo = self.hp_grupo_inimigo
        hp_max = inimigo.get("hp", 1)
        qtd_vivos = max(1, hp_grupo // hp_max + (1 if hp_grupo % hp_max > 0 else 0))
        
        # Chama resolver_turno_combate com todos os parâmetros
        res = resolver_turno_combate(
            jogador=self.jogador,
            inimigo_ca=inimigo["ca"],
            inimigo_ataque_str=inimigo.get("ataque", "+0"),
            inimigo_nome=inimigo["nome"],
            hp_alvo_atual=hp_grupo,
            hp_max_inimigo=hp_max,
            qtd_ataques_inimigo=qtd_vivos,
            texto_acao="atacar",
            estilo=None,
            inimigo_resistencias=inimigo.get("resistencias", []),
            inimigo_vulnerabilidades=inimigo.get("vulnerabilidades", []),
            inimigo_imunidades=inimigo.get("imunidades", []),
            inimigo_primeiro=False,
            inimigo_dano_str=inimigo.get("dano", "1d4"),
        )
        
        # Atualiza HP do grupo inimigo
        self.hp_grupo_inimigo = max(0, res.hp_alvo_restante)
        
        # Formata e loga
        self._formatar_resultado_combate(res, inimigo["nome"])
        
        # Sincroniza status do jogador (HP, status_efeitos já modificados in-place)
        self.jogador.status_efeitos = list(self.jogador.status_efeitos)
        
        # Verifica vitória
        if self.hp_grupo_inimigo <= 0:
            # Desktop é single-player: 100% do loot vai pro jogador
            xp_rec = inimigo.get("xp_recompensa", 25)
            ouro_rec = inimigo.get("ouro_recompensa", 5)
            self.jogador.xp += xp_rec
            self.jogador.gold += ouro_rec
            self.estado_salas[f"derrotado_{inimigo['nome']}"] = True
            
            from game_helpers import aplicar_level_up
            niveis = aplicar_level_up(self.jogador)
            if niveis > 0:
                self._log_combate([f"✨ LEVEL UP! Agora és Nv {self.jogador.nivel}! HP={self.jogador.hp_maximo}"])
            
            self._log_combate([f"", f"🏆 VITÓRIA! Recebes {xp_rec} XP e {ouro_rec} PO.", ""])
            
            self.inimigo_atual = None
            self._atualizar_botoes()
        
        # Verifica morte/inconsciente
        if self.jogador.hp_atual <= 0 or res.estado_jogador in ("inconsciente", "morto", "estabilizado"):
            if res.estado_jogador == "morto":
                from game_helpers import aplicar_morte_resgate
                class _FakeCampanha:
                    cena_atual = None
                    em_combate = True
                campanha = _FakeCampanha()
                narrativa = aplicar_morte_resgate(self.jogador, campanha)
                self.log(narrativa)
            self.ir_para("carvalhal")
            self.jogador.hp_atual = self.jogador.hp_maximo
        
        self._atualizar_status()
        self._auto_save(silencioso=True)

    # Remove _revide_inimigo_formatado (não usado mais)

    def fugir(self):
        """Fuga do combate: 1d6+2 ataque de oportunidade (D&D 5e), depois volta pra sala anterior."""
        if not self.cena_atual or not self.cena_atual.get("conexoes"):
            self.log("🛑 Não tens para onde recuar!")
            return
        if not self.inimigo_atual:
            self.log("🏃 Não há inimigo. Tu simplesmente te moves.")
            primeira = list(self.cena_atual["conexoes"].values())[0]
            self.ir_para(primeira)
            return

        # 1. Rola ataque de oportunidade (canônico)
        from game_helpers import resolver_fuga
        levou_dano, narrativa = resolver_fuga(self.jogador, self.inimigo_atual["nome"], self.inimigo_atual)
        self.log(narrativa)

        # 2. Se morreu, vai pra carvalhal via morte/resgate
        if self.jogador.hp_atual == 0:
            from game_helpers import aplicar_morte_resgate
            class _FakeC:
                cena_atual = self.cena_atual["cod_sala"]
                em_combate = True
            aplicar_morte_resgate(self.jogador, _FakeC())
            self.ir_para("carvalhal")
            self.jogador.hp_atual = self.jogador.hp_maximo
            return

        # 3. Move pra sala anterior (primeira conexão)
        primeira = list(self.cena_atual["conexoes"].values())[0]
        self.log(f"🏃 Foges para {primeira}!")
        self.ir_para(primeira)

    def vasculhar(self):
        self.log(f"👁️  Vasculhaste a sala. Nada de especial por aqui (no protótipo, loot fixo virá do DB).")

    def falar_npc(self):
        # Filtra NPCs por cena atual (só mostra quem tá AQUI)
        if not self.cena_atual:
            self.log("💬 Não há ninguém interessante para conversar aqui.")
            return
        npc = get_npc_da_cena(self.cena_atual["cod_sala"])
        if npc:
            self.npc_atual = npc  # guarda pra ações de diálogo
            self.log(f"💬 {npc['nome']}:")
            self.log(f"   {npc.get('dialogo_inicial', '...')}")
            # Mostra opções de diálogo como botões de ação
            self._mostrar_opcoes_dialogo_npc(npc)
        else:
            self.log(f"💬 Não há ninguém interessante para conversar em {self.cena_atual['nome_sala']}.")

    def _mostrar_opcoes_dialogo_npc(self, npc: dict):
        """Mostra opções de diálogo do NPC como botões de ação."""
        self.botoes_acoes_frame.clear()
        for i, opcao in enumerate(npc.get("opcoes_dialogo", [])):
            self.botoes_acoes_frame.add_button(
                f"💬 {opcao}",
                lambda o=opcao: self._processar_opcao_dialogo(o, npc),
                width=160
            )

    def _processar_opcao_dialogo(self, opcao: str, npc: dict):
        """Processa a opção de diálogo escolhida pelo jogador."""
        self.log(f"💬 > {opcao}")
        
        opcao_lower = opcao.lower()
        
        # Mapeia opções genéricas
        if "bebida" in opcao_lower or "cerveja" in opcao_lower or "hidromel" in opcao_lower:
            self.log(f"💬 {npc['nome']}: Aqui está, jovem aventureiro. Isso vai te custar 2 PO.")
            if self.jogador.gold >= 2:
                self.jogador.gold -= 2
                self.log("🍻 Você bebe e sente o calor subir. HP +2 temporário!")
                self.jogador.hp_atual = min(self.jogador.hp_atual + 2, self.jogador.hp_maximo)
            else:
                self.log("⚠️  Você não tem ouro suficiente!")
                
        elif "rumor" in opcao_lower or "fofoca" in opcao_lower or "notícia" in opcao_lower:
            self.log(f"💬 {npc['nome']}: Dizem que tem kobolds na cidadela ao norte... e algo mais sinistro nas profundezas. Cuidado com a árvore retorcida.")
            if "rumores" not in self.estado_salas.get("carvalhal", {}):
                if "carvalhal" not in self.estado_salas:
                    self.estado_salas["carvalhal"] = {}
                self.estado_salas["carvalhal"]["rumores_ouvidos"] = True
                
        elif "quarto" in opcao_lower or "hosped" in opcao_lower or "dormir" in opcao_lower:
            self.log(f"💬 {npc['nome']}: quartinho no andar de cima, 5 PO a noite. Café da manhã incluso.")
            if self.jogador.gold >= 5:
                self.jogador.gold -= 5
                self.log("🛏️  Você dorme bem. HP e slots de magia restaurados!")
                self.jogador.hp_atual = self.jogador.hp_maximo
                self.jogador.slots_magia = self.jogador.slots_magia_max
                self.jogador.hit_dice_atual = self.jogador.hit_dice_max
            else:
                self.log("⚠️  Ouro insuficiente.")
                
        elif "comida" in opcao_lower or "ensopado" in opcao_lower or "comer" in opcao_lower:
            self.log(f"💬 {npc['nome']}: Ensopado de javali, 3 PO. Recupera 1d8+2 HP.")
            if self.jogador.gold >= 3:
                self.jogador.gold -= 3
                from game_helpers import rolar_dano
                cura = rolar_dano("1d8+2")[0]
                self.jogador.hp_atual = min(self.jogador.hp_atual + cura, self.jogador.hp_maximo)
                self.log(f"🍲 Você come e recupera {cura} HP. HP atual: {self.jogador.hp_atual}/{self.jogador.hp_maximo}")
            else:
                self.log("⚠️  Sem ouro.")
                
        elif "sair" in opcao_lower or "tchau" in opcao_lower or "adeus" in opcao_lower:
            self.log(f"💬 {npc['nome']}: Volte sempre, aventureiro. A lareira tá sempre acesa.")
            self.botoes_acoes_frame.clear()
            self.npc_atual = None
            
        else:
            self.log(f"💬 {npc['nome']}: Hmm... não entendi. Tenta de novo?")

    def ver_inventario(self):
        if not self.jogador.inventario:
            self.log("🎒 Inventário vazio.")
            return
        itens = "\n   • ".join(self.jogador.inventario)
        self.log(f"🎒 Inventário de {self.jogador.nome}:\n   • {itens}")

    def ver_status(self):
        j = self.jogador
        self.log(
            f"📊 STATUS DE {j.nome.upper()} ({j.classe} Nv {j.nivel})\n"
            f"   ❤️  HP: {j.hp_atual}/{j.hp_maximo}    🛡️  CA: {j.modificador_defesa}    ⭐  XP: {j.xp}\n"
            f"   STR {j.str_val}({j.mod_str:+d})  DEX {j.dex_val}({j.mod_dex:+d})  CON {j.con_val}({j.mod_con:+d})  "
            f"INT {j.int_val}({j.mod_int:+d})  WIS {j.wis_val}({j.mod_wis:+d})  CHA {j.cha_val}({j.mod_cha:+d})\n"
            f"   ⚔️  Arma: {j.arma_equipada} ({j.dano_dado}+{j.mod_dano})    🛡️  Armadura: {j.armadura_equipada}\n"
            f"   🪙  Ouro: {j.gold} PO"
        )

    # ── LOJA ───────────────────────────────────────────────────────────────
    PRECO_VENDA_PCT = 0.5  # vende por 50% do preço

    def loja_popup(self):
        """Abre popup da loja. Só funciona em Carvalhal (Vila)."""
        if not self.cena_atual or self.cena_atual.get("cod_sala") != "carvalhal":
            self.log("💰 A loja só funciona na Vila de Carvalhal. Volta pra lá primeiro!")
            return

        popup = ctk.CTkToplevel(self)
        popup.title("💰 Loja de Carvalhal")
        popup.geometry("600x650")
        popup.transient(self)
        popup.grab_set()

        ctk.CTkLabel(
            popup,
            text=f"💰 LOJA DE CARVALHAL\n🪙 Seu ouro: {self.jogador.gold} PO",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=10)

        # Tabview pra Comprar / Vender
        tabview = ctk.CTkTabview(popup, width=560, height=480)
        tabview.pack(padx=10, pady=5, fill="both", expand=True)
        tab_comprar = tabview.add("🛒 Comprar")
        tab_vender = tabview.add("💸 Vender")

        # ── ABA COMPRAR ──
        ctk.CTkLabel(tab_comprar, text="Itens disponíveis (clique pra comprar):", anchor="w").pack(fill="x", padx=10, pady=(10, 5))
        scroll_comprar = ctk.CTkScrollableFrame(tab_comprar, height=380)
        scroll_comprar.pack(fill="both", expand=True, padx=10, pady=5)

        # Agrupa por tipo
        tipos_ordem = ["arma", "armadura", "pocao", "equipamento"]
        for tipo in tipos_ordem:
            itens_tipo = [(n, d) for n, d in LOJA_CARVALHAL.items() if d.get("tipo") == tipo]
            if not itens_tipo:
                continue
            emoji_tipo = {"arma": "⚔️", "armadura": "🛡️", "pocao": "🧪", "equipamento": "🎒"}.get(tipo, "")
            ctk.CTkLabel(
                scroll_comprar,
                text=f"{emoji_tipo} {tipo.upper()}S",
                font=ctk.CTkFont(weight="bold"),
                anchor="w",
            ).pack(fill="x", padx=5, pady=(10, 2))
            for nome, dados in itens_tipo:
                preco = dados.get("preco", 0)
                desc = dados.get("descricao", "")
                pode_comprar = self.jogador.gold >= preco
                cor = "#1B5E20" if pode_comprar else "#424242"
                texto = f"{nome} — {preco} PO"
                if not pode_comprar:
                    texto += " (caro)"
                ctk.CTkButton(
                    scroll_comprar,
                    text=texto,
                    anchor="w",
                    fg_color=cor,
                    state="normal" if pode_comprar else "disabled",
                    command=lambda n=nome, p=preco, d=dados: self._comprar_item(n, p, d, popup),
                ).pack(fill="x", padx=5, pady=1)

        # ── ABA VENDER ──
        ctk.CTkLabel(tab_vender, text="Seu inventário (clique pra vender por 50%):", anchor="w").pack(fill="x", padx=10, pady=(10, 5))
        scroll_vender = ctk.CTkScrollableFrame(tab_vender, height=380)
        scroll_vender.pack(fill="both", expand=True, padx=10, pady=5)
        inventario = self.jogador.inventario or []
        if not inventario:
            ctk.CTkLabel(scroll_vender, text="(inventário vazio)").pack(padx=10, pady=5)
        for item in inventario:
            # Procura o preço base na loja
            preco_base = 0
            for nome_loja, dados_loja in LOJA_CARVALHAL.items():
                if item.lower() in nome_loja.lower() or nome_loja.lower() in item.lower():
                    preco_base = dados_loja.get("preco", 0)
                    break
            preco_venda = max(1, int(preco_base * self.PRECO_VENDA_PCT)) if preco_base else 1
            ctk.CTkButton(
                scroll_vender,
                text=f"{item} → +{preco_venda} PO",
                anchor="w",
                fg_color="#B71C1C",
                hover_color="#C62828",
                command=lambda i=item, p=preco_venda: self._vender_item(i, p, popup),
            ).pack(fill="x", padx=5, pady=1)

        # Fechar
        ctk.CTkButton(popup, text="❌ Fechar", command=popup.destroy).pack(pady=10)

    def _comprar_item(self, nome: str, preco: int, dados: dict, popup):
        """Compra um item, deduz ouro, adiciona ao inventário."""
        if self.jogador.gold < preco:
            self.log(f"❌ Ouro insuficiente! Precisa de {preco} PO, tem {self.jogador.gold}.")
            return
        self.jogador.gold -= preco
        if not self.jogador.inventario:
            self.jogador.inventario = []
        self.jogador.inventario.append(nome)
        self.log(f"🛒 Comprou {nome} por {preco} PO! (restam {self.jogador.gold} PO)")
        self._atualizar_status()
        self._auto_save(silencioso=True)
        # fecha e reabre pra atualizar a lista
        popup.destroy()
        self.loja_popup()

    def _vender_item(self, item: str, preco_venda: int, popup):
        """Vende um item do inventário, adiciona ouro."""
        if item not in self.jogador.inventario:
            self.log(f"❌ {item} não tá no inventário.")
            return
        self.jogador.inventario.remove(item)
        self.jogador.gold += preco_venda
        self.log(f"💸 Vendeu {item} por {preco_venda} PO! (total: {self.jogador.gold} PO)")
        self._atualizar_status()
        self._auto_save(silencioso=True)
        popup.destroy()
        self.loja_popup()

    def equipar_popup(self):
        """Abre um popup com lista de armas e armaduras do inventário."""
        # Coleta armas e armaduras do inventário
        inventario = self.jogador.inventario or []
        armas = []
        armaduras = []
        for item in inventario:
            # Procura no LOJA_CARVALHAL por match
            for nome_loja, dados in LOJA_CARVALHAL.items():
                if item.lower() in nome_loja.lower() or nome_loja.lower() in item.lower():
                    if dados.get("tipo") == "arma":
                        armas.append((nome_loja, dados))
                    elif dados.get("tipo") == "armadura":
                        armaduras.append((nome_loja, dados))
                    break

        # Cria janela modal
        popup = ctk.CTkToplevel(self)
        popup.title("🗡️ Equipar")
        popup.geometry("500x600")
        popup.transient(self)
        popup.grab_set()

        ctk.CTkLabel(popup, text="🗡️ EQUIPAMENTO", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        # ── ARMAS ──
        ctk.CTkLabel(popup, text=f"⚔️ ARMAS ({len(armas)})", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10, 0))
        armas_frame = ctk.CTkScrollableFrame(popup, height=180)
        armas_frame.pack(fill="x", padx=20, pady=5)
        if not armas:
            ctk.CTkLabel(armas_frame, text="(nenhuma arma no inventário)").pack(padx=10, pady=5)
        for nome, dados in armas:
            equipado = " (EQUIPADO)" if nome.lower() in self.jogador.arma_equipada.lower() else ""
            btn = ctk.CTkButton(
                armas_frame,
                text=f"{nome} — {dados.get('dano', '?')} {dados.get('descricao', '')[:40]}{equipado}",
                anchor="w",
                fg_color="#1B5E20" if equipado else None,
                command=lambda n=nome: self._equipar_arma(n, popup),
            )
            btn.pack(fill="x", padx=5, pady=2)

        # ── ARMADURAS ──
        ctk.CTkLabel(popup, text=f"🛡️ ARMADURAS ({len(armaduras)})", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10, 0))
        armaduras_frame = ctk.CTkScrollableFrame(popup, height=180)
        armaduras_frame.pack(fill="x", padx=20, pady=5)
        if not armaduras:
            ctk.CTkLabel(armaduras_frame, text="(nenhuma armadura no inventário)").pack(padx=10, pady=5)
        for nome, dados in armaduras:
            equipado = " (EQUIPADO)" if nome.lower() in self.jogador.armadura_equipada.lower() else ""
            btn = ctk.CTkButton(
                armaduras_frame,
                text=f"{nome} — CA base {dados.get('ca_base', '?')} {dados.get('subtipo', '')} {equipado}",
                anchor="w",
                fg_color="#1B5E20" if equipado else None,
                command=lambda n=nome: self._equipar_armadura(n, popup),
            )
            btn.pack(fill="x", padx=5, pady=2)

        # Botão fechar
        ctk.CTkButton(popup, text="❌ Fechar", command=popup.destroy).pack(pady=10)

    def _equipar_arma(self, nome_arma: str, popup):
        """Troca a arma equipada e recalcula modificadores."""
        try:
            mod_ataque, nome_oficial, dano_dado = calcular_modificadores_ataque(self.jogador, nome_arma)
            self.jogador.arma_equipada = nome_oficial
            self.jogador.dano_dado = dano_dado
            self.jogador.modificador_ataque = mod_ataque + self.jogador.proficiencia
            self.jogador.mod_dano = mod_ataque
            self.log(f"⚔️ Equipou {nome_oficial}! Dano {dano_dado}+{mod_ataque}, ataque +{self.jogador.modificador_ataque}")
            self._atualizar_status()
            self._auto_save(silencioso=True)
            popup.destroy()
        except Exception as e:
            self.log(f"❌ Erro ao equipar: {e}")

    def _equipar_armadura(self, nome_armadura: str, popup):
        """Troca a armadura equipada e recalcula CA."""
        try:
            ca_final = calcular_ca_final(self.jogador, nome_armadura)
            self.jogador.armadura_equipada = nome_armadura
            self.jogador.modificador_defesa = ca_final
            self.log(f"🛡️ Equipou {nome_armadura}! CA = {ca_final}")
            self._atualizar_status()
            self._auto_save(silencioso=True)
            popup.destroy()
        except Exception as e:
            self.log(f"❌ Erro ao equipar: {e}")

    # ── WIZARD DE CRIAÇÃO DE PERSONAGEM ─────────────────────────────────────
    def criar_personagem_wizard(self):
        """Abre wizard de criação. Equivalente ao /criar do Telegram."""
        # Estado do wizard
        self._wizard = {
            "step": 0,
            "dados": {},
        }
        # Janela modal
        self._wizard_window = ctk.CTkToplevel(self)
        self._wizard_window.title("🧙 Criar Personagem")
        self._wizard_window.geometry("500x600")
        self._wizard_window.transient(self)
        self._wizard_window.grab_set()

        # Frame principal que troca conteúdo por step
        self._wizard_frame = ctk.CTkFrame(self._wizard_window)
        self._wizard_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._wizard_render_step()

    def _wizard_render_step(self):
        """Renderiza o step atual do wizard."""
        # Limpa frame
        for w in self._wizard_frame.winfo_children():
            w.destroy()

        step = self._wizard["step"]
        dados = self._wizard["dados"]

        if step == 0:  # Nome
            ctk.CTkLabel(self._wizard_frame, text="🧙 Qual será o nome do herói?", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
            self._wizard_entry = ctk.CTkEntry(self._wizard_frame, placeholder_text="Ex: Aragorn, Lyra, Thorin...", width=300)
            self._wizard_entry.pack(pady=10)
            self._wizard_entry.focus()
            self._wizard_entry.bind("<Return>", lambda e: self._wizard_next())
            ctk.CTkButton(self._wizard_frame, text="Próximo →", command=self._wizard_next).pack(pady=10)

        elif step == 1:  # Sexo
            ctk.CTkLabel(self._wizard_frame, text="Qual é o sexo/gênero do herói?", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
            for sexo in ["Masculino", "Feminino", "Não Binário"]:
                ctk.CTkButton(self._wizard_frame, text=sexo, width=200, command=lambda s=sexo: self._wizard_pick("sexo", s)).pack(pady=3)

        elif step == 2:  # Raça
            ctk.CTkLabel(self._wizard_frame, text="Escolha sua Raça:", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
            racas = [
                ["Humano", "Elfo", "Anão"],
                ["Halfling", "Draconato", "Meio-Orc"],
                ["Meio-Elfo", "Tiefling", "Gnomo"],
            ]
            for linha in racas:
                row_frame = ctk.CTkFrame(self._wizard_frame, fg_color="transparent")
                row_frame.pack(pady=3)
                for r in linha:
                    ctk.CTkButton(row_frame, text=r, width=140, command=lambda x=r: self._wizard_pick("raca", x)).pack(side="left", padx=3)

        elif step == 3:  # Classe
            ctk.CTkLabel(self._wizard_frame, text="Escolha sua Classe:", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
            classes = [
                ["Bárbaro", "Bardo", "Bruxo"],
                ["Clérigo", "Druida", "Feiticeiro"],
                ["Guerreiro", "Ladino", "Mago"],
                ["Monge", "Paladino", "Patrulheiro"],
            ]
            for linha in classes:
                row_frame = ctk.CTkFrame(self._wizard_frame, fg_color="transparent")
                row_frame.pack(pady=3)
                for c in linha:
                    ctk.CTkButton(row_frame, text=c, width=120, command=lambda x=c: self._wizard_pick("classe", x)).pack(side="left", padx=2)

        elif step == 4:  # Background
            ctk.CTkLabel(self._wizard_frame, text="Escolha seu Background:", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
            bgs = [
                ["Acólito", "Criminoso"],
                ["Herói do Povo", "Nobre"],
                ["Sábio", "Soldado"],
                ["Forasteiro"],
            ]
            for linha in bgs:
                row_frame = ctk.CTkFrame(self._wizard_frame, fg_color="transparent")
                row_frame.pack(pady=3)
                for b in linha:
                    ctk.CTkButton(row_frame, text=b, width=160, command=lambda x=b: self._wizard_pick("background", x)).pack(side="left", padx=3)

        elif step == 5:  # Atributos (rolar + distribuir)
            rolagens = sorted([self._rolar_4d6_drop_lowest() for _ in range(6)], reverse=True)
            self._wizard["dados"]["atributos_rolados"] = rolagens
            exemplo = " ".join(map(str, rolagens))
            ctk.CTkLabel(
                self._wizard_frame,
                text=f"🎲 Seus Dados: {', '.join(map(str, rolagens))}",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(pady=10)
            ctk.CTkLabel(
                self._wizard_frame,
                text="Distribua esses valores nos atributos!\nOrdem: STR DEX CON INT WIS CHA",
                font=ctk.CTkFont(size=12),
            ).pack(pady=5)
            ctk.CTkLabel(
                self._wizard_frame,
                text=f"Exemplo: {exemplo}",
                font=ctk.CTkFont(size=11),
            ).pack(pady=5)
            self._wizard_entry = ctk.CTkEntry(self._wizard_frame, placeholder_text="15 14 13 12 10 8", width=300)
            self._wizard_entry.pack(pady=10)
            self._wizard_entry.focus()
            self._wizard_entry.bind("<Return>", lambda e: self._wizard_next())
            ctk.CTkButton(self._wizard_frame, text="Próximo →", command=self._wizard_next).pack(pady=10)

        elif step == 6:  # Revisão final
            self._wizard_render_review()

        # Botão voltar (sempre visível depois do step 0)
        if step > 0:
            ctk.CTkButton(
                self._wizard_frame,
                text="← Voltar",
                fg_color="gray",
                command=self._wizard_back,
            ).pack(side="bottom", pady=10)

    def _wizard_pick(self, field: str, value: str):
        """Usado pelos botões de seleção (sexo, raca, classe, background)."""
        self._wizard["dados"][field] = value
        self._wizard["step"] += 1
        self._wizard_render_step()

    def _wizard_next(self):
        """Usado pelos campos de texto (nome, atributos)."""
        if self._wizard["step"] == 0:  # nome
            nome = self._wizard_entry.get().strip()
            if not nome:
                return
            self._wizard["dados"]["nome"] = nome
        elif self._wizard["step"] == 5:  # atributos
            texto = self._wizard_entry.get().strip()
            partes = texto.replace(",", " ").split()
            if len(partes) != 6:
                return
            try:
                val = [int(p) for p in partes]
            except ValueError:
                return
            self._wizard["dados"]["atributos"] = val
        self._wizard["step"] += 1
        self._wizard_render_step()

    def _wizard_back(self):
        if self._wizard["step"] > 0:
            self._wizard["step"] -= 1
            self._wizard_render_step()

    def _wizard_render_review(self):
        """Step final: mostra resumo e pede confirmação."""
        dados = self._wizard["dados"]
        # Calcula tudo
        jogador_dict = self._wizard_calcular_stats(dados)
        # Resumo
        texto = (
            f"✨ {jogador_dict['nome']} ({jogador_dict['raca']} {jogador_dict['classe']})\n"
            f"Sexo: {jogador_dict['sexo']} | Background: {jogador_dict['background']}\n\n"
            f"HP: {jogador_dict['hp_atual']}/{jogador_dict['hp_maximo']} | CA: {jogador_dict['modificador_defesa']}\n"
            f"Arma: {jogador_dict['arma_equipada']} ({jogador_dict['dano_dado']}+{jogador_dict['mod_dano']})\n"
            f"Armadura: {jogador_dict['armadura_equipada']}\n"
            f"Inventário: {', '.join(jogador_dict['inventario'])}\n\n"
            f"STR {jogador_dict['str_val']}({jogador_dict['mod_str']:+d})  "
            f"DEX {jogador_dict['dex_val']}({jogador_dict['mod_dex']:+d})  "
            f"CON {jogador_dict['con_val']}({jogador_dict['mod_con']:+d})\n"
            f"INT {jogador_dict['int_val']}({jogador_dict['mod_int']:+d})  "
            f"WIS {jogador_dict['wis_val']}({jogador_dict['mod_wis']:+d})  "
            f"CHA {jogador_dict['cha_val']}({jogador_dict['mod_cha']:+d})"
        )
        ctk.CTkLabel(self._wizard_frame, text=texto, justify="left", font=ctk.CTkFont(size=12)).pack(pady=15)
        ctk.CTkButton(self._wizard_frame, text="🎉 Confirmar e começar!", fg_color="#2E7D32", hover_color="#1B5E20", command=lambda: self._wizard_confirmar(jogador_dict)).pack(pady=10)

    def _wizard_confirmar(self, jogador_dict: dict):
        """Cria o personagem: substitui o save local e reinicia."""
        from save_manager import save_jogador
        from pathlib import Path
        import json

        # Gera um party_id local (pra salvar no save)
        jogador_dict["party_id"] = "PTY-LOCAL"
        jogador_dict["cena_atual"] = "taverna"
        jogador_dict["cena_anterior"] = None
        jogador_dict["estado_salas"] = {}
        jogador_dict["xp"] = 0
        jogador_dict["nivel"] = 1

        # Salva no JSON local
        result = save_jogador(jogador_dict, estado_salas={})
        self.log(f"💾 Personagem criado e salvo: {jogador_dict['nome']} ({jogador_dict['classe']})")

        # Fecha wizard
        self._wizard_window.destroy()

        # Recarrega o jogador na sessão atual
        self.jogador = MockJogador(dados_db=jogador_dict)
        self._cena_inicial = "carvalhal"
        self.estado_salas = {}
        self.ir_para("carvalhal")
        self._atualizar_status()

    @staticmethod
    def _rolar_4d6_drop_lowest() -> int:
        """Rola 4d6, descarta o menor, soma os 3 maiores (D&D 5e padrão)."""
        dados = [random.randint(1, 6) for _ in range(4)]
        dados.remove(min(dados))
        return sum(dados)

    @staticmethod
    def _wizard_calcular_stats(dados: dict) -> dict:
        """
        Calcula todos os stats do personagem novo.
        Lógica canônica do main.py (lines 537-572), port pro pygame.
        """
        from ui_utils import HP_POR_CLASSE, INVENTARIO_POR_CLASSE, ARMAS_DB, BONUS_RACA

        raca = dados.get("raca", "Humano")
        bonus_raca = BONUS_RACA.get(raca, [0, 0, 0, 0, 0, 0])
        val_base = dados.get("atributos", [10, 10, 10, 10, 10, 10])
        val = [val_base[i] + bonus_raca[i] for i in range(6)]
        mods = [RPGApp._calcular_modificador_static(v) for v in val]
        classe = dados.get("classe", "Guerreiro")

        # HP e inventário
        hp_base = HP_POR_CLASSE.get(classe, 8)
        inv_lista = list(INVENTARIO_POR_CLASSE.get(classe, ["Adaga", "Tochas", "Rações"]))

        # CA inicial
        ca_inicial = 10 + mods[1]
        if classe in ["Guerreiro", "Paladino", "Clérigo"]:
            ca_inicial = 18
        elif classe in ["Patrulheiro", "Ladino", "Bárbaro"]:
            ca_inicial = 11 + mods[1]

        # Arma e armadura iniciais
        arma_inicial = next(
            (item for item in inv_lista if any(a.lower() in item.lower() for a in ARMAS_DB.keys())),
            "Desarmado"
        )
        armadura_inicial = next(
            (item for item in inv_lista if any(x in item for x in ["Armadura", "Cota", "Peitoral"])),
            "Trajes Comuns"
        )
        if any("Escudo" in i for i in inv_lista):
            armadura_inicial += " & Escudo"

        # Dano por classe
        if classe == "Bárbaro":
            dano_dado = "1d12"
        elif classe in ["Guerreiro", "Paladino"]:
            dano_dado = "1d10"
        elif classe in ["Patrulheiro", "Ladino", "Clérigo", "Bardo", "Monge", "Druida", "Bruxo", "Feiticeiro", "Artífice", "Mago"]:
            dano_dado = "1d8"
        else:
            dano_dado = "1d6"

        # Mod de ataque e dano
        if classe in ["Ladino", "Bardo", "Monge", "Patrulheiro"]:
            mod_ataque = mods[1] + 2
            mod_dano = mods[1]
        else:
            mod_ataque = mods[0] + 2
            mod_dano = mods[0]

        return {
            "telefone": "local-dev",
            "nome": dados.get("nome", "Aventureiro"),
            "sexo": dados.get("sexo", "Desconhecido"),
            "raca": raca,
            "classe": classe,
            "background": dados.get("background", "Forasteiro"),
            "nivel": 1,
            "hp_maximo": hp_base + mods[2],
            "hp_atual": hp_base + mods[2],
            "str_val": val[0], "dex_val": val[1], "con_val": val[2],
            "int_val": val[3], "wis_val": val[4], "cha_val": val[5],
            "mod_str": mods[0], "mod_dex": mods[1], "mod_con": mods[2],
            "mod_int": mods[3], "mod_wis": mods[4], "mod_cha": mods[5],
            "modificador_ataque": mod_ataque,
            "modificador_defesa": ca_inicial,
            "proficiencia": 2,
            "gold": 15,
            "inventario": inv_lista,
            "arma_equipada": arma_inicial,
            "armadura_equipada": armadura_inicial,
            "slots_magia": 2,
            "slots_magia_max": 2,
            "dano_dado": dano_dado,
            "mod_dano": mod_dano,
            "status_efeitos": [],
            "hit_dice_max": 1,
            "hit_dice_atual": 1,
            "descanso_curto_disponivel": True,
        }

    @staticmethod
    def _calcular_modificador_static(valor: int) -> int:
        return (valor - 10) // 2

    def _calcular_modificador(self, valor: int) -> int:
        return (valor - 10) // 2

    def descansar(self):
        from game_helpers import aplicar_descanso
        if not self.cena_atual:
            self.log("⚠️ Não há onde descansar aqui.")
            return
        ok, narrativa = aplicar_descanso(self.jogador, self.cena_atual["cod_sala"])
        self.log(narrativa)
        if ok and self.jogador.cena_atual == "carvalhal" and self.jogador.nivel > 1:
            # se level-up rolou descanso na vila após level up, mostra
            pass
        self._atualizar_status()
        self._auto_save(silencioso=True)  # salva após descansar


# =============================================================================
# ENTRYPOINT
# =============================================================================
if __name__ == "__main__":
    app = RPGApp()
    app.mainloop()
