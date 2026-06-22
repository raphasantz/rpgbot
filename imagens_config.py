"""
imagens_config.py — Imagens do jogo MezzaRPG.

114 cenas com imagens unicas geradas com FAL.ai (FLUX 2 Klein 9B).
Todas servidas localmente de /static/imagens/cenas/.

CACHE LOCAL:
    - url_para() verifica arquivo local primeiro, depois mapping
    - 114 imagens unicas + 4 genericas de fallback
"""
from pathlib import Path

CACHE_DIR = Path(__file__).parent / ".cache_imagens"
CACHE_DIR.mkdir(exist_ok=True)

STATIC_CENAS = Path(__file__).parent / "app" / "static" / "imagens" / "cenas"
STATIC_NPCS = Path(__file__).parent / "app" / "static" / "imagens" / "npcs"
STATIC_INIMIGOS = Path(__file__).parent / "app" / "static" / "imagens" / "inimigos"


def _local(tipo: str, chave: str) -> str:
    """Retorna URL local /static/imagens/{tipo}/{chave}.png se o arquivo existir."""
    if tipo == "cena":
        path = STATIC_CENAS / f"{chave}.jpg"
        if not path.exists(): path = STATIC_CENAS / f"{chave}.png"
        if path.exists():
            return f"/static/imagens/cenas/{chave}.jpg"
    elif tipo == "npc":
        path = STATIC_NPCS / f"{chave}.png"
        if path.exists():
            return f"/static/imagens/npcs/{chave}.png"
    elif tipo == "inimigo":
        path = STATIC_INIMIGOS / f"{chave}.png"
        if path.exists():
            return f"/static/imagens/inimigos/{chave}.png"
    return ""


