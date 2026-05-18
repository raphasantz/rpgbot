import random
from dataclasses import dataclass, field
from typing import Optional, List, Any

@dataclass
class ResultadoAtaqueObjeto:
    d20: int
    total_ataque: int
    acertou: bool
    critico: bool
    dano: int
    destruido: bool      # True se o objeto chegou a 0 HP neste golpe
    hp_restante: int     # HP do objeto após o ataque
    quebrou_por_forca: bool  # True se foi derruíbado pelo break_threshold
    detalhes_d20: list = field(default_factory=list)   # Guarda os dados rolados caso tenha vantagem/desvantagem

@dataclass
class ResultadoAtaque:
    d20: int
    total_ataque: int
    acertou: bool
    critico: bool
    dano: int
    detalhes_d20: list = field(default_factory=list)


def rolar_dado(lados):
    return random.randint(1, lados)


def calcular_vantagem_desvantagem(atacante_status: List[str], defensor_status: List[str], tipo_ataque: str = "melee"):
    vantagem = False
    desvantagem = False

    # --- PENALIDADES DO ATACANTE ---
    if atacante_status:
        if any(s in atacante_status for s in ["Envenenado", "Cego", "Assustado", "Caído"]):
            desvantagem = True

    # --- VANTAGENS CONTRA O DEFENSOR ---
    if defensor_status:
        if any(s in defensor_status for s in ["Cego", "Atordoado", "Paralisado"]):
            vantagem = True
        if "Caído" in defensor_status:
            if tipo_ataque == "melee":
                vantagem = True # Bater em quem está no chão com espada é fácil
            elif tipo_ataque == "distancia":
                desvantagem = True # Atirar flecha em quem está deitado é difícil (alvo menor)

    # Anulam-se mutuamente
    if vantagem and desvantagem:
        return False, False
    return vantagem, desvantagem


def rolar_d20_combate(vantagem: bool, desvantagem: bool):
    roll1 = rolar_dado(20)
    roll2 = rolar_dado(20)
    
    if vantagem:
        return max(roll1, roll2), [roll1, roll2]
    elif desvantagem:
        return min(roll1, roll2), [roll1, roll2]
    
    return roll1, [roll1]


def processar_ataque_fisico(jogador, inimigo_ca: int, defensor_status: list = None, tipo_ataque: str = "melee", vantagem_extra: bool = False, desvantagem_extra: bool = False) -> ResultadoAtaque:
    if defensor_status is None:
        defensor_status = []
        
    atacante_status = getattr(jogador, 'status_efeitos', [])
    
    # 1. Rola o d20 com Vantagem/Desvantagem
    vantagem, desvantagem = calcular_vantagem_desvantagem(atacante_status, defensor_status, tipo_ataque)
    
    if vantagem_extra: vantagem = True
    if desvantagem_extra: desvantagem = True
    
    if vantagem and desvantagem:
        vantagem = False
        desvantagem = False
        
    d20, detalhes_d20 = rolar_d20_combate(vantagem, desvantagem)
    
    # Usando o modificador real do banco de dados (Proficiência + Atributo)
    modificador = jogador.modificador_ataque
    total_ataque = d20 + modificador

    # 2. Verifica acerto
    acertou = False
    critico = False

    if d20 == 20:
        acertou = True
        critico = True
    elif d20 == 1:
        acertou = False
    else:
        acertou = total_ataque >= inimigo_ca

    # 3. Calcula dano (se acertar)
    dano = 0
    if acertou:
        dano_dado = getattr(jogador, 'dano_dado', '1d6')
        try:
            partes = dano_dado.lower().split('d')
            qtd_dados = int(partes[0]) if partes[0] and partes[0].isdigit() else 1
            faces_dano = int(partes[1])
        except (ValueError, IndexError):
            qtd_dados = 1
            faces_dano = 6  # Fallback seguro para 1d6

        mod_dano = getattr(jogador, 'mod_dano', 0)
        
        # Rola a quantidade exata de dados (Ex: 2d6 rola duas vezes o d6)
        rolagem_dano = sum(rolar_dado(faces_dano) for _ in range(qtd_dados))
        
        # Crítico na 5e: Dobram-se os DADOS rolados, não o total
        if critico:
            rolagem_dano += sum(rolar_dado(faces_dano) for _ in range(qtd_dados))
            
        dano = rolagem_dano + mod_dano

    return ResultadoAtaque(
        d20=d20,
        total_ataque=total_ataque,
        acertou=acertou,
        critico=critico,
        dano=dano,
        detalhes_d20=detalhes_d20
    )


