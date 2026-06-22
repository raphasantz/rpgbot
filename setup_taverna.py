"""Cria a sala taverna como lobby central do jogo."""
from modelos_web import SessionLocal, Cena, Npc
from sqlalchemy import select


def setup_taverna():
    db = SessionLocal()
    try:
        # 1. Criar sala taverna (lobby central)
        taverna = db.execute(select(Cena).filter(Cena.cod_sala == 'taverna')).scalars().first()
        if not taverna:
            taverna = Cena(
                cod_sala='taverna',
                nome_sala='A Taverna do Dragao Descansado',
                descricao_visual=(
                    'Uma taverna acolhedora com lareira acesa, mesas de madeira rústicas, '
                    'e o aroma de estufado no ar. Um letreiro de ferro curvado pendurado '
                    'acima da barra mostra um dragao adormecido. A taverna esta cheia de '
                    'aventureiros e viajantes de todas as racas.'
                ),
                conexoes={
                    'sair': 'carvalhal',
                    'rua': 'carvalhal',
                    'descanso': 'taverna_quarto',
                },
                hazards=[],
            )
            db.add(taverna)
            print('[OK] Sala taverna criada')
        else:
            taverna.conexoes = {
                'sair': 'carvalhal',
                'rua': 'carvalhal',
                'descanso': 'taverna_quarto',
            }
            print('[UPDATE] Sala taverna atualizada')

        # 2. Criar quarto de descanso
        quarto = db.execute(select(Cena).filter(Cena.cod_sala == 'taverna_quarto')).scalars().first()
        if not quarto:
            quarto = Cena(
                cod_sala='taverna_quarto',
                nome_sala='Quarto da Taverna',
                descricao_visual=(
                    'Um quarto simples com uma cama de palha, uma bacia de agua, '
                    'e uma vela que queima suavemente. O silencio e reconfortante.'
                ),
                conexoes={
                    'voltar': 'taverna',
                    'taverna': 'taverna',
                },
                hazards=[],
            )
            db.add(quarto)
            print('[OK] Quarto da taverna criado')

        # 3. Criar Taverneiro (Garrick)
        taverneiro = db.execute(select(Npc).filter(Npc.cod_sala == 'taverna', Npc.nome == 'Garrick Cervaspetra')).scalars().first()
        if not taverneiro:
            taverneiro = Npc(
                cod_sala='taverna',
                nome='Garrick Cervaspetra',
                descricao='Um homem robusto de meia-idade com bigode grisalho e sorriso acolhedor. Veste avental de couro e serve cerveja com maestria.',
                dialogo_base='Bem-vindo ao Dragao Descansado! O que vai ser? Uma cerveja gelada ou uma refeicao quente? Dizem que coisas estranhas estao acontecendo na Cidadela...',
            )
            db.add(taverneiro)
            print('[OK] Taverneiro criado')

        # 4. Criar Bardo (Melodia)
        bardo = db.execute(select(Npc).filter(Npc.cod_sala == 'taverna', Npc.nome == 'Melodia Silvaluz')).scalars().first()
        if not bardo:
            bardo = Npc(
                cod_sala='taverna',
                nome='Melodia Silvaluz',
                descricao='Uma jovem de olhos verdes com uma lira no colo. Sua voz suave preenche a taverna com melodias encantadas.',
                dialogo_base='Ah, um aventureiro! Quer ouvir uma cancao? Dizem que o Magus Nikolai esta procurando ajudantes na Torre do Dragao. Interessante, nao?',
            )
            db.add(bardo)
            print('[OK] Bardo criada')

        # 5. Criar Estranho Misterioso
        estranho = db.execute(select(Npc).filter(Npc.cod_sala == 'taverna', Npc.nome == 'O Estranho de Capuz')).scalars().first()
        if not estranho:
            estranho = Npc(
                cod_sala='taverna',
                nome='O Estranho de Capuz',
                descricao='Uma figura encapuzada sentada no canto mais escuro da taverna. Ninguem sabe quem e, mas sempre parece estar observando.',
                dialogo_base='...nao e hora...ainda...os sinais estao la... Cuidado com a floresta. As arvores la... elas lembram.',
            )
            db.add(estranho)
            print('[OK] Estranho misterioso criado')

        # 6. Atualizar conexoes de carvalhal
        carvalhal = db.execute(select(Cena).filter(Cena.cod_sala == 'carvalhal')).scalars().first()
        if carvalhal:
            carvalhal.conexoes = {
                'norte': 'estrada_velha',
                'leste': 'trilha_triboar',
                'taverna': 'taverna',
                'estalagem': 'taverna',
            }
            print('[OK] Carvalhal conectado a taverna')

        db.commit()
        print('\n=== Taverna configurada com sucesso! ===')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    setup_taverna()