# ── CENAS (114 salas com imagens unicas) ──────────────────────────────────────
IMAGENS_CENAS = {
    "taverna":              "/static/imagens/cenas/taverna.jpg",
    "estalagem_colina":     "/static/imagens/cenas/estalagem_colina.jpg",
    "cidadela_0":           "/static/imagens/cenas/cidadela_0.jpg",
    "cidadela_1":           "/static/imagens/cenas/cidadela_1.jpg",
    "cidadela_2":           "/static/imagens/cenas/cidadela_2.jpg",
    "cidadela_3":           "/static/imagens/cenas/cidadela_3.jpg",
    "cidadela_4":           "/static/imagens/cenas/cidadela_4.jpg",
    "cidadela_5":           "/static/imagens/cenas/cidadela_5.jpg",
    "cidadela_6":           "/static/imagens/cenas/cidadela_6.jpg",
    "cidadela_7":           "/static/imagens/cenas/cidadela_7.jpg",
    "cidadela_8":           "/static/imagens/cenas/cidadela_8.jpg",
    "cidadela_9":           "/static/imagens/cenas/cidadela_9.jpg",
    "cidadela_10":          "/static/imagens/cenas/cidadela_10.jpg",
    "cidadela_11":          "/static/imagens/cenas/cidadela_11.jpg",
    "cidadela_12":          "/static/imagens/cenas/cidadela_12.jpg",
    "cidadela_13":          "/static/imagens/cenas/cidadela_13.jpg",
    "cidadela_14":          "/static/imagens/cenas/cidadela_14.jpg",
    "cidadela_15":          "/static/imagens/cenas/cidadela_15.jpg",
    "cidadela_16":          "/static/imagens/cenas/cidadela_16.jpg",
    "cidadela_17":          "/static/imagens/cenas/cidadela_17.jpg",
    "cidadela_18":          "/static/imagens/cenas/cidadela_18.jpg",
    "cidadela_19":          "/static/imagens/cenas/cidadela_19.jpg",
    "cidadela_20":          "/static/imagens/cenas/cidadela_20.jpg",
    "cidadela_21":          "/static/imagens/cenas/cidadela_21.jpg",
    "cidadela_22":          "/static/imagens/cenas/cidadela_22.jpg",
    "cidadela_23":          "/static/imagens/cenas/cidadela_23.jpg",
    "cidadela_24":          "/static/imagens/cenas/cidadela_24.jpg",
    "cidadela_25":          "/static/imagens/cenas/cidadela_25.jpg",
    "cidadela_26":          "/static/imagens/cenas/cidadela_26.jpg",
    "cidadela_27":          "/static/imagens/cenas/cidadela_27.jpg",
    "cidadela_28":          "/static/imagens/cenas/cidadela_28.jpg",
    "cidadela_29":          "/static/imagens/cenas/cidadela_29.jpg",
    "cidadela_30":          "/static/imagens/cenas/cidadela_30.jpg",
    "cidadela_31":          "/static/imagens/cenas/cidadela_31.jpg",
    "cidadela_32":          "/static/imagens/cenas/cidadela_32.jpg",
    "cidadela_33":          "/static/imagens/cenas/cidadela_33.jpg",
    "cidadela_34":          "/static/imagens/cenas/cidadela_34.jpg",
    "cidadela_35":          "/static/imagens/cenas/cidadela_35.jpg",
    "cidadela_36":          "/static/imagens/cenas/cidadela_36.jpg",
    "cidadela_37":          "/static/imagens/cenas/cidadela_37.jpg",
    "cidadela_38":          "/static/imagens/cenas/cidadela_38.jpg",
    "cidadela_39":          "/static/imagens/cenas/cidadela_39.jpg",
    "cidadela_40":          "/static/imagens/cenas/cidadela_40.jpg",
    "cidadela_41":          "/static/imagens/cenas/cidadela_41.jpg",
    "cidadela_42":          "/static/imagens/cenas/cidadela_42.jpg",
    "cidadela_43":          "/static/imagens/cenas/cidadela_43.jpg",
    "cidadela_44":          "/static/imagens/cenas/cidadela_45.jpg",
    "cidadela_45":          "/static/imagens/cenas/cidadela_45.jpg",
    "cidadela_46":          "/static/imagens/cenas/cidadela_46.jpg",
    "cidadela_47":          "/static/imagens/cenas/cidadela_47.jpg",
    "cidadela_48":          "/static/imagens/cenas/cidadela_48.jpg",
    "cidadela_49":          "/static/imagens/cenas/cidadela_49.jpg",
    "cidadela_50":          "/static/imagens/cenas/cidadela_50.jpg",
    "cidadela_51":          "/static/imagens/cenas/cidadela_51.jpg",
    "cidadela_52":          "/static/imagens/cenas/cidadela_52.jpg",
    "cidadela_53":          "/static/imagens/cenas/cidadela_53.jpg",
    "cidadela_54":          "/static/imagens/cenas/cidadela_54.jpg",
    "cidadela_55":          "/static/imagens/cenas/cidadela_55.jpg",
    "cidadela_56":          "/static/imagens/cenas/cidadela_56.jpg",
    "cid_altar_belak":      "/static/imagens/cenas/cid_altar_belak.jpg",
    "trilha_triboar":       "/static/imagens/cenas/trilha_triboar.jpg",
    "esconderijo_entrada":  "/static/imagens/cenas/esconderijo_entrada.jpg",
    "esconderijo_passagem": "/static/imagens/cenas/esconderijo_passagem.jpg",
    "esconderijo_lobos":    "/static/imagens/cenas/esconderijo_lobos.jpg",
    "esconderijo_fissura":  "/static/imagens/cenas/esconderijo_fissura.jpg",
    "esconderijo_ponte":    "/static/imagens/cenas/esconderijo_ponte.jpg",
    "esconderijo_covil":    "/static/imagens/cenas/esconderijo_covil.jpg",
    "esconderijo_fontes":   "/static/imagens/cenas/esconderijo_fontes.jpg",
    "esconderijo_klarg":    "/static/imagens/cenas/esconderijo_klarg.jpg",
    "phandalin":            "/static/imagens/cenas/phandalin_vila.jpg",
    "phandalin_escritorio": "/static/imagens/cenas/phandalin_escritorio.jpg",
    "phandalin_ferreiro":   "/static/imagens/cenas/phandalin_ferreiro.jpg",
    "phandalin_pomar":      "/static/imagens/cenas/phandalin_pomar.jpg",
    "phandalin_templo":     "/static/imagens/cenas/phandalin_templo.jpg",
    "marcarrubra_porao":        "/static/imagens/cenas/marcarrubra_porao.jpg",
    "marcarrubra_corredor":     "/static/imagens/cenas/marcarrubra_corredor.jpg",
    "marcarrubra_barracas":     "/static/imagens/cenas/marcarrubra_barracas.jpg",
    "marcarrubra_criptas":      "/static/imagens/cenas/marcarrubra_criptas.jpg",
    "marcarrubra_prisao":       "/static/imagens/cenas/marcarrubra_prisao.jpg",
    "marcarrubra_saguao":       "/static/imagens/cenas/marcarrubra_saguao.jpg",
    "marcarrubra_torre":        "/static/imagens/cenas/marcarrubra_torre.jpg",
    "marcarrubra_fenda":        "/static/imagens/cenas/marcarrubra_estalactites.jpg",
    "marcarrubra_templo":       "/static/imagens/cenas/marcarrubra_templo.jpg",
    "marcarrubra_estalactites": "/static/imagens/cenas/marcarrubra_estalactites.jpg",
    "marcarrubra_mina":         "/static/imagens/cenas/marcarrubra_mina.jpg",
    "marcarrubra_glasstaff":    "/static/imagens/cenas/marcarrubra_glasstaff.jpg",
    "conyberry":            "/static/imagens/cenas/conyberry.jpg",
    "poco_coruja":          "/static/imagens/cenas/poco_coruja.jpg",
    "cume_wyvern":          "/static/imagens/cenas/cume_wyvern.jpg",
    "arvore_trovao_entrada":    "/static/imagens/cenas/arvore_trovao_entrada.jpg",
    "arvore_trovao_boticario":  "/static/imagens/cenas/arvore_trovao_boticario.jpg",
    "arvore_trovao_torre":      "/static/imagens/cenas/arvore_trovao_torre.jpg",
    "arvore_trovao_tesouro":    "/static/imagens/cenas/arvore_trovao_tesouro.jpg",
    "arvore_trovao_floresta":   "/static/imagens/cenas/arvore_trovao_floresta.jpg",
    "castelo_entrada":      "/static/imagens/cenas/castelo_entrada.jpg",
    "castelo_saguao":       "/static/imagens/cenas/castelo_saguao.jpg",
    "castelo_refeitorio":   "/static/imagens/cenas/castelo_refeitorio.jpg",
    "castelo_torre_urso":   "/static/imagens/cenas/castelo_torre_urso.jpg",
    "castelo_santuario":    "/static/imagens/cenas/castelo_santuario.jpg",
    "castelo_aposentos":    "/static/imagens/cenas/castelo_aposentos.jpg",
    "onda_eco_entrada":         "/static/imagens/cenas/onda_eco_entrada.jpg",
    "onda_eco_tuneis":          "/static/imagens/cenas/onda_eco_tuneis.jpg",
    "onda_eco_fungos":          "/static/imagens/cenas/onda_eco_fungos.jpg",
    "onda_eco_grande_caverna":  "/static/imagens/cenas/onda_eco_grande_caverna.jpg",
    "onda_eco_fornalha":        "/static/imagens/cenas/onda_eco_fornalha.jpg",
    "onda_eco_aposentos":       "/static/imagens/cenas/onda_eco_aposentos.jpg",
    "onda_eco_forja":           "/static/imagens/cenas/onda_eco_forja.jpg",
    "onda_eco_piscina":         "/static/imagens/cenas/onda_eco_piscina.jpg",
    "onda_eco_templo":          "/static/imagens/cenas/onda_eco_templo.jpg",
    "onda_eco_goblins":         "/static/imagens/cenas/onda_eco_goblins.jpg",
    "onda_eco_estreitas":       "/static/imagens/cenas/onda_eco_estreitas.jpg",
    "onda_eco_mina_escura":     "/static/imagens/cenas/onda_eco_mina_escura.jpg",
    "onda_eco_coluna":          "/static/imagens/cenas/onda_eco_coluna.jpg",
    "onda_eco_espirituais":     "/static/imagens/cenas/onda_eco_espirituais.jpg",
    "onda_eco_basilisco":       "/static/imagens/cenas/onda_eco_basilisco.jpg",
    "onda_eco_nezznar":         "/static/imagens/cenas/onda_eco_nezznar.jpg",
    "_default":             "/static/imagens/cenas/_generic_dungeon.png",
}