def processar_ataque_objeto(jogador, objeto) -> ResultadoAtaqueObjeto:
    """Processa um ataque físico contra um ObjetoDestrutivel.
    Respeita CA, HP, vulnerabilidades e break_threshold (Str).
    """
    atacante_status = getattr(jogador, 'status_efeitos', [])
    
    # 1. Verificar arrombamento por Força pura (Teste de Força ao invés de usar valor direto)
    quebrou_por_forca = False
    if getattr(objeto, 'break_threshold', 0) > 0:
        vantagem, desvantagem = calcular_vantagem_desvantagem(atacante_status, [], "melee")
        d20_str, detalhes_str = rolar_d20_combate(vantagem, desvantagem)
        
        mod_str = getattr(jogador, 'mod_str', 0)
        forca_total = d20_str + mod_str
        
        if forca_total >= objeto.break_threshold:
            quebrou_por_forca = True
            dano = objeto.hp_atual  # destroi em um golpe
            novo_hp = 0
            return ResultadoAtaqueObjeto(
                d20=d20_str, total_ataque=forca_total, acertou=True,
                critico=False, dano=dano, destruido=True,
                hp_restante=0, quebrou_por_forca=True, detalhes_d20=detalhes_str
            )

    # 2. Rolagem de ataque normal vs. CA do objeto
    vantagem, desvantagem = calcular_vantagem_desvantagem(atacante_status, [], "melee")
    d20, detalhes_d20 = rolar_d20_combate(vantagem, desvantagem)
    
    modificador = jogador.modificador_ataque
    total_ataque = d20 + modificador

    acertou = False
    critico = d20 == 20
    if d20 == 20:
        acertou = True
    elif d20 == 1:
        acertou = False
    else:
        acertou = total_ataque >= getattr(objeto, 'ca', 10)

    # 3. Calcular dano
    dano = 0
    novo_hp = objeto.hp_atual
    if acertou:
        dano_dado = getattr(jogador, 'dano_dado', '1d6')
        try:
            partes = dano_dado.lower().split('d')
            qtd_dados = int(partes[0]) if partes[0] and partes[0].isdigit() else 1
            faces_dano = int(partes[1])
        except (ValueError, IndexError):
            qtd_dados = 1
            faces_dano = 6

        mod_dano = getattr(jogador, 'mod_dano', 0)
        
        # Rola a quantidade exata de dados (Ex: 2d6 rola duas vezes o d6)
        rolagem_dano = sum(rolar_dado(faces_dano) for _ in range(qtd_dados))
        
        # Crítico na 5e: Dobram-se os DADOS rolados, não o total
        if critico:
            rolagem_dano += sum(rolar_dado(faces_dano) for _ in range(qtd_dados))
            
        dano = rolagem_dano + mod_dano

        # Aplicar vulnerabilidades (dano dobrado)
        vulnerabilidades = getattr(objeto, 'vulnerabilidades', []) or []
        if vulnerabilidades:
            arma = getattr(jogador, 'arma_equipada', '').lower()
            
            # CORREÇÃO: Socos e artes marciais agora contam como contundente!
            tipo_dano = 'contundente' if any(x in arma for x in ['clava', 'maca', 'maça', 'martelo', 'bordão', 'cajado', 'desarmado', 'soco', 'artes marciais']) else \
                        'cortante' if any(x in arma for x in ['espada', 'machado', 'adaga', 'foice']) else \
                        'perfurante'
            
            if tipo_dano in vulnerabilidades:
                dano *= 2

        # Resistências (dano reduzido à metade)
        resistencias = getattr(objeto, 'resistencias', []) or []
        if resistencias:
            # Resistência genérica a dano físico não mágico
            if 'fisico' in resistencias or 'todos' in resistencias:
                dano = max(1, dano // 2)

        novo_hp = max(0, objeto.hp_atual - dano)

    destruido = novo_hp <= 0

    return ResultadoAtaqueObjeto(
        d20=d20,
        total_ataque=total_ataque,
        acertou=acertou,
        critico=critico,
        dano=dano,
        destruido=destruido,
        hp_restante=novo_hp,
        quebrou_por_forca=False,
        detalhes_d20=detalhes_d20
    )