#!/usr/bin/env python3
"""
Seed database from JSON export files (db_export/).
Run once to populate all tables from the rpg_bot JSON data.
"""
import json
import os
from pathlib import Path

from modelos_web import (
    engine, SessionLocal, Base,
    JogadorWeb, CampanhaWeb, Aventura,
    Encontro, Inimigo, Cena,
    Interativo, ObjetoDestrutivel, Npc,
    EncontroAleatorio, Missao,
)
from sqlalchemy import select

DATA_DIR = Path(__file__).parent / "db_export"


def load_json(name: str) -> list:
    path = DATA_DIR / name
    if not path.exists():
        print(f"⚠️  {name} não encontrado")
        return []
    with open(path, encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return []
        return json.loads(content)


def seed():
    db = SessionLocal()
    try:
        # ── AVENTURAS ──────────────────────────────────────────────
        for a in load_json("aventuras.json"):
            if not db.execute(select(Aventura).filter(Aventura.id == a["id"])).scalars().first():
                db.add(Aventura(id=a["id"], nome=a["nome"], prologo=a.get("prologo", "")))
        print(f"✅ Aventuras: {len(load_json('aventuras.json'))}")

        # ── INIMIGOS (bestiário) ──────────────────────────────────
        for i in load_json("bestiario_cidadela.json"):
            if not db.execute(select(Inimigo).filter(Inimigo.nome == i["nome"])).scalars().first():
                # Extrair ataque dos acoes (primeiro valor)
                ataque_str = "+0"
                acoes = i.get("acoes", [])
                if acoes and isinstance(acoes[0], str):
                    ataque_str = acoes[0]

                db.add(Inimigo(
                    nome=i["nome"],
                    hp_max=i.get("hp_max", i.get("hp", 1)),
                    ca=i["ca"],
                    ataque=ataque_str,
                    dano=i.get("dano") or "1d4",
                    imagem_url=i.get("imagem_url"),
                    xp_recompensa=i.get("xp", 50),
                    ouro_recompensa=i.get("ouro_recompensa", 5),
                    is_boss=i.get("is_boss", False),
                    fase_atual=i.get("fase_atual", 1),
                    loot_especial=i.get("loot_especial", []),
                    tipo_dano_padrao=i.get("tipo_dano_padrao", "contundente"),
                    resistencias=i.get("resistencias", []),
                    vulnerabilidades=i.get("vulnerabilidades", []),
                    imunidades=i.get("imunidades", []),
                ))
        print(f"✅ Inimigos: {len(load_json('bestiario_cidadela.json'))}")

        # ── CENAS / SALAS ─────────────────────────────────────────
        for c in load_json("aventura_cidadela.json"):
            if not db.execute(select(Cena).filter(Cena.cod_sala == c["cod_sala"])).scalars().first():
                db.add(Cena(
                    cod_sala=c["cod_sala"],
                    nome_sala=c["nome_sala"],
                    descricao_visual=c.get("descricao_visual", ""),
                    conexoes=c.get("conexoes", {}),
                    imagem_url=c.get("imagem_url"),
                    loot_fixo=c.get("loot_fixo", []),
                    hazards=c.get("hazards", []),
                ))
        print(f"✅ Cenas: {len(load_json('aventura_cidadela.json'))}")

        # ── NPCS ──────────────────────────────────────────────────
        for n in load_json("aliados_e_npcs.json"):
            if not db.execute(select(Npc).filter(Npc.nome == n["nome"])).scalars().first():
                db.add(Npc(
                    cod_sala=n.get("localizacao", "carvalhal"),
                    nome=n["nome"],
                    descricao=n.get("descricao", ""),
                    dialogo_base=n.get("dialogo_inicial", n.get("dialogo_base", "")),
                    dialogo_item_especial=n.get("dialogo_item_especial"),
                    item_gatilho=n.get("item_gatilho"),
                ))
        print(f"✅ NPCs: {len(load_json('aliados_e_npcs.json'))}")

        # ── ENCONTROS (spawn por sala) ────────────────────────────
        # Definidos manualmente baseados na Cidadela Sans Sol
        # Nomes EXATOS do bestiário (bestiario_cidadela.json)
        encontros_definidos = [
            # cod_sala, nome_inimigo_exato_do_bestiario, quantidade
            ("entrada_cidadela", "Goblin Saqueador", 2),
            ("saguao_principal", "Esqueleto", 3),
            ("corredor_leste", "Aranha Gigante", 2),
            ("sala_boss", "Belak, o Proscrito (Druida)", 1),  # Boss da cidadela
            # Masmorra clássica (Sunless Citadel / Cidadela)
            ("cidadela_1", "Rato Atroz", 2),
            ("cidadela_2", "Kobold Sentinela", 3),
            ("cidadela_3", "Goblin", 2),  # ou "Goblin Arqueiro"
        ]
        for cod_sala, nome_inimigo, quantidade in encontros_definidos:
            # Verificar se o inimigo existe no bestiário
            inimigo_existe = db.execute(select(Inimigo).filter(Inimigo.nome == nome_inimigo)).scalars().first()
            if not inimigo_existe:
                print(f"⚠️  Inimigo '{nome_inimigo}' não encontrado no bestiário, pulando encontro em {cod_sala}")
                continue
            exists = db.execute(select(Encontro).filter(
                Encontro.cod_sala == cod_sala,
                Encontro.nome_inimigo == nome_inimigo
            )).scalars().first()
            if not exists:
                db.add(Encontro(
                    cod_sala=cod_sala,
                    nome_inimigo=nome_inimigo,
                    quantidade=quantidade,
                    condicao_aparecimento="sempre",
                    ativo=True,
                    multiplicador_ameaca=1,
                ))
        print(f"✅ Encontros: {len(encontros_definidos)}")

        # ── ENCONTROS ALEATÓRIOS ──────────────────────────────────
        # Opcional: pode derivar de cenas com chance < 100
        print("ℹ️  Encontros aleatórios: usando padrão (manual se necessário)")

        # ── INTERATIVOS (baús, armadilhas) ────────────────────────
        # Extrair de cenas se houver campo 'interativos'
        for c in load_json("aventura_cidadela.json"):
            for inter in c.get("interativos", []):
                exists = db.execute(select(Interativo).filter(
                    Interativo.cod_sala == c["cod_sala"],
                    Interativo.nome == inter["nome"]
                )).scalars().first()
                if not exists:
                    db.add(Interativo(
                        cod_sala=c["cod_sala"],
                        nome=inter["nome"],
                        descricao=inter.get("descricao", ""),
                        tipo=inter.get("tipo", "bau"),
                        cd_teste=inter.get("cd_teste", 10),
                        atributo_teste=inter.get("atributo_teste", "DEX"),
                        recompensa=inter.get("recompensa", []),
                        dano_falha=inter.get("dano_falha", 0),
                        ativo=True,
                    ))
        print("✅ Interativos: extraídos das cenas")

        db.commit()
        print("🎉 Seed completo!")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()