# ── NPCs ────────────────────────────────────────────────────────────────────────
IMAGENS_NPCS = {
    "Taverneiro do Velho Javali":  "/static/imagens/cenas/taverna_npc.jpg",
    "Dona Linene":                 "/static/imagens/cenas/phandalin_ferreiro.jpg",
    "Belak o Proscrito":           "/static/imagens/cenas/cid_altar_belak.jpg",
    "_default":                    "",
}


# ── INIMIGOS ────────────────────────────────────────────────────────────────────
IMAGENS_INIMIGOS = {
    "Rato Atroz":                  "https://orbedosdragoes.com/wp-content/uploads/2015/02/rato-atroz.jpg",
    "Ramo Seco":                   "https://dragoesdosreinos.wordpress.com/wp-content/uploads/2009/05/ramoseco.jpg",
    "Kobold Sentinela":            "https://draconusdictum.wordpress.com/wp-content/uploads/2006/12/kobold.jpg",
    "Goblin Saqueador":            "https://cdn.cardsrealm.com/images/cartas/7ed-seventh-edition/en/crop-med/goblin-raider-192.jpeg",
    "Goblin Guerreiro":            "https://nadaqueteinteresse.weebly.com/uploads/8/1/7/1/8171548/3847330.jpg",
    "Bugbear Jardineiro":          "https://media-waterdeep.cursecdn.com/avatars/thumbnails/0/291/1000/1000/636252772552775032.jpeg",
    "Esqueleto":                   "https://media-waterdeep.cursecdn.com/avatars/thumbnails/16/471/1000/1000/636376289069650058.jpeg",
    "Durnn (Chefe Goblin)":        "https://media-waterdeep.cursecdn.com/avatars/thumbnails/0/353/1000/1000/636252777935400263.jpeg",
    "Calcryx (Filhote Dragao)":    "https://media-waterdeep.cursecdn.com/avatars/thumbnails/0/132/1000/1000/636252755375971485.jpeg",
    "Belak o Proscrito":           "https://media-waterdeep.cursecdn.com/avatars/thumbnails/16/465/1000/1000/636376288647043878.jpeg",
    "_default":                    "",
}


# ── ITENS ───────────────────────────────────────────────────────────────────────
IMAGENS_ITENS = {
    "Pocao de Cura":       "",
    "Espada Longa":        "",
    "Adaga":               "",
    "Arco Longo":          "",
    "Cota de Malha":       "",
    "Escudo":              "",
    "_default":            "",
}


_MAPA_IMAGENS = {
    "cena": IMAGENS_CENAS,
    "npc": IMAGENS_NPCS,
    "inimigo": IMAGENS_INIMIGOS,
    "item": IMAGENS_ITENS,
}


def url_para(tipo: str, chave: str) -> str:
    """
    Retorna a URL da imagem do tipo (cena/npc/inimigo/item) e chave.
    1. Verifica arquivo local em /static/imagens/
    2. Verifica mapping no dict
    3. Usa _default se nao encontrar
    """
    mapa = _MAPA_IMAGENS.get(tipo, {})
    local = _local(tipo, chave)
    if local:
        return local
    url = mapa.get(chave)
    if url:
        return url
    return mapa.get("_default", "") or ""
