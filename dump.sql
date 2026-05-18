--
-- PostgreSQL database dump
--

-- Dumped from database version 17.0
-- Dumped by pg_dump version 17.0

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: iniciar_aventura(character varying, character varying); Type: FUNCTION; Schema: public; Owner: rpg
--

CREATE FUNCTION public.iniciar_aventura(p_jogador_id character varying, p_aventura_nome character varying) RETURNS TABLE(paragrafo_id integer, texto_paragrafo text, opcoes_json jsonb, aventura_ref character varying)
    LANGUAGE plpgsql
    AS $$
DECLARE v_paragrafo_inicial INTEGER;
BEGIN
    SELECT paragrafo_inicial INTO v_paragrafo_inicial FROM aventuras_catalogo WHERE nome = p_aventura_nome;
    
    INSERT INTO aventuras_progresso (jogador_id, aventura_nome, paragrafo_atual, paragrafos_visitados)
    VALUES (p_jogador_id, p_aventura_nome, v_paragrafo_inicial, jsonb_build_array(v_paragrafo_inicial))
    ON CONFLICT (jogador_id, aventura_nome) 
    DO UPDATE SET 
        paragrafo_atual = v_paragrafo_inicial, 
        paragrafos_visitados = jsonb_build_array(v_paragrafo_inicial), 
        ultima_acao = NOW(), 
        finalizado = false;

    RETURN QUERY SELECT par.numero, par.texto, par.opcoes, p_aventura_nome 
    FROM aventuras_paragrafos par 
    WHERE par.aventura_nome = p_aventura_nome AND par.numero = v_paragrafo_inicial;
END;
$$;


ALTER FUNCTION public.iniciar_aventura(p_jogador_id character varying, p_aventura_nome character varying) OWNER TO rpg;

--
-- Name: ir_paragrafo(character varying, character varying, integer); Type: FUNCTION; Schema: public; Owner: rpg
--

CREATE FUNCTION public.ir_paragrafo(p_jogador_id character varying, p_aventura_nome character varying, p_numero_paragrafo integer) RETURNS TABLE(paragrafo_id integer, texto_paragrafo text, opcoes_json jsonb, aventura_ref character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE aventuras_progresso 
    SET paragrafo_atual = p_numero_paragrafo, 
        paragrafos_visitados = paragrafos_visitados || jsonb_build_array(p_numero_paragrafo), 
        ultima_acao = NOW()
    WHERE jogador_id = p_jogador_id AND aventura_nome = p_aventura_nome;

    RETURN QUERY SELECT par.numero, par.texto, par.opcoes, p_aventura_nome 
    FROM aventuras_paragrafos par 
    WHERE par.aventura_nome = p_aventura_nome AND par.numero = p_numero_paragrafo;
END;
$$;


ALTER FUNCTION public.ir_paragrafo(p_jogador_id character varying, p_aventura_nome character varying, p_numero_paragrafo integer) OWNER TO rpg;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: aliados_e_npcs; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.aliados_e_npcs (
    id integer NOT NULL,
    nome character varying(50),
    raca_classe character varying(50),
    hp_atual integer,
    tendencia character varying(20),
    notas_personalidade text
);


ALTER TABLE public.aliados_e_npcs OWNER TO rpg;

--
-- Name: aliados_e_npcs_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.aliados_e_npcs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.aliados_e_npcs_id_seq OWNER TO rpg;

--
-- Name: aliados_e_npcs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.aliados_e_npcs_id_seq OWNED BY public.aliados_e_npcs.id;


--
-- Name: aventura_cidadela; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.aventura_cidadela (
    cod_sala character varying NOT NULL,
    nome_sala character varying,
    descricao_visual text,
    segredos_mestre text,
    conexoes json
);


ALTER TABLE public.aventura_cidadela OWNER TO rpg;

--
-- Name: aventuras; Type: TABLE; Schema: public; Owner: user_8W2mTA
--

CREATE TABLE public.aventuras (
    id character varying(50) NOT NULL,
    nome character varying(100),
    prologo text
);


ALTER TABLE public.aventuras OWNER TO "user_8W2mTA";

--
-- Name: aventuras_catalogo; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.aventuras_catalogo (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    titulo character varying(200) NOT NULL,
    descricao text,
    autor character varying(100),
    dificuldade character varying(20),
    nivel_recomendado character varying(20),
    paragrafo_inicial integer DEFAULT 1,
    total_paragrafos integer,
    tempo_estimado_minutos integer,
    ativa boolean DEFAULT true,
    criado_em timestamp without time zone DEFAULT now()
);


ALTER TABLE public.aventuras_catalogo OWNER TO rpg;

--
-- Name: aventuras_catalogo_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.aventuras_catalogo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.aventuras_catalogo_id_seq OWNER TO rpg;

--
-- Name: aventuras_catalogo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.aventuras_catalogo_id_seq OWNED BY public.aventuras_catalogo.id;


--
-- Name: aventuras_inventario; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.aventuras_inventario (
    id integer NOT NULL,
    progresso_id integer,
    item_nome character varying(100) NOT NULL,
    item_tipo character varying(50),
    quantidade integer DEFAULT 1,
    descricao text,
    paragrafo_obtido integer,
    usado boolean DEFAULT false
);


ALTER TABLE public.aventuras_inventario OWNER TO rpg;

--
-- Name: aventuras_inventario_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.aventuras_inventario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.aventuras_inventario_id_seq OWNER TO rpg;

--
-- Name: aventuras_inventario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.aventuras_inventario_id_seq OWNED BY public.aventuras_inventario.id;


--
-- Name: aventuras_paragrafos; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.aventuras_paragrafos (
    id integer NOT NULL,
    aventura_nome character varying(100),
    numero integer NOT NULL,
    texto text NOT NULL,
    opcoes jsonb DEFAULT '[]'::jsonb,
    tipo character varying(20) DEFAULT 'normal'::character varying,
    requer_teste boolean DEFAULT false,
    teste_atributo character varying(10),
    teste_dificuldade integer,
    sucesso_paragrafo integer,
    falha_paragrafo integer,
    imagem_url text
);


ALTER TABLE public.aventuras_paragrafos OWNER TO rpg;

--
-- Name: aventuras_paragrafos_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.aventuras_paragrafos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.aventuras_paragrafos_id_seq OWNER TO rpg;

--
-- Name: aventuras_paragrafos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.aventuras_paragrafos_id_seq OWNED BY public.aventuras_paragrafos.id;


--
-- Name: aventuras_progresso; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.aventuras_progresso (
    id integer NOT NULL,
    jogador_id character varying(50) NOT NULL,
    aventura_nome character varying(100),
    paragrafo_atual integer NOT NULL,
    paragrafos_visitados jsonb DEFAULT '[]'::jsonb,
    itens_coletados jsonb DEFAULT '[]'::jsonb,
    decisoes jsonb DEFAULT '{}'::jsonb,
    hp_atual integer,
    hp_maximo integer,
    energia integer DEFAULT 10,
    ouro integer DEFAULT 0,
    iniciado_em timestamp without time zone DEFAULT now(),
    ultima_acao timestamp without time zone DEFAULT now(),
    finalizado boolean DEFAULT false,
    final_alcancado character varying(50)
);


ALTER TABLE public.aventuras_progresso OWNER TO rpg;

--
-- Name: aventuras_progresso_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.aventuras_progresso_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.aventuras_progresso_id_seq OWNER TO rpg;

--
-- Name: aventuras_progresso_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.aventuras_progresso_id_seq OWNED BY public.aventuras_progresso.id;


--
-- Name: aventuras_stats; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.aventuras_stats (
    id integer NOT NULL,
    aventura_nome character varying(100),
    total_inicios integer DEFAULT 0,
    total_conclusoes integer DEFAULT 0,
    total_mortes integer DEFAULT 0,
    tempo_medio_minutos integer,
    paragrafo_mais_visitado integer,
    escolha_mais_comum jsonb,
    atualizado_em timestamp without time zone DEFAULT now()
);


ALTER TABLE public.aventuras_stats OWNER TO rpg;

--
-- Name: aventuras_stats_globais; Type: VIEW; Schema: public; Owner: rpg
--

CREATE VIEW public.aventuras_stats_globais AS
 SELECT count(DISTINCT jogador_id) AS total_jogadores,
    count(*) AS total_aventuras_iniciadas,
    sum(
        CASE
            WHEN finalizado THEN 1
            ELSE 0
        END) AS total_conclusoes,
    round(avg((EXTRACT(epoch FROM (ultima_acao - iniciado_em)) / (60)::numeric)), 0) AS tempo_medio_minutos
   FROM public.aventuras_progresso;


ALTER VIEW public.aventuras_stats_globais OWNER TO rpg;

--
-- Name: aventuras_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.aventuras_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.aventuras_stats_id_seq OWNER TO rpg;

--
-- Name: aventuras_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.aventuras_stats_id_seq OWNED BY public.aventuras_stats.id;


--
-- Name: bestiario_cidadela; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.bestiario_cidadela (
    nome character varying NOT NULL,
    ca integer,
    hp_max integer,
    ataque character varying,
    dano character varying,
    ouro_recompensa integer,
    xp_recompensa integer
);


ALTER TABLE public.bestiario_cidadela OWNER TO rpg;

--
-- Name: campanhas; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.campanhas (
    party_id character varying NOT NULL,
    host_id character varying NOT NULL,
    aventura_ativa character varying,
    estado_salas json,
    ultimo_evento json,
    momento character varying,
    tensao integer,
    turno_atual integer,
    em_combate boolean,
    fila_iniciativa json,
    indice_turno integer,
    cena_atual character varying,
    cena_anterior character varying,
    status character varying,
    votos_destino json,
    bolsa_da_party json
);


ALTER TABLE public.campanhas OWNER TO rpg;

--
-- Name: campanhas_cenas; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.campanhas_cenas (
    id integer NOT NULL,
    aventura_ref character varying(100) NOT NULL,
    cena_id character varying(50) NOT NULL,
    nome_local character varying(100) NOT NULL,
    descricao_narrativa text NOT NULL,
    regras_da_sala text NOT NULL,
    conexoes jsonb DEFAULT '[]'::jsonb
);


ALTER TABLE public.campanhas_cenas OWNER TO rpg;

--
-- Name: campanhas_cenas_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.campanhas_cenas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.campanhas_cenas_id_seq OWNER TO rpg;

--
-- Name: campanhas_cenas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.campanhas_cenas_id_seq OWNED BY public.campanhas_cenas.id;


--
-- Name: cenas; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.cenas (
    cod_sala character varying NOT NULL,
    nome_sala character varying,
    descricao_visual text,
    conexoes jsonb,
    imagem_url text,
    loot_fixo json DEFAULT '[]'::json,
    hazards json
);


ALTER TABLE public.cenas OWNER TO rpg;

--
-- Name: cenas_backup; Type: TABLE; Schema: public; Owner: user_8W2mTA
--

CREATE TABLE public.cenas_backup (
    cod_sala character varying,
    nome_sala character varying,
    descricao_visual text,
    conexoes json,
    imagem_url text,
    loot_fixo json
);


ALTER TABLE public.cenas_backup OWNER TO "user_8W2mTA";

--
-- Name: combate_states; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.combate_states (
    id integer NOT NULL,
    room_id character varying,
    party_id character varying,
    turn_index integer,
    round integer,
    status character varying,
    participants_order json,
    created_at character varying,
    updated_at character varying
);


ALTER TABLE public.combate_states OWNER TO rpg;

--
-- Name: combate_states_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.combate_states_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.combate_states_id_seq OWNER TO rpg;

--
-- Name: combate_states_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.combate_states_id_seq OWNED BY public.combate_states.id;


--
-- Name: criacao_ficha; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.criacao_ficha (
    telefone character varying(50) NOT NULL,
    etapa character varying(50) NOT NULL,
    dados_temp jsonb DEFAULT '{}'::jsonb,
    criado_em timestamp without time zone DEFAULT now(),
    atualizado_em timestamp without time zone DEFAULT now()
);


ALTER TABLE public.criacao_ficha OWNER TO rpg;

--
-- Name: diario_thorak; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.diario_thorak (
    id integer NOT NULL,
    data_hora timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    evento text,
    sala_atual character varying(50),
    hp_restante integer
);


ALTER TABLE public.diario_thorak OWNER TO rpg;

--
-- Name: diario_thorak_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.diario_thorak_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.diario_thorak_id_seq OWNER TO rpg;

--
-- Name: diario_thorak_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.diario_thorak_id_seq OWNED BY public.diario_thorak.id;


--
-- Name: documentos_aventura; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.documentos_aventura (
    id integer NOT NULL,
    nome_item character varying(100),
    conteudo_texto text,
    sala_onde_encontra character varying(50)
);


ALTER TABLE public.documentos_aventura OWNER TO rpg;

--
-- Name: documentos_aventura_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.documentos_aventura_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.documentos_aventura_id_seq OWNER TO rpg;

--
-- Name: documentos_aventura_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.documentos_aventura_id_seq OWNED BY public.documentos_aventura.id;


--
-- Name: encontros; Type: TABLE; Schema: public; Owner: user_8W2mTA
--

CREATE TABLE public.encontros (
    id integer NOT NULL,
    cod_sala character varying NOT NULL,
    quantidade integer NOT NULL,
    condicao_aparecimento character varying DEFAULT 'sempre'::character varying,
    ativo boolean DEFAULT true,
    nome_inimigo character varying,
    dificuldade character varying,
    item_drop character varying,
    multiplicador_ameaca integer DEFAULT 1
);


ALTER TABLE public.encontros OWNER TO "user_8W2mTA";

--
-- Name: encontros_aleatorios; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.encontros_aleatorios (
    id integer NOT NULL,
    cod_sala character varying,
    nome_inimigo character varying,
    quantidade integer,
    chance integer
);


ALTER TABLE public.encontros_aleatorios OWNER TO rpg;

--
-- Name: encontros_aleatorios_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.encontros_aleatorios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.encontros_aleatorios_id_seq OWNER TO rpg;

--
-- Name: encontros_aleatorios_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.encontros_aleatorios_id_seq OWNED BY public.encontros_aleatorios.id;


--
-- Name: encontros_id_seq; Type: SEQUENCE; Schema: public; Owner: user_8W2mTA
--

CREATE SEQUENCE public.encontros_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.encontros_id_seq OWNER TO "user_8W2mTA";

--
-- Name: encontros_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user_8W2mTA
--

ALTER SEQUENCE public.encontros_id_seq OWNED BY public.encontros.id;


--
-- Name: encontros_salas; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.encontros_salas (
    id integer NOT NULL,
    cod_sala character varying,
    nome_inimigo character varying,
    quantidade integer,
    condicao_aparecimento character varying,
    ativo boolean
);


ALTER TABLE public.encontros_salas OWNER TO rpg;

--
-- Name: z_old_encontros_salas; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.z_old_encontros_salas (
    id integer NOT NULL,
    cod_sala character varying,
    nome_inimigo character varying,
    quantidade integer,
    condicao_aparecimento character varying,
    ativo boolean
);


ALTER TABLE public.z_old_encontros_salas OWNER TO rpg;

--
-- Name: encontros_salas_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.encontros_salas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.encontros_salas_id_seq OWNER TO rpg;

--
-- Name: encontros_salas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.encontros_salas_id_seq OWNED BY public.z_old_encontros_salas.id;


--
-- Name: encontros_salas_id_seq1; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.encontros_salas_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.encontros_salas_id_seq1 OWNER TO rpg;

--
-- Name: encontros_salas_id_seq1; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.encontros_salas_id_seq1 OWNED BY public.encontros_salas.id;


--
-- Name: estatisticas_jogador; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.estatisticas_jogador (
    jogador_telefone character varying NOT NULL,
    inimigos_derrotados integer,
    vezes_derrotado integer,
    danos_causados_total integer,
    danos_recebidos_total integer,
    total_ataques_acertados integer,
    total_ataques_errados integer,
    criticos_acertados integer,
    fumbles_rolados integer,
    salas_visitadas json,
    salas_desbloqueadas_count integer,
    xp_ganho_total integer,
    ouro_ganho_total integer,
    ouro_perdido_total integer,
    testes_realizados integer,
    testes_sucesso integer,
    testes_falha integer,
    descansos_curtos integer,
    intervencoes_divinas integer,
    primeira_sessao character varying,
    ultima_sessao character varying,
    tempo_jogo_minutos integer
);


ALTER TABLE public.estatisticas_jogador OWNER TO rpg;

--
-- Name: estatisticas_jogadores; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.estatisticas_jogadores (
    jogador_telefone character varying NOT NULL,
    inimigos_derrotados integer,
    vezes_derrotado integer,
    total_ataques_acertados integer,
    total_ataques_errados integer,
    danos_causados_total integer,
    danos_recebidos_total integer,
    criticos_acertados integer,
    fumbles_rolados integer,
    salas_visitadas json,
    salas_desbloqueadas_count integer,
    xp_ganho_total integer,
    ouro_ganho_total integer,
    ouro_perdido_total integer,
    testes_realizados integer,
    testes_sucesso integer,
    testes_falha integer,
    descansos_curtos integer,
    intervencoes_divinas integer,
    primeira_sessao character varying,
    ultima_sessao character varying,
    tempo_jogo_minutos integer
);


ALTER TABLE public.estatisticas_jogadores OWNER TO rpg;

--
-- Name: grimorio_cidadela; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.grimorio_cidadela (
    id integer NOT NULL,
    nome_magia character varying(50),
    nivel integer,
    alcance character varying(30),
    efeito text
);


ALTER TABLE public.grimorio_cidadela OWNER TO rpg;

--
-- Name: grimorio_cidadela_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.grimorio_cidadela_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.grimorio_cidadela_id_seq OWNER TO rpg;

--
-- Name: grimorio_cidadela_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.grimorio_cidadela_id_seq OWNED BY public.grimorio_cidadela.id;


--
-- Name: historico_partidas; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.historico_partidas (
    id integer NOT NULL,
    jogador_telefone character varying,
    data_inicio character varying,
    data_fim character varying,
    resultado character varying,
    inimigos_derrotados integer,
    ouro_coletado integer,
    xp_ganho integer,
    sala_final character varying
);


ALTER TABLE public.historico_partidas OWNER TO rpg;

--
-- Name: historico_partidas_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.historico_partidas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.historico_partidas_id_seq OWNER TO rpg;

--
-- Name: historico_partidas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.historico_partidas_id_seq OWNED BY public.historico_partidas.id;


--
-- Name: inimigos; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.inimigos (
    id integer NOT NULL,
    nome character varying,
    hp_max integer,
    ca integer,
    ataque character varying,
    dano character varying,
    imagem_url character varying,
    xp_recompensa integer,
    ouro_recompensa integer,
    is_boss boolean DEFAULT false,
    loot_especial json DEFAULT '[]'::json
);


ALTER TABLE public.inimigos OWNER TO rpg;

--
-- Name: inimigos_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.inimigos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inimigos_id_seq OWNER TO rpg;

--
-- Name: inimigos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.inimigos_id_seq OWNED BY public.inimigos.id;


--
-- Name: interativos; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.interativos (
    id integer NOT NULL,
    cod_sala character varying,
    nome character varying,
    descricao text,
    tipo character varying,
    cd_teste integer,
    atributo_teste character varying,
    recompensa json,
    dano_falha integer,
    ativo boolean
);


ALTER TABLE public.interativos OWNER TO rpg;

--
-- Name: interativos_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.interativos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.interativos_id_seq OWNER TO rpg;

--
-- Name: interativos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.interativos_id_seq OWNED BY public.interativos.id;


--
-- Name: itens_magicos; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.itens_magicos (
    id integer NOT NULL,
    nome character varying(100),
    propriedades text,
    valor_ouro integer
);


ALTER TABLE public.itens_magicos OWNER TO rpg;

--
-- Name: itens_magicos_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.itens_magicos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.itens_magicos_id_seq OWNER TO rpg;

--
-- Name: itens_magicos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.itens_magicos_id_seq OWNED BY public.itens_magicos.id;


--
-- Name: jogadores; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.jogadores (
    telefone character varying NOT NULL,
    party_id character varying,
    cena_atual character varying,
    cena_anterior character varying,
    nome character varying,
    classe character varying,
    raca character varying,
    background character varying,
    nivel integer,
    xp integer,
    hp_atual integer,
    hp_maximo integer,
    str integer,
    dex integer,
    con integer,
    "int" integer,
    wis integer,
    cha integer,
    mod_str integer,
    mod_dex integer,
    mod_con integer,
    mod_int integer,
    mod_wis integer,
    mod_cha integer,
    modificador_ataque integer,
    modificador_defesa integer,
    proficiencia integer,
    arma_equipada character varying,
    armadura_equipada character varying,
    dano_dado character varying,
    mod_dano integer,
    gold integer,
    inventario json,
    slots_magia integer,
    slots_magia_max integer,
    descanso_curto_disponivel boolean,
    status_efeitos json,
    hit_dice_max integer,
    hit_dice_atual integer,
    sexo character varying DEFAULT 'Masculino'::character varying,
    descricao text
);


ALTER TABLE public.jogadores OWNER TO rpg;

--
-- Name: logs_navegacao; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.logs_navegacao (
    id integer NOT NULL,
    telefone character varying(20),
    sala_origem character varying(50),
    texto_digitado text,
    sala_destino character varying(50),
    sucesso boolean,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.logs_navegacao OWNER TO rpg;

--
-- Name: logs_navegacao_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.logs_navegacao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.logs_navegacao_id_seq OWNER TO rpg;

--
-- Name: logs_navegacao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.logs_navegacao_id_seq OWNED BY public.logs_navegacao.id;


--
-- Name: masmorra_cenas; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.masmorra_cenas (
    id integer NOT NULL,
    sala_id character varying(50),
    nome_sala character varying(100),
    descricao text,
    inimigos text,
    saidas text
);


ALTER TABLE public.masmorra_cenas OWNER TO rpg;

--
-- Name: masmorra_cenas_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.masmorra_cenas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.masmorra_cenas_id_seq OWNER TO rpg;

--
-- Name: masmorra_cenas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.masmorra_cenas_id_seq OWNED BY public.masmorra_cenas.id;


--
-- Name: missoes; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.missoes (
    id integer NOT NULL,
    jogador_telefone character varying,
    npc_nome character varying,
    titulo character varying,
    descricao text,
    objetivo_item character varying,
    objetivo_quantidade integer,
    recompensa_xp integer,
    recompensa_ouro integer,
    recompensa_item character varying,
    concluida boolean
);


ALTER TABLE public.missoes OWNER TO rpg;

--
-- Name: missoes_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.missoes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.missoes_id_seq OWNER TO rpg;

--
-- Name: missoes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.missoes_id_seq OWNED BY public.missoes.id;


--
-- Name: monster_templates; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.monster_templates (
    id integer NOT NULL,
    nome character varying(100),
    hp_base integer,
    ca integer,
    ataque_bonus integer,
    dano_dice character varying(20),
    xp integer
);


ALTER TABLE public.monster_templates OWNER TO rpg;

--
-- Name: monster_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.monster_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.monster_templates_id_seq OWNER TO rpg;

--
-- Name: monster_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.monster_templates_id_seq OWNED BY public.monster_templates.id;


--
-- Name: npcs; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.npcs (
    id integer NOT NULL,
    cod_sala character varying,
    nome character varying,
    descricao text,
    dialogo_base text,
    dialogo_item_especial text,
    item_gatilho character varying
);


ALTER TABLE public.npcs OWNER TO rpg;

--
-- Name: npcs_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.npcs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.npcs_id_seq OWNER TO rpg;

--
-- Name: npcs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.npcs_id_seq OWNED BY public.npcs.id;


--
-- Name: objetos_destrutiveis; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.objetos_destrutiveis (
    id integer NOT NULL,
    cod_sala character varying,
    nome character varying,
    descricao text,
    hp_atual integer,
    hp_max integer,
    ca integer,
    break_threshold integer,
    resistencias json,
    vulnerabilidades json,
    recompensa_ao_destruir json,
    ativo boolean
);


ALTER TABLE public.objetos_destrutiveis OWNER TO rpg;

--
-- Name: objetos_destrutiveis_id_seq; Type: SEQUENCE; Schema: public; Owner: rpg
--

CREATE SEQUENCE public.objetos_destrutiveis_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.objetos_destrutiveis_id_seq OWNER TO rpg;

--
-- Name: objetos_destrutiveis_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rpg
--

ALTER SEQUENCE public.objetos_destrutiveis_id_seq OWNED BY public.objetos_destrutiveis.id;


--
-- Name: regras_cache; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.regras_cache (
    nome character varying(200) NOT NULL,
    openai_file_id character varying(100) NOT NULL,
    atualizado_em timestamp without time zone DEFAULT now()
);


ALTER TABLE public.regras_cache OWNER TO rpg;

--
-- Name: turnos; Type: TABLE; Schema: public; Owner: rpg
--

CREATE TABLE public.turnos (
    grupo_id character varying(100) NOT NULL,
    indice integer DEFAULT 0
);


ALTER TABLE public.turnos OWNER TO rpg;

--
-- Name: aliados_e_npcs id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aliados_e_npcs ALTER COLUMN id SET DEFAULT nextval('public.aliados_e_npcs_id_seq'::regclass);


--
-- Name: aventuras_catalogo id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_catalogo ALTER COLUMN id SET DEFAULT nextval('public.aventuras_catalogo_id_seq'::regclass);


--
-- Name: aventuras_inventario id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_inventario ALTER COLUMN id SET DEFAULT nextval('public.aventuras_inventario_id_seq'::regclass);


--
-- Name: aventuras_paragrafos id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_paragrafos ALTER COLUMN id SET DEFAULT nextval('public.aventuras_paragrafos_id_seq'::regclass);


--
-- Name: aventuras_progresso id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_progresso ALTER COLUMN id SET DEFAULT nextval('public.aventuras_progresso_id_seq'::regclass);


--
-- Name: aventuras_stats id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_stats ALTER COLUMN id SET DEFAULT nextval('public.aventuras_stats_id_seq'::regclass);


--
-- Name: campanhas_cenas id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.campanhas_cenas ALTER COLUMN id SET DEFAULT nextval('public.campanhas_cenas_id_seq'::regclass);


--
-- Name: combate_states id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.combate_states ALTER COLUMN id SET DEFAULT nextval('public.combate_states_id_seq'::regclass);


--
-- Name: diario_thorak id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.diario_thorak ALTER COLUMN id SET DEFAULT nextval('public.diario_thorak_id_seq'::regclass);


--
-- Name: documentos_aventura id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.documentos_aventura ALTER COLUMN id SET DEFAULT nextval('public.documentos_aventura_id_seq'::regclass);


--
-- Name: encontros id; Type: DEFAULT; Schema: public; Owner: user_8W2mTA
--

ALTER TABLE ONLY public.encontros ALTER COLUMN id SET DEFAULT nextval('public.encontros_id_seq'::regclass);


--
-- Name: encontros_aleatorios id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.encontros_aleatorios ALTER COLUMN id SET DEFAULT nextval('public.encontros_aleatorios_id_seq'::regclass);


--
-- Name: encontros_salas id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.encontros_salas ALTER COLUMN id SET DEFAULT nextval('public.encontros_salas_id_seq1'::regclass);


--
-- Name: grimorio_cidadela id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.grimorio_cidadela ALTER COLUMN id SET DEFAULT nextval('public.grimorio_cidadela_id_seq'::regclass);


--
-- Name: historico_partidas id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.historico_partidas ALTER COLUMN id SET DEFAULT nextval('public.historico_partidas_id_seq'::regclass);


--
-- Name: inimigos id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.inimigos ALTER COLUMN id SET DEFAULT nextval('public.inimigos_id_seq'::regclass);


--
-- Name: interativos id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.interativos ALTER COLUMN id SET DEFAULT nextval('public.interativos_id_seq'::regclass);


--
-- Name: itens_magicos id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.itens_magicos ALTER COLUMN id SET DEFAULT nextval('public.itens_magicos_id_seq'::regclass);


--
-- Name: logs_navegacao id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.logs_navegacao ALTER COLUMN id SET DEFAULT nextval('public.logs_navegacao_id_seq'::regclass);


--
-- Name: masmorra_cenas id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.masmorra_cenas ALTER COLUMN id SET DEFAULT nextval('public.masmorra_cenas_id_seq'::regclass);


--
-- Name: missoes id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.missoes ALTER COLUMN id SET DEFAULT nextval('public.missoes_id_seq'::regclass);


--
-- Name: monster_templates id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.monster_templates ALTER COLUMN id SET DEFAULT nextval('public.monster_templates_id_seq'::regclass);


--
-- Name: npcs id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.npcs ALTER COLUMN id SET DEFAULT nextval('public.npcs_id_seq'::regclass);


--
-- Name: objetos_destrutiveis id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.objetos_destrutiveis ALTER COLUMN id SET DEFAULT nextval('public.objetos_destrutiveis_id_seq'::regclass);


--
-- Name: z_old_encontros_salas id; Type: DEFAULT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.z_old_encontros_salas ALTER COLUMN id SET DEFAULT nextval('public.encontros_salas_id_seq'::regclass);


--
-- Data for Name: aliados_e_npcs; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.aliados_e_npcs (id, nome, raca_classe, hp_atual, tendencia, notas_personalidade) FROM stdin;
1	Meepo	Kobold	2	Leal e Neutro	Obcecado por dragões. Chora com facilidade. Quer ser amigo de quem o ajudar a achar Calcryx.
2	Erky Timbers	Gnomo Clérigo	8	Bom e Neutro	Prisioneiro dos Goblins (Área 18/34 dependendo da versão). Pode curar o Thorak se for libertado.
3	Sharwyn Hucrele	Humana Maga	7	Suplantada (Mal)	Filha de Kerowyn. Foi transformada em serva da árvore. Possui uma varinha de mísseis mágicos.
\.


--
-- Data for Name: aventura_cidadela; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.aventura_cidadela (cod_sala, nome_sala, descricao_visual, segredos_mestre, conexoes) FROM stdin;
carvalhal	Vila de Carvalhal	A Vila de Carvalhal pulsa com uma tensão silenciosa. Aldeões olham desconfiados através de janelas de madeira húmida, enquanto a fumaça das chaminés se mistura com a névoa perpétua. A Taverna do Velho Javali é o único lugar que parece oferecer algum calor real.		{"norte": "estrada_velha"}
estrada_velha	Estrada Velha	Uma trilha desolada e esquecida. Árvores retorcidas de galhos secos como garras observam o seu avanço. O vento aqui não canta, ele apenas sibila entre os troncos podres, cheirando a abandono e folhas mortas.		{"sul": "carvalhal", "norte": "ravina_escura"}
ravina_escura	Área 0: Ravina	A terra abre-se numa fenda monumental, como se o mundo tivesse sido partido ao meio. Uma corda grossa, ancorada a um pilar de pedra rachada, desce rumo às profundezas onde a luz do sol não ousa entrar.		{"sul": "estrada_velha", "descer": "sala_01"}
sala_01	Área 1: Parapeito	Você aterra num parapeito estreito. O ar é gélido, cheirando a pó e pedra molhada. Nas sombras, o som de garras arranhando a rocha ecoa suavemente, anunciando que você não está sozinho.		{"subir": "ravina_escura", "oeste": "sala_02"}
sala_02	Área 2: Escadas Sinuosas	Uma escadaria de pedra em zigue-zague desce ainda mais para a escuridão. Os degraus estão irregulares e perigosos, cobertos por um musgo escorregadio e poças de água negra.		{"leste": "sala_01", "baixo": "sala_03"}
sala_03	Área 3: Pátio em Ruínas	O pátio de um antigo castelo que se afundou na terra. Paredes de granito destroçadas formam um anel ao redor de escombros. Estátuas sem cabeça de heróis do passado permanecem como sentinelas tristes no escuro.		{"cima": "sala_02", "oeste": "sala_04", "norte": "sala_07"}
sala_04	Área 4: Torre em Ruínas	Uma torre circular em ruínas. O teto desabou há séculos. No chão, quatro corpos de goblins em decomposição jazem espalhados; um deles está bizarramente empalado contra a parede oeste por uma lança ferrugenta.		{"leste": "sala_03"}
sala_05	Área 5: Corredor de Entrada	Uma pequena câmara secreta, abafada e com cheiro a ar preso há séculos. Teias de aranha grossas como cordas pendem do teto, escondendo cantos obscuros.		{"norte": "sala_07"}
sala_06	Área 6: Antessala Velha	Uma antessala fria com portas de pedra pesada. O silêncio aqui é perturbador, quebrado apenas pelo som da sua própria respiração e pelo gotejar distante de água.		{"leste": "sala_07"}
sala_07	Área 7: Galeria das Estátuas	A Galeria das Estátuas. Um longo corredor flanqueado por colunas esculpidas com a forma de dragões em voo. O chão está coberto por uma poeira espessa, ocultando perigos antigos.		{"sul": "sala_03", "leste": "sala_21", "oeste": "sala_06", "norte": "sala_08"}
sala_08	Área 8: Sala de Pressão	O corredor afunila. Há manchas escuras no chão de pedra que lembram sangue seco. Uma placa de pressão ligeiramente elevada no centro da sala sugere uma armadilha mecânica adormecida.		{"sul": "sala_07", "norte": "sala_09"}
sala_09	Área 9: Sala da Serpente	A Câmara da Serpente. Uma porta de pedra maciça bloqueia o caminho, entalhada com o formato de um dragão enrolado. Há um enigma dracónico desgastado gravado na base da porta.		{"sul": "sala_08", "leste": "sala_10"}
sala_10	Área 10: Corredor Estrito	O Corredor da Guarda de Honra. Nichos nas paredes contêm armaduras enferrujadas e vazias, de pé em posição de sentido. Elas parecem observar quem quer que passe por ali.		{"oeste": "sala_09", "norte": "sala_12"}
sala_11	Área 11: Câmara Secundária	Uma câmara secundária esquecida. Caixotes apodrecidos e barris desfeitos em lascas espalham-se pelo chão. O ar aqui tem o gosto amargo de bolor.		{"voltar": "sala_03"}
sala_12	Área 12: Tumba de Honorável	A Tumba do Sacerdote Dragão. Uma câmara silenciosa com um sarcófago de mármore liso no centro. Inscrições antigas em dracónico alertam severamente sobre a maldição dos violadores de tumbas.		{"sul": "sala_10"}
sala_13	Área 13: Câmara Secundária	Um corredor estreito e escuro. As paredes de granito estão cobertas de fungos cinzentos que parecem pulsar levemente quando você se aproxima.		{"voltar": "sala_03"}
sala_14	Área 14: Câmara Secundária	A câmara está parcialmente inundada com uma água escura e fétida, na altura dos tornozelos. O som de respingos ecoa, como se algo escorregadio nadasse nas sombras aquáticas.		{"voltar": "sala_03"}
sala_15	Área 15: Câmara Secundária	O posto de guarda Kobold. Fogueiras pequenas iluminam o rosto de criaturas reptilianas encolhidas em cantos, segurando lanças afiadas. O cheiro de carne queimada é forte.		{"voltar": "sala_03"}
sala_16	Área 16: Câmara Secundária	A Sala das Correntes. Uma cela reforçada onde enormes anéis de ferro pendem das paredes. O ar é incrivelmente frio aqui, e as paredes estão cobertas por uma fina camada de gelo.		{"voltar": "sala_03"}
sala_17	Área 17: Câmara Secundária	Um salão de transição longo. Peles de animais manchadas de sangue cobrem algumas passagens. O som de vozes esganiçadas e risadas cruéis reverbera mais adiante.		{"voltar": "sala_03"}
sala_18	Área 18: Câmara Secundária	Um cruzamento de corredores guardado por barricadas improvisadas com mesas quebradas. Kobolds nervosos patrulham a área, mantendo as armas em punho.		{"voltar": "sala_03"}
sala_19	Área 19: Câmara Secundária	Os quarteirões da tribo Kobold. Dezenas de ninhos de palha e tecido rasgado espalham-se pelo chão. O ruído constante de resmungos e dentes a ranger enche o ambiente.		{"voltar": "sala_03"}
sala_20	Área 20: Câmara Secundária	A antessala real. Cortinas rasgadas de veludo vermelho tentam, sem sucesso, dar um ar de nobreza a esta caverna fria.		{"voltar": "sala_03"}
sala_21	Área 21: Trono Kobold	O grande salão do trono. A líder kobold, Yusdrayl, majestosa e ameaçadora, governa o seu clã sentada num trono construído com blocos de altar roubados e ossos polidos.		{"oeste": "sala_07", "norte": "sala_26"}
sala_22	Área 22: Câmara Secundária	A antiga prisão. As grades de ferro estão tortas, algumas arrancadas das dobradiças. Restos de esqueletos humanoides jazem esquecidos nas celas mais escuras.		{"voltar": "sala_03"}
sala_23	Área 23: Câmara Secundária	Um santuário menor desconsagrado. O altar de pedra foi vandalizado com sangue goblin, e símbolos de crueldade foram pintados sobre os relevos sagrados originais.		{"voltar": "sala_03"}
sala_24	Área 24: Câmara Secundária	Um laboratório alquímico destruído. Vidros quebrados, cinzas e manchas químicas coloridas decoram o chão. Um odor metálico irrita a garganta.		{"voltar": "sala_03"}
sala_25	Área 25: Câmara Secundária	A antiga armaria. Prateleiras de madeira podre alinham as paredes. Quase tudo de valor já foi saqueado, restando apenas lanças partidas e escudos rachados.		{"voltar": "sala_03"}
sala_26	Área 26: Fronteira Goblin	Uma fonte circular de pedra, completamente seca. No centro, a estátua de um dragão com a boca aberta serve de poleiro para estranhos morcegos sem olhos.		{"sul": "sala_21", "norte": "sala_33"}
sala_27	Área 27: Câmara Secundária	Uma sala de descanso em ruínas. Bancos de pedra estão virados e marcados por garras profundas. O chão é uma cama de poeira inexplorada.		{"voltar": "sala_03"}
sala_28	Área 28: Câmara Secundária	O Corredor das Gárgulas. Figuras monstruosas de pedra observam do alto das paredes. A sensação de estar sendo vigiado é angustiante.		{"voltar": "sala_03"}
sala_29	Área 29: Câmara Secundária	Um fosso seco corta o caminho. Uma tábua de madeira bamba e podre serve como única ponte para o lado goblin da cidadela.		{"voltar": "sala_03"}
sala_30	Área 30: Câmara Secundária	Um posto avançado Goblin. Ossos de pequenos animais formam decorações macabras penduradas no teto. O fedor de goblin não lavado é esmagador.		{"voltar": "sala_03"}
sala_31	Área 31: Câmara Secundária	Um corredor estreito e traiçoeiro. Existem frestas suspeitas nas paredes de pedra, um clássico indício de armadilhas com flechas prontas a disparar.		{"voltar": "sala_03"}
sala_32	Área 32: Câmara Secundária	A Câmara dos Espinhos. O chão cede para um buraco escuro cheio de lanças e galhos afiados. É preciso cuidado extremo para navegar por aqui.		{"voltar": "sala_03"}
sala_33	Área 33: Quartéis Goblin	O Quartel General Goblin. O cheiro é insuportável. Camas de palha imunda e lixo espalhado mostram que dezenas de goblins vivem, comem e lutam neste salão caótico.		{"sul": "sala_26", "norte": "sala_41"}
sala_34	Área 34: Câmara Secundária	A cozinha imunda dos goblins. Caldeirões fervem com carnes não identificáveis. O vapor engordurado mancha as paredes de preto.		{"voltar": "sala_03"}
sala_35	Área 35: Câmara Secundária	A despensa dos horrores. Barris quebrados e sacos roídos por ratos alinham as prateleiras. Pequenos vermes movem-se na penumbra.		{"voltar": "sala_03"}
sala_36	Área 36: Câmara Secundária	A prisão goblin. Cordas e correntes estão presas a argolas no chão. Marcas de desespero nas paredes mostram onde prisioneiros tentaram, em vão, escapar.		{"voltar": "sala_03"}
sala_37	Área 37: Câmara Secundária	A sala de troféus. Crânios de diversas criaturas, incluindo alguns anões e elfos, estão empalados em estacas. O ambiente exala brutalidade selvagem.		{"voltar": "sala_03"}
sala_38	Área 38: Câmara Secundária	O salão da guarda de elite. Goblins com armaduras mais limpas (ou menos sujas) montam guarda aqui. A disciplina entre eles é mantida pelo medo.		{"voltar": "sala_03"}
sala_39	Área 39: Câmara Secundária	Câmara de interrogatório. Ferramentas cruéis pendem das paredes. No centro, uma mesa de pedra está impregnada de escuridão e manchas inquietantes.		{"voltar": "sala_03"}
sala_40	Área 40: Câmara Secundária	O Santuário de Maglubiyet. Ídolos macabros de barro e sangue adornam a parede. Uma fumaça de incenso nauseabundo queima lentamente num braseiro enferrujado.		{"voltar": "sala_03"}
sala_41	Área 41: Trono de Durnn	O covil de Durnn, o cruel Chefe Goblin. Troféus de heróis caídos estão amontoados. No fundo da sala, um poço perfeitamente cilíndrico mergulha nas profundezas escuras da terra.		{"sul": "sala_33", "baixo": "sala_42"}
sala_42	Área 42: Pilares Enraizados	Você chega ao Nível do Bosque Inferior. O teto aqui é sustentado por pilares que parecem árvores petrificadas, envoltas em raízes cinzentas que parecem vivas e pulsantes.		{"cima": "sala_41", "norte": "sala_43"}
sala_43	Área 43: Corredor de Musgo	Um corredor coberto de fungos fosforescentes. A luz verde pálida ilumina esporos que dançam no ar frio, dando uma sensação de irrealidade ao ambiente.		{"sul": "sala_42", "norte": "sala_49"}
sala_44	Área 44: Câmara Secundária	A caverna dos insetos. O chão está coberto de exoesqueletos esmagados e terra remexida. Zumbidos graves podem ser ouvidos vindos de fissuras nas rochas.		{"voltar": "sala_03"}
sala_45	Área 45: Câmara Secundária	O início do Bosque das Sombras. Árvores retorcidas crescem na escuridão subterrânea sem precisar de sol, alimentando-se apenas da energia mágica do local.		{"voltar": "sala_03"}
sala_46	Área 46: Câmara Secundária	Um santuário engolido por vinhas espinhosas. Restos de uma divindade silvestre jazem quebrados sob uma cama de mato grosso e hostil.		{"voltar": "sala_03"}
sala_47	Área 47: Câmara Secundária	A Passagem Entrelaçada. Raízes grossas como troncos bloqueiam metade do caminho, forçando-o a espremer-se entre a casca áspera que parece sangrar seiva vermelha.		{"voltar": "sala_03"}
sala_48	Área 48: Câmara Secundária	A caverna do musgo gigante. Tapetes de musgo amarelo e púrpura cobrem tudo, macios como almofadas, mas exalam um gás com cheiro a podridão doce.		{"voltar": "sala_03"}
sala_49	Área 49: Jardim Crepuscular	O Jardim Crepuscular. Uma área agrícola bizarra. O solo foi arado, mas as plantas que aqui crescem são pálidas, venenosas e cheias de espinhos. Arbustos secos tremem sem vento.		{"sul": "sala_43", "oeste": "sala_53", "norte": "sala_56"}
sala_50	Área 50: Câmara Secundária	A estufa macabra. Parede de pedras desabadas formam um canto escuro onde mudas de plantas trepadeiras parecem esticar as folhas em direção ao calor do seu corpo.		{"voltar": "sala_03"}
sala_51	Área 51: Câmara Secundária	A biblioteca em ruínas de Belak. Pilhas de livros apodrecidos e pergaminhos esfarelados sobre rituais druídicos sombrios forram o chão úmido.		{"voltar": "sala_03"}
sala_52	Área 52: Câmara Secundária	Os aposentos espartanos do Druida. Uma cama de folhas secas, uma bacia de pedra com água estagnada e símbolos de pura obsessão rúnica desenhados nas paredes.		{"voltar": "sala_03"}
sala_53	Área 53: Lab de Belak	O laboratório botânico profano. Mesas de madeira vergadas sob o peso de frascos esguios, ervas trituradas e anotações frenéticas sobre enxertos de sangue e raízes vampíricas.		{"leste": "sala_49"}
sala_54	Área 54: Câmara Secundária	A Gruta Lamacenta. O chão transforma-se num pântano subterrâneo profundo e nojento. O coaxar baixo e gutural de anfíbios gigantes ressoa nas paredes da caverna.		{"voltar": "sala_03"}
sala_55	Área 55: Câmara Secundária	A Clareira Inferior. O ar aqui é sufocante e pesado com o cheiro de seiva mágica. O ambiente é tenso, como se o próprio chão estivesse a prender a respiração para o que está à frente.		{"voltar": "sala_03"}
sala_56	Área 56: Árvore de Gulthias	O Coração do Mal. No centro da clareira final, ergue-se a colossal Árvore de Gulthias — uma abominação de madeira negra que bebe sangue em vez de água. Belak, o Proscrito, aguarda nas suas sombras.		{"sul": "sala_49"}
\.


--
-- Data for Name: aventuras; Type: TABLE DATA; Schema: public; Owner: user_8W2mTA
--

COPY public.aventuras (id, nome, prologo) FROM stdin;
cidadela	A Cidadela Sem Sol	As nuvens cinzentas se acumulam sobre a Vila de Carvalhal. O ferreiro local treme ao mencionar os túneis sob a ravina. Crianças desapareceram na noite passada, e o Conselho pede heróis. Armado e determinado, você é a última esperança.
phandelver	A Mina Perdida de Phandelver	O anão Gundren Buscapedra, seu velho amigo, contratou-o para escoltar uma carroça de suprimentos até a vila de Phandalin. "É o trabalho mais importante da minha vida!" — ele disse, os olhos brilhando. Mas ao chegar à Estrada de Triboar, você encontra apenas destruição: a carroça está revirada, os cavalos mortos por flechas goblin, e Gundren desapareceu.
\.


--
-- Data for Name: aventuras_catalogo; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.aventuras_catalogo (id, nome, titulo, descricao, autor, dificuldade, nivel_recomendado, paragrafo_inicial, total_paragrafos, tempo_estimado_minutos, ativa, criado_em) FROM stdin;
1	templo-do-terror	O Templo do Terror	Uma jornada épica para recuperar cinco artefatos dragões roubados pelo maligno Malbordus. Atravesse o Porto de Craggen, navegue pela Costa Selvagem e infiltre-se no sinistro Templo do Terror.	Ian Livingstone	dificil	1-10	1	400	120	t	2026-02-18 21:38:03.647939
\.


--
-- Data for Name: aventuras_inventario; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.aventuras_inventario (id, progresso_id, item_nome, item_tipo, quantidade, descricao, paragrafo_obtido, usado) FROM stdin;
\.


--
-- Data for Name: aventuras_paragrafos; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.aventuras_paragrafos (id, aventura_nome, numero, texto, opcoes, tipo, requer_teste, teste_atributo, teste_dificuldade, sucesso_paragrafo, falha_paragrafo, imagem_url) FROM stdin;
1	templo-do-terror	1	Para um homem velho, Yaztromo é surpreendentemente vivaz. Você atravessa Red River e os campos arados além, o logo chega ao limite de Port Blacksand. Yaztromo continua. Toma um caminho estreito em direção à escura muralha de árvores. Está escurecendo; raízes emaranhadas obstruem a passagem e tornam a caminhada muito cansativa. Você pergunta a Yaztromo por que ele parece tão despreocupado em relação à possibilidade de ser atacado pelos monstros da floresta. Ele ironiza e diz que sua magia é bem conhecida e respeitada por todas as criaturas numa área de muitas milhas - ninguém ousaria desafiar Yaztromo! Depois de passar a calma noite na floresta, você sobe a torre de Yaztromo no meio da manhã do dia seguinte. Você o segue pela escadaria em caracol até uma ampla sala no topo da torre. Prateleiras, cristaleiras e armários se espalham pelas paredes, cheios de garrafas, potes de vidro e livros, caixas e toda variedade de estranhos objetos. Yaztromo cai sentado na sua velha cadeira de carvalho, parecendo momentaneamente muito cansado e de longa jornada. Ele põe a mão no bolso e tira dali um delicado par de óculos de armação de ouro. Depois de colocá-los no nariz, ele observa você furtivamente sobre eles, e você se sente bastante intimidado com aquele olhar penetrante. Finalmente, ele diz: "Qualquer um que espere derrotar Malbordus tem que conhecer um mínimo de magia. Você parece bastante inteligente para aprender mas não acho que tenha tempo suficiente para absorver os dez encantos que possuía de ensinar a você. Falando nisso, gostaria que você compreendesse o quanto é privilegiado por poder aprender minha magia. Mas uma crise é uma crise. Agora, vamos começar. Que encantos devo ensinar? Você pode optar pelo encanto de Abrir Portas, do Sono das Criaturas, da Flecha Mágica, do Idioma, de Ler Símbolos, da Luz, do Fogo, de Saltar, de Detectar Armadilha e de Criar Água."	[{"texto": "Abrir Portas", "numero": 1, "paragrafo": 12}, {"texto": "Sono das Criaturas", "numero": 2, "paragrafo": 58}, {"texto": "Flecha Mágica", "numero": 3, "paragrafo": 136}, {"texto": "Idioma", "numero": 4, "paragrafo": 194}, {"texto": "Ler Símbolos", "numero": 5, "paragrafo": 391}, {"texto": "Luz", "numero": 6, "paragrafo": 223}, {"texto": "Fogo", "numero": 7, "paragrafo": 264}, {"texto": "Saltar", "numero": 8, "paragrafo": 301}, {"texto": "Detectar Armadilha", "numero": 9, "paragrafo": 342}, {"texto": "Criar Água", "numero": 10, "paragrafo": 367}]	normal	f	\N	\N	\N	\N	\N
2	templo-do-terror	58	Yaztromo explica que seu encanto do Sono das Criaturas fará dormir qualquer criatura humanoide. Ele conta para você as palavras necessárias para lançar o encanto e diz que ele praticamente nada exigirá de suas forças, somente 1 ponto de ENERGIA a cada vez que você o utilizar. Volte para 34, depois de ter anotado o encanto e seu custo em ENERGIA na sua Folha de Aventuras.	[{"texto": "Voltar e escolher outro encanto", "numero": 1, "paragrafo": 34}]	normal	f	\N	\N	\N	\N	\N
\.


--
-- Data for Name: aventuras_progresso; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.aventuras_progresso (id, jogador_id, aventura_nome, paragrafo_atual, paragrafos_visitados, itens_coletados, decisoes, hp_atual, hp_maximo, energia, ouro, iniciado_em, ultima_acao, finalizado, final_alcancado) FROM stdin;
1	123456	templo-do-terror	1	[1]	[]	{}	\N	\N	10	0	2026-02-18 21:45:31.209504	2026-02-18 21:45:31.209504	f	\N
2	5326646936	templo-do-terror	34	[1, 58, 34]	[]	{}	\N	\N	10	0	2026-02-18 22:53:36.687921	2026-02-18 23:09:06.777844	f	\N
\.


--
-- Data for Name: aventuras_stats; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.aventuras_stats (id, aventura_nome, total_inicios, total_conclusoes, total_mortes, tempo_medio_minutos, paragrafo_mais_visitado, escolha_mais_comum, atualizado_em) FROM stdin;
\.


--
-- Data for Name: bestiario_cidadela; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.bestiario_cidadela (nome, ca, hp_max, ataque, dano, ouro_recompensa, xp_recompensa) FROM stdin;
Rato Atroz	12	7	+4	1d4+2	0	25
Rato Atroz (Gutash)	13	18	+4	1d6+2	0	50
Kobold Sentinela	12	5	+4	1d4+2	3	25
Yusdrayl (Feiticeira)	12	27	+4	1d4+2	30	450
Goblin Salteador	15	7	+4	1d6+2	3	50
Robgoblin Guerreiro	18	11	+3	1d8+1	5	100
Durnn (Chefe Goblin)	17	16	+5	2d6+3	25	700
Balsag (Bugbear)	16	27	+4	2d8+2	20	700
Bugbear Jardineiro	16	27	+4	2d8+2	8	200
Esqueleto Guardião	13	13	+4	1d6+2	2	50
Ramo Seco	13	4	+3	1d4+1	0	25
Thoqqua	20	16	+5	1d8+4	0	200
Calcryx (Filhote Dragão)	17	33	+4	1d10+2	0	700
Jot (Quasit)	13	7	+4	1d4+3	10	100
Sacerdote-Troll	15	84	+7	1d8+4	15	200
Sir Bradford (Corrompido)	18	25	+6	1d10+3	40	700
Sharwyn (Corrompida)	12	20	+4	1d6+2	40	700
Belak o Proscrito	12	40	+3	1d6+1	80	1800
\.


--
-- Data for Name: campanhas; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.campanhas (party_id, host_id, aventura_ativa, estado_salas, ultimo_evento, momento, tensao, turno_atual, em_combate, fila_iniciativa, indice_turno, cena_atual, cena_anterior, status, votos_destino, bolsa_da_party) FROM stdin;
PTY-90A7Y	5326646936	cidadela	{"ca_alvo": 10, "hp_40": -2, "derrotado_40": true}	{}	inicio	0	1	f	[]	0	sala_03	sala_02	exploracao	{}	{"ouro": 0, "itens": []}
\.


--
-- Data for Name: campanhas_cenas; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.campanhas_cenas (id, aventura_ref, cena_id, nome_local, descricao_narrativa, regras_da_sala, conexoes) FROM stdin;
1	cidadela_sem_sol	carvalhal	Vila de Carvalhal	A aventura se inicia na vila de Carvalhal, um local marcado por um ciclo de mortes misteriosas durante o solstício de inverno. Há uma Estalagem chamada Javali Véio, um empório e um pequeno posto da guarda. Os moradores estão assustados e desconfiados. Rumores falam sobre o desaparecimento dos irmãos Talgen e Sharwyn Hucrele nas ruínas próximas.	REGRA DE OURO DA CENA: ESTA É UMA ZONA SEGURA (TOWN). SOB NENHUMA HIPÓTESE INICIE COMBATE AQUI, MESMO QUE OS JOGADORES SEJAM AGRESSIVOS. Se tentarem brigar, narre que a guarda municipal interveio. Foco absoluto em interpretação (roleplay), entregar rumores na estalagem e guiá-los para a Ravina que leva à Cidadela.	["ravina_entrada"]
\.


--
-- Data for Name: cenas; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.cenas (cod_sala, nome_sala, descricao_visual, conexoes, imagem_url, loot_fixo, hazards) FROM stdin;
carvalhal	Vila de Carvalhal (Oakhurst)	A pequena vila de Oakhurst ergue-se precariamente na borda da ravina. O ar é frio e o cheiro de fumaça de lareira preenche as ruas lamacentas. Aldeões desconfiados observam através de janelas. A Taverna do Velho Javali é o único lugar que parece oferecer algum calor real.	{"norte": "estrada_velha"}	AgACAgEAAxkDAAIWzmnupRqCweTxgq8Iu3kpUecvOtktAAKODGsbd6B4Rw1I_bFlkFC3AQADAgADeQADOwQ	[]	\N
estrada_velha	A Estrada Velha	Uma trilha de pedras arruinadas que serpenteia por quilômetros. Árvores retorcidas de galhos secos como garras observam seu avanço. O silêncio é interrompido apenas pelo vento. Carvalhos antigos formam uma abóbada sombria sobre o caminho.	{"sul": "carvalhal", "norte": "ravina_escura"}	AgACAgEAAxkDAAIVhWntJGAecZP5Z8DMt-eHF5A--aToAAIrDGsb_VNxR8WO3fkXKFqVAQADAgADeQADOwQ	[]	\N
ravina_escura	Área 0: A Ravina	Uma fenda profunda e estreita abre-se na terra como uma cicatriz. Dois pilares de pedra ainda estão de pé, mas a maioria está inclinada para o abismo. Uma corda grossa com nós, amarrada a um pilar, desce 15 metros até a escuridão abaixo. Marcas de pés goblin estão gravadas na face do rochedo.	{"sul": "estrada_velha", "descer": "sala_01"}	AgACAgEAAxkDAAIViGntJLKecU9r-ehv3Bblc3imgZHuAAIsDGsb_VNxR41Y5jQYJXx4AQADAgADeQADOwQ	[]	\N
sala_01	Área 1: O Parapeito	Um parapeito de areia domina um golfo subterrâneo de escuridão a oeste. Areia, pedregulhos e ossos de pequenos animais recobrem o solo. Uma escada talhada na pedra serpenteia pela lateral, descendo às trevas.	{"oeste": "sala_02", "subir": "ravina_escura"}	AgACAgEAAxkDAAIVi2ntJMgkcOb69-tou-oZgOhNwZW8AAItDGsb_VNxR63z_ojB3B5MAQADAgADeQADOwQ	[]	\N
sala_02	Área 2: Escadas Sinuosas	Escadas de pedra rústica descem em espiral, cobertas por uma camada espessa de poeira e teias de aranha. Os degraus estão irregulares e perigosos, cobertos por musgo escorregadio e poças de água negra.	{"baixo": "sala_03", "leste": "sala_01"}	AgACAgEAAxkDAAIWGGnun82Jl0wvzjT3RDeE4XYF8lmLAAJ3DGsbd6B4R5T6Jv2-H_oYAQADAgADeQADOwQ	[]	\N
sala_03	Área 3: Pátio em Ruínas	Um vasto pátio subterrâneo pavimentado, mas rachado. O ar é pesado e cheira a poeira secular. Estátuas sem cabeça de heróis do passado permanecem como sentinelas tristes. Portas de pedra levam para o interior da fortaleza em várias direções.	{"leste": "sala_12", "norte": "sala_04", "oeste": "sala_05", "subir": "sala_02"}	AgACAgEAAxkDAAIWHmnun-hd86DE2xXZFyw8-SAOZJ7hAAJ4DGsbd6B4R--GVbmjevm_AQADAgADeQADOwQ	[]	\N
sala_04	Área 4: Torre em Ruínas	Uma torre circular de granito. O teto desabou há séculos. No chão, corpos de goblins em decomposição jazem espalhados. Um deles está empalado na parede oeste por uma lança enferrujada. Qualquer PJ que conheça Dracônico lerá a inscrição na parede: 'Ashardalon'.	{"sul": "sala_03", "oeste": "sala_06"}	AgACAgEAAxkDAAIWJGnuoAj37xfHjRoMxTesoQAB0Vr5HQACeQxrG3egeEeZWLEwRvxNNQEAAwIAA3kAAzsE	[]	\N
sala_05	Área 5: Câmara Secreta	Uma câmara pequena e abafada, escondida atrás de uma porta secreta (Procurar CD 16). Prateleiras quebradas indicam uma antiga despensa. A passagem está armada com uma armadilha de agulha — embora o veneno já tenha evaporado, a agulha ainda causa 1 ponto de dano.	{"leste": "sala_03"}	AgACAgEAAxkDAAIW4GnupT5_PwWwCdeu14PgzsMSK6Q0AAKPDGsbd6B4R93JnLQmJw9KAQADAgADeQADOwQ	[]	\N
sala_06	Área 6: Corredor da Aproximação	Um corredor longo com portas de pedra pesadas. O ar é estagnado e cheira a poeira secular. Manchas escuras no chão lembram sangue seco. Uma porta secreta na parede leva à Área 5.	{"leste": "sala_04", "oeste": "sala_07"}	AgACAgEAAxkDAAIWJ2nuoCifepqIQID1C-a-vgLM9R7BAAJ6DGsbd6B4R2IiZUOyavc6AQADAgADeQADOwQ	[]	\N
sala_07	Área 7: Galeria das Notas de Forlorn	Um corredor amplo adornado com estátuas de dragão esculpidas em pedra vermelha. Dois pedestais de pedra sustentam globos cristalinos — o globo sul ainda emite um suave brilho e notas musicais tênues. Há um alçapão no chão que desce para o território goblin.	{"baixo": "sala_31", "leste": "sala_06", "norte": "sala_08"}	AgACAgEAAxkDAAIWKmnuoEnKEMAQgAfiBPM2-sjZNaGgAAJ7DGsbd6B4R_kNSXXkYx_xAQADAgADeQADOwQ	[]	\N
sala_15	Área 15: Fora da Gaiola (Meepo)	Símbolos e grafias em tinta verde decoram essa câmara arruinada. Uma jaula metálica arrebentada e vazia fica na parede sul. O kobold Meepo dorme num sono repleto de pesadelos.	{"sul": "sala_13"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-jMqKDyC6XUE5ZvB4t504KXZ5.png?st=2026-05-01T23%3A31%3A06Z&se=2026-05-02T01%3A31%3A06Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=8eb2c87c-0531-4dab-acb3-b5e2adddce6c&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-01T14%3A13%3A39Z&ske=2026-05-02T14%3A13%3A39Z&sks=b&skv=2026-02-06&sig=nffuNOGd%2BcsHvjslFDKt%2Byi3i8y0uwZX3XNC07q6%2Ba8%3D	[]	\N
sala_09	Área 9: O Enigma do Dragão	Uma câmara repleta de poeira como neve cinzenta. Na parede norte, uma escultura de dragão em mármore branco com relevos vermelhos. Resposta do enigma: ESTRELAS.	{"sul": "sala_08", "leste": "sala_10"}	\N	[]	\N
sala_10	Área 10: A Guarda de Honra	Um corredor flanqueado por alcova nas paredes leste e oeste. Cada alcova contém uma figura humana vestida em mármore branco com véus vermelhos. As estátuas lembram cavaleiros em cotas de malha.	{"sul": "sala_12", "norte": "sala_11", "oeste": "sala_09"}	AgACAgEAAxkDAAIW6WnupXaJ2stGoqr7u6rs0efufe5qAAKRDGsbd6B4R5eB8plX3ctYAQADAgADeQADOwQ	[]	\N
sala_11	Área 11: Tumba do Sacerdote do Dragão	O teto e as paredes estão rachados e quebrados. Um sarcófago de mármore maciço com mais de 2,5 metros jaz no centro. A pedra foi talhada com motivos dracônicos. Uma chama esverdeada permanente ilumina a câmara.	{"sul": "sala_10"}	AgACAgEAAxkDAAIW7mnupZOzGMi0J1mWqncF47vH7U1dAAKSDGsbd6B4RwaQzQXFas39AQADAgADeQADOwQ	[]	\N
sala_12	Área 12: Saguão de Entrada Kobold	A entrada principal para o território Kobold. Barricadas e ossos espalhados marcam o lugar. O cheiro de escamas e fumaça preenche o ar. Ao norte começam os corredores controlados pela tribo de Yusdrayl.	{"sul": "sala_10", "norte": "sala_13", "oeste": "sala_03"}	AgACAgEAAxkDAAIW5mnupVmh_5I_6STP9oKJ6KfNHI9wAAKQDGsbd6B4Rwe5yaTjz3QcAQADAgADeQADOwQ	[]	\N
sala_14	Área 14: Despensa do Dragão	Ratos e fezes enchem o aposento. Uma pequena barreira evita que os ratos escapem com facilidade. Os kobolds alimentavam os ratos com grilos para o filhote de dragão.	{"leste": "sala_13"}	\N	[]	\N
sala_18	Área 18: Prisão de Guerra	Quatro humanóides pequenos com chifres estão amarrados aqui. Os kobolds mantêm guerreiros goblins capturados para resgate. Algemas corroídas nas paredes.	{"oeste": "sala_17"}	\N	[]	\N
sala_20	Área 20: Colônia Kobold	Principal refugio dos kobolds. Diversas fogueiras iluminam o aposento. Utensílios de cozinha primitiva visíveis. Senha: 'milho que roda'.	{"leste": "sala_21"}	\N	[]	\N
sala_22	Área 22: Despensa Kobold	O odor de carne podre permeia esta câmara. Ganchos de ferro sustentam carcaças de grandes vermes e insetos.	{"sul": "sala_21", "norte": "sala_23"}	\N	[]	\N
sala_23	Área 23: Acesso ao Subterrâneo	Pedras soltas revelam um túnel rústico. Carrinolas num canto. O túnel conduz a quilômetros de escuridão além da aventura.	{"sul": "sala_22"}	\N	[]	\N
sala_24	Área 24: Passagem do Fosso	Corredor de 6 metros com alçapão escondido (armadilha goblin). Uma passarela de 30cm permite acesso seguro.	{"sul": "sala_17", "norte": "sala_26"}	\N	[]	\N
sala_25	Área 25: Desolação	Vazia e escura, contém dejetos de ratos e manchas impossíveis de identificar. Trilhas de botas passaram por aqui recentemente.	{"norte": "sala_29", "oeste": "sala_21"}	\N	[]	\N
sala_26	Área 26: Fonte Seca	Fonte ornamental seca com escultura de dragão. Inscrição em Dracônico: 'Que haja fogo' — invoca poção de sopro.	{"sul": "sala_24", "norte": "sala_27", "oeste": "sala_19"}	\N	[]	\N
sala_27	Área 27: Santuário	Porta esculpida com dragões esqueletizados. Cinco sarcófagos guardam esqueletos protetores. Inscrição: 'Canalize o bem'.	{"sul": "sala_26", "norte": "sala_28"}	\N	[]	\N
sala_28	Área 28: Celas Infestadas	Seis portas para pequenas celas. Três ratos atrozes habitam os ninhos de pedra, osso e fungos.	{"sul": "sala_27", "norte": "sala_29"}	\N	[]	\N
sala_29	Área 29: Armadilhas Antigas	Alçapões abertos e bloqueados por ferro. Fonte seca com inscrição: 'Que haja morte' (nuvem de veneno).	{"sul": "sala_28", "leste": "sala_25", "norte": "sala_30"}	\N	[]	\N
sala_30	Área 30: Mamãe Rato (Gutash)	Cheiro de carne podre. Um ninho particularmente grande abriga Gutash — a Mamãe Rato colossal de 1,8m.	{"sul": "sala_29"}	\N	[]	\N
sala_31	Área 31: Câmara dos Estrepes	Aposento coberto com estrepes afiados. Parede de tijolos em ruínas. Ponto de emboscada goblin.	{"cima": "sala_07", "norte": "sala_32"}	AgACAgEAAxkDAAIWLWnuoGeF-VRbL0IN-pIvUZ0KdvwzAAJ8DGsbd6B4R3dLr2kZQ7ZnAQADAgADeQADOwQ	[]	\N
sala_32	Área 32: Portão Goblin	Posto de guarda da tribo Durbuluk. Manchas na parede e odores de criaturas de má higiene.	{"sul": "sala_31", "norte": "sala_33"}	AgACAgEAAxkDAAIWMGnuoIHPNOb0dhGgiEkd9GP_t2KxAAJ9DGsbd6B4R1knkEr97k15AQADAgADeQADOwQ	[]	\N
sala_33	Área 33: Sala de Prática	Goblins praticam azagaias em bonecos de estopa parecidos com humanos e elfos. Licor goblin pelo chão.	{"sul": "sala_32", "leste": "sala_34", "norte": "sala_36a"}	AgACAgEAAxkDAAIWN2nuoT9FeJRj_4vjOB-UARChD69BAAJ-DGsbd6B4R0638kLvLU1SAQADAgADeQADOwQ	[]	\N
sala_34	Área 34: Prisão Militar Goblin	Imundície reina. Kobolds amarrados e o gnomo Erky Timbers definha dentro de uma jaula de ferro pequena demais.	{"oeste": "sala_33"}	AgACAgEAAxkDAAIWPWnuoZQl9EeL1cKNr2xbNc6bAAExagACfwxrG3egeEf9-z0_HElD2wEAAwIAA3kAAzsE	[]	\N
sala_35	Área 35: Corredor com Armadilha	Corredor comum com alçapão no solo. No fundo do poço há um anel de ouro com safira.	{"sul": "sala_37", "norte": "sala_36a"}	\N	[]	\N
sala_36a	Área 36: Salteadores Goblins (Quartel A)	Lixo e carne podre. Seis redes de peles em volta de um fogão de lenha. Seis goblins 'salteadores' habitam aqui.	{"sul": "sala_33", "leste": "sala_36b", "norte": "sala_38"}	AgACAgEAAxkDAAIWSWnuogproPP3bF2AUCVYsTddAoRlAAKADGsbd6B4R_AbvnlZA1ZCAQADAgADeQADOwQ	[]	\N
sala_37	Área 37: Sala dos Troféus (Calcryx!)	Cabeças de animais empalhados. Camadas de gelo recobrem as paredes — aqui está Calcryx, o filhote de dragão branco.	{"leste": "sala_38", "norte": "sala_35"}	\N	[]	\N
sala_38	Área 38: Passagem Goblin	Câmara de estoque: água, carne e óleo. Barris com a escrita: 'pudim elfico'.	{"sul": "sala_36a", "norte": "sala_39", "oeste": "sala_37"}	AgACAgEAAxkDAAIWUGnuooG7gvf0XSpbwIXiPhlUIXPRAAKBDGsbd6B4R1EdwPQ2FadOAQADAgADeQADOwQ	[]	\N
sala_39	Área 39: Fumaça do Dragão	Saguão cheio de fumaça que atrapalha a visão. Fileira dupla de figuras de mármore com dragões enlaçados.	{"sul": "sala_36b", "norte": "sala_40", "oeste": "sala_38"}	AgACAgEAAxkDAAIWVWnuos_EzB29oasBqnBPKOKa92DfAAKCDGsbd6B4R4SCuSmxhDUMAQADAgADeQADOwQ	[]	\N
sala_40	Área 40: Vilarejo Goblin	Antiga catedral agora covil goblin. Fungos com brilho violeta iluminam dezenas de goblins em seus afazeres.	{"sul": "sala_36c", "leste": "sala_39", "norte": "sala_41"}	AgACAgEAAxkDAAIWWmnuowMkDvCNJxttKTY7clnXtFMvAAKDDGsbd6B4RyEdOhPpMNTAAQADAgADeQADOwQ	[]	\N
sala_41	Área 41: Câmara do Chefe Goblin (Durnn)	Trono de pedra e arca de ferro. Durnn, o robgoblin, rege a tribo acima do poço de vinhas que desce ao Bosque.	{"sul": "sala_40", "baixo": "sala_42"}	AgACAgEAAxkDAAIWXWnuoyjRVUiHQ0drqyRxiXxEuT2CAAKEDGsbd6B4R_CoF8TB5ZtpAQADAgADeQADOwQ	[]	\N
sala_42	Área 42: Central de Adubo	Bosque do Crepúsculo. Ramos secos e esqueletos remexem adubo para nutrir as plantas de Belak.	{"cima": "sala_41", "norte": "sala_43"}	AgACAgEAAxkDAAIWYmnuo2rTQqaS88iJitX-ZXDQUly_AAKFDGsbd6B4R0CXp1TuJ2MpAQADAgADeQADOwQ	[]	\N
sala_43	Área 43: O Grande Caçador (Balsag)	Chão rústico manchado. Balsag, o bugbear, e seus dois ratos caçadores habitam aqui.	{"sul": "sala_42", "leste": "sala_44", "norte": "sala_47"}	AgACAgEAAxkDAAIWZWnuo4PShcqiT6AmQfMyuHp5zVvIAAKGDGsbd6B4R3f9DTb2st_9AQADAgADeQADOwQ	[]	\N
sala_44	Área 44: Fenda	Terra partida por desastre geológico. Cheiro de enxofre e buracos de 30cm no chão.	{"norte": "sala_45", "oeste": "sala_43"}	AgACAgEAAxkDAAIWaGnuo5prxbqvl5MU-10OKDgpYE5KAAKHDGsbd6B4R0ZONIDw9jYaAQADAgADeQADOwQ	[]	\N
sala_45	Área 45: Nódulo da Fenda (Thoqqua)	Antecâmara de pedra com luz flamejante. Habitada por um thoqqua incandescente.	{"sul": "sala_44"}	AgACAgEAAxkDAAIWa2nuo68agf4CPGEkPAiZ0zBPIpmEAAKIDGsbd6B4R2R6GxkCuXIHAQADAgADeQADOwQ	[]	\N
sala_46	Área 46: O Antigo Altar	Pedestal de metal na forma de um dragão ereto. Mosaicos desbotados recobrem as paredes.	{"leste": "sala_47"}	\N	[]	\N
sala_47	Área 47: Comunidade Goblin de Belak	Colunas envoltas em fungos luminescentes. Goblins servos de Belak trabalham com pilões e argila.	{"sul": "sala_43", "norte": "sala_49", "oeste": "sala_46"}	AgACAgEAAxkDAAIWhmnuo-PyIH9MP96L1mLmmRIYARrVAAKJDGsbd6B4R1LyLq484Mt4AQADAgADeQADOwQ	[]	\N
sala_48	Área 48: Galeria (Jardins de Belak)	Estufas de Belak. Vegetação da superfície crescendo no subterrâneo. Jardineiro bugbear com foice longa.	{"sul": "sala_47", "norte": "sala_49"}	\N	[]	\N
sala_49	Área 49: Arvoredo (Centro do Bosque)	Quatro arvoredos com odor de podridão e brilho verde-pálido. Centro vital habitado por servos de Belak.	{"sul": "sala_47", "leste": "sala_52", "norte": "sala_54", "oeste": "sala_50"}	AgACAgEAAxkDAAIWi2nuo_uhbH1mC9vy5JvDQSzMW2scAAKKDGsbd6B4R4Fg9L_i_WCvAQADAgADeQADOwQ	[]	\N
sala_50	Área 50: Templo de Ashardalon	Blocos de granito com dragões. Estátua de dragão com olhos vermelhos brilhantes. Uma Sombra espreita aqui.	{"leste": "sala_49", "norte": "sala_51"}	AgACAgEAAxkDAAIWjmnupBSnmugLVko96_ukQzS6J_W8AAKLDGsbd6B4R3iQUXIevQjzAQADAgADeQADOwQ	[]	\N
sala_51	Área 51: Biblioteca dos Dragões	Estantes de pedra inclinadas e páginas queimadas. Pergaminhos valiosos escondidos sob o lixo.	{"sul": "sala_50", "norte": "sala_53"}	AgACAgEAAxkDAAIWk2nupCtp1eT5Y4W-Sq8KKSayWXWbAAKMDGsbd6B4R-iJysQjYIYRAQADAgADeQADOwQ	[]	\N
sala_52	Área 52: Passagem Subterrânea	Degraus úmidos descendo sob a área 49. Passagem destruída e inundada.	{"oeste": "sala_49"}	\N	[]	\N
sala_53	Área 53: Aposentos de Belak	Tomos e pergaminhos de Belak. Arbustos pálidos crescendo no solo sob fungos do teto.	{"sul": "sala_51"}	AgACAgEAAxkDAAIWlmnupEIOAnbSM94nP_NcvD5nr0RrAAKNDGsbd6B4R3XBixJ_I9H0AQADAgADeQADOwQ	[]	\N
sala_13	Área 13: Corredor de Entrada Kobold	Um corredor com barricadas improvisadas de kobolds. O fedor de muitos corpos em área tão pequena saturou o ar. Um pequeno círculo de brasas no meio foi construído com lajes quebradas.	{"sul": "sala_12", "leste": "sala_16", "norte": "sala_15", "oeste": "sala_14"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-62Lymrf3u5J8ILoe1vGkAMlC.png?st=2026-05-01T23%3A28%3A59Z&se=2026-05-02T01%3A28%3A59Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=38e27a3b-6174-4d3e-90ac-d7d9ad49543f&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-01T14%3A16%3A55Z&ske=2026-05-02T14%3A16%3A55Z&sks=b&skv=2026-02-06&sig=Vau8MfFrhPEGtozazpw/x7D9Kc/IQdMqD0u0/ridncI%3D	[]	\N
sala_16	Área 16: Kobolds Sentinelas	O fedor de muitos corpos saturou o ar. Um pequeno círculo de brasas no meio da câmara. Diversos humanóides pequenos com escamas habitam a câmara.	{"leste": "sala_17", "oeste": "sala_13"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-5e51BCbkpVvo0WqGQwB2i6gS.png?st=2026-05-01T23%3A31%3A52Z&se=2026-05-02T01%3A31%3A52Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=0e2a3d55-e963-40c9-9c89-2a1aa28cb3ac&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-01T11%3A19%3A35Z&ske=2026-05-02T11%3A19%3A35Z&sks=b&skv=2026-02-06&sig=sR8EDiXqfZVmaYJsIMhULyGvYeTKGWCUXCiOPwsrVos%3D	[]	\N
sala_17	Área 17: Câmara Dracônica	Uma sala cerimonial ampla com pilares esculpidos com dragões. O chão está coberto por tapetes feitos de cabelo entrelaçado e plantas mortas.	{"leste": "sala_18", "norte": "sala_19", "oeste": "sala_16"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-UPwSfMAlCX34qNjTea6iNBq3.png?st=2026-05-01T23%3A33%3A42Z&se=2026-05-02T01%3A33%3A42Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=8eb2c87c-0531-4dab-acb3-b5e2adddce6c&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-01T13%3A44%3A10Z&ske=2026-05-02T13%3A44%3A10Z&sks=b&skv=2026-02-06&sig=UvWz0wmPvMCjpZ0F9vieOJ/OECFoiojAAidZDIU8hAs%3D	[]	\N
sala_08	Área 8: Placas de Pressão	Uma pequena câmara com uma placa de pressão ligeiramente elevada no centro do chão. O mecanismo, se ativado, dispara setas da parte superior da porta oeste. O pó espesso e intocado sugere que esta câmara permaneceu selada há eras.	{"sul": "sala_07", "norte": "sala_09"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-4XIkHqJDOAlbxWnd0PhIZe2y.png?st=2026-04-28T19%3A56%3A59Z&se=2026-04-28T21%3A56%3A59Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=ae240de5-197c-4e03-af8e-c66aed9a4539&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-04-28T14%3A00%3A43Z&ske=2026-04-29T14%3A00%3A43Z&sks=b&skv=2026-02-06&sig=Z9xPG89LGGGHR4VrtHcMMqCIDa8rlEjlT7Hde4Z8wbo%3D	[]	\N
estrada_triboar	Emboscada na Estrada de Triboar	A estrada de terra se estreita aqui, com um barranco alto e moitas dos dois lados. Dois cavalos mortos, crivados de flechas negras, bloqueiam o caminho.	{"norte": "trilha_goblin"}	\N	[]	\N
trilha_goblin	Trilha Goblin nos Matos	Uma trilha escura e traiçoeira serpenteia por um bosque denso. Marcas de arrasto no chão indicam que corpos foram puxados por aqui.	{"sul": "estrada_triboar", "noroeste": "caverna_entrada"}	\N	[]	\N
caverna_entrada	Entrada da Caverna Dentefino	Uma larga abertura ao lado de um morro. Um riacho raso flui do interior da caverna, deixando um caminho estreito do lado direito.	{"sul": "trilha_goblin", "leste": "caverna_vigias", "norte": "caverna_canil", "noroeste": "caverna_passagem"}	\N	[]	\N
caverna_vigias	Posto de Vigia	Clareira entre arbustos espinhosos. Tábuas formam um abrigo improvisado para os guardas goblins.	{"oeste": "caverna_entrada"}	\N	[]	\N
caverna_canil	Canil dos Lobos	Câmara escura com cheiro de pelo molhado e carne podre. Estalagmites no chão e uma fissura que sobe como chaminé natural.	{"sul": "caverna_entrada", "acima": "caverna_klarg"}	\N	[]	\N
caverna_passagem	Passagem Estreita e Ponte	O túnel sobe acompanhando o riacho. No alto, uma ponte frágil de madeira e cordas cruza a passagem nas sombras do teto.	{"sul": "caverna_entrada", "norte": "caverna_tanques", "oeste": "caverna_covil"}	\N	[]	\N
caverna_covil	Covil dos Goblins	Gruta larga com degrau íngreme. Ar enfumaçado. Sildar Hallwinter está amarrado e amordaçado num canto.	{"leste": "caverna_passagem"}	\N	[]	\N
caverna_tanques	Caverna dos Tanques Duplos	Barulho ensurdecedor de cachoeira. Dois tanques de água represada por muros frágeis de pedra.	{"sul": "caverna_passagem", "oeste": "caverna_klarg"}	\N	[]	\N
caverna_klarg	Caverna de Klarg	Caverna ampla com fogueira no centro. Sacos e caixas com o símbolo do Leão Azul empilhados no fundo.	{"leste": "caverna_tanques", "abaixo": "caverna_canil"}	\N	[]	\N
phandalin_centro	Praça de Phandalin	Vila rústica e poeirenta. Aqui ficam a Estalagem Colina de Pedra, Provisões Barthen e o Posto de Trocas Escudo do Leão.	{"leste": "estrada_triboar", "norte": "mansao_tresendar_ext"}	\N	[]	\N
mansao_tresendar_ext	Ruínas da Mansão Tresendar	Fundações de pedra de uma mansão antiga. Um porão escuro desce para as profundezas.	{"sul": "phandalin_centro", "abaixo": "marcar_adega"}	\N	[]	\N
marcar_adega	Adega dos Marcarrubras	Barris de cerveja e grande cisterna. Cheiro de umidade. Uma parede parece falsa...	{"acima": "mansao_tresendar_ext", "norte": "marcar_corredor", "segredo": "marcar_fenda"}	\N	[]	\N
marcar_corredor	Corredor Principal	Corredor largo de pedra que conecta os cômodos do esconderijo.	{"sul": "marcar_adega", "leste": "marcar_barracas", "norte": "marcar_fenda"}	\N	[]	\N
marcar_barracas	Alojamento dos Bandidos	Camas desarrumadas e restos de comida. Bandidos de mantos vermelhos jogam cartas.	{"oeste": "marcar_corredor"}	\N	[]	\N
marcar_fenda	Caverna da Fenda	Fenda profunda e fria divide a caverna. Cheiro de carne podre. Algo brilha entre os detritos.	{"sul": "marcar_corredor", "oeste": "marcar_laboratorio"}	\N	[]	\N
marcar_laboratorio	Laboratório de Iarno	Laboratório alquímico com livros, pergaminhos e frascos borbulhantes. Iarno, o mago renegado, trabalha aqui.	{"leste": "marcar_fenda"}	\N	[]	\N
conyberry_agatha	Covil de Agatha (Conyberry)	Cabana de galhos numa aldeia abandonada. Ar frio e silêncio absoluto.	{"sul": "phandalin_centro"}	\N	[]	\N
poco_coruja_velha	Poço da Coruja Velha	Ruínas de torre de vigia. Tenda colorida montada perto do poço.	{"oeste": "phandalin_centro"}	\N	[]	\N
torre_wyvern	Torre de Wyvern	Afloramento rochoso com caverna rasa. Cheiro de carne podre e fumaça.	{"norte": "phandalin_centro"}	\N	[]	\N
cragmaw_ext	Frente do Castelo Cragmaw	Ruínas de castelo com torres desmoronadas. Flechas espreitam das frestas escuras.	{"leste": "cragmaw_torre_urso", "norte": "cragmaw_salao"}	\N	[]	\N
cragmaw_salao	Salão de Banquetes	Teto parcialmente caído. Mesas cobertas de restos de comida estragada.	{"sul": "cragmaw_ext", "oeste": "cragmaw_rei"}	\N	[]	\N
cragmaw_torre_urso	Torre do Urso-Coruja	Chão coberto de ossos roídos e penas. Teto desabado, aberto ao céu.	{"oeste": "cragmaw_ext"}	\N	[]	\N
cragmaw_rei	Aposentos do Rei Grol	Cama de peles nojentas. Gundren está caído e ferido. Mapas sobre uma mesa improvisada.	{"leste": "cragmaw_salao"}	\N	[]	\N
thundertree_ruinas	Ruínas de Thundertree	Casas destruídas por erupção. Arbustos mortos com espinhos. Uma torre no alto da colina.	{"leste": "wave_entrada_mina", "norte": "thundertree_torre"}	\N	[]	\N
thundertree_torre	Torre de Venomfang	Torre no topo da colina. Ar com cheiro de cloro. Tesouros velhos cobrem o chão.	{"sul": "thundertree_ruinas"}	\N	[]	\N
wave_entrada_mina	Entrada dos Túneis da Mina	Rede de túneis antigos. Esqueletos de anões e orcs jazem aqui.	{"sul": "thundertree_ruinas", "norte": "wave_caverna_fungos", "oeste": "wave_escritorio"}	\N	[]	\N
wave_escritorio	Escritório dos Avaliadores	Mesas empoeiradas e livros apodrecidos. Cofre de ferro aberto.	{"leste": "wave_entrada_mina"}	\N	[]	\N
wave_caverna_fungos	Caverna dos Fungos	Tapete de cogumelos fosforescentes. Vapor estranho e esporos flutuando.	{"sul": "wave_entrada_mina", "norte": "wave_grande_caverna"}	\N	[]	\N
wave_grande_caverna	A Grande Caverna	Câmara vasta com estalactites imensas. Som ensurdecedor das 'ondas' ecoa.	{"sul": "wave_caverna_fungos", "leste": "wave_aposentos_mago", "norte": "caverna_eco_forja"}	\N	[]	\N
wave_aposentos_mago	Aposentos do Mago (Mormesk)	Sala luxuosa em ruínas. Mormesk, o Espectro, flutua sobre uma cama apodrecida.	{"oeste": "wave_grande_caverna"}	\N	[]	\N
caverna_eco_forja	A Forja das Magias	Fogo verde em braseiro esférico. Crânio Flamejante guarda a sala. Runas anãs nas paredes.	{"sul": "wave_grande_caverna"}	\N	[]	\N
caverna_eco_templo	Templo de Dumathoin	Colunas anãs esculpidas. Nezznar analisa mapas. Teias gigantes nas paredes.	{"oeste": "wave_grande_caverna"}	\N	[]	\N
wave_caverna_estrelada	Caverna Estrelada	Cristais no teto brilham como estrelas. Beleza que contrasta com o perigo.	{"sul": "wave_grande_caverna", "norte": "caverna_eco_templo"}	\N	[]	\N
sala_19	Área 19: Salão dos Dragões	Fileira dupla de colunas de mármore esculpidas com dragões alados. Humanóides pequenos patrulham frequentemente a área.	{"sul": "sala_17", "leste": "sala_26", "norte": "sala_21"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-eVkpLGKqKwB2ImEeuVdL5d40.png?st=2026-05-02T14%3A26%3A08Z&se=2026-05-02T16%3A26%3A08Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=7252282d-c412-4b10-a746-00f5af2a7888&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-02T02%3A22%3A05Z&ske=2026-05-03T02%3A22%3A05Z&sks=b&skv=2026-02-06&sig=pPcP4i5jmGi9fVutgcLuZ8oWDMEv4KToNJ3uwcoFv/k%3D	[]	\N
sala_21	Área 21: O Trono do Dragão (Yusdrayl)	Um trono baixo feito de altar quebrado. Yusdrayl governa com 6 sentinelas ao redor. Uma chave metálica está presa na boca do dragão esculpido.	{"sul": "sala_19", "leste": "sala_25", "norte": "sala_22", "oeste": "sala_20"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-lIPe6LSK17Pv80ugKH986ymh.png?st=2026-05-02T14%3A26%3A42Z&se=2026-05-02T16%3A26%3A42Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=32836cae-d25f-4fe9-827b-1c8c59c442cc&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-02T15%3A24%3A30Z&ske=2026-05-03T15%3A24%3A30Z&sks=b&skv=2026-02-06&sig=OyuvaT0hbjqlv9igtuHcVZ2FwVUNqMxJuFdn4eMPgOI%3D	[]	\N
sala_54	Área 54: Portão do Bosque	Goblins separam galhos diante da caverna ampla. Nódulos de fungos iluminam o bosque de brotos doentes.	{"sul": "sala_49", "norte": "sala_55"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-K5aUqVioNP5CDlymVE2zFXvb.png?st=2026-05-03T17%3A24%3A46Z&se=2026-05-03T19%3A24%3A46Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=7252282d-c412-4b10-a746-00f5af2a7888&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-03T17%3A24%3A13Z&ske=2026-05-04T17%3A24%3A13Z&sks=b&skv=2026-02-06&sig=NqmQmezX0jXG7c1SLWA%2B%2BbcDouQZjneayWyvfTbuIeU%3D	[]	\N
sala_55	Área 55: Bosque do Crepúsculo	Vegetação pálida banhando-se na radiação fraca dos fungos. Ramos secos estão enraizados aqui.	{"sul": "sala_54", "norte": "sala_56"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-olS9tzXKgwLiN05EBFI52JLE.png?st=2026-05-03T17%3A25%3A08Z&se=2026-05-03T19%3A25%3A08Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=8eb2c87c-0531-4dab-acb3-b5e2adddce6c&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-03T04%3A24%3A40Z&ske=2026-05-04T04%3A24%3A40Z&sks=b&skv=2026-02-06&sig=5bWv5ERhQi21bV5pPJ%2BuqH7KfqdV%2BDcZsduRQgLF%2Bh0%3D	[]	\N
sala_56	Área 56: A Árvore Gulthias (BOSS FINAL)	Colossal abominação de madeira negra. Belak e os corrompidos Bradford e Sharwyn aguardam no centro.	{"sul": "sala_55"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-Pm4HkE8c9nZAz3Ou8QjTn7VZ.png?st=2026-05-03T17%3A25%3A37Z&se=2026-05-03T19%3A25%3A37Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=7252282d-c412-4b10-a746-00f5af2a7888&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-02T19%3A26%3A57Z&ske=2026-05-03T19%3A26%3A57Z&sks=b&skv=2026-02-06&sig=c2oxeX1hgvF4GjzHJUMhP2aWsTs2vBRuIQGO92FOhoI%3D	[]	\N
sala_36c	Área 36: Salteadores Goblins (Quartel C)	Terceiro quartel em condições deploráveis. Odres de vinho estragado e restos podres.	{"norte": "sala_40", "oeste": "sala_36b"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-CjMbbNW1G96Xe6ix21KEuNOL.png?st=2026-05-04T19%3A47%3A05Z&se=2026-05-04T21%3A47%3A05Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=8eb2c87c-0531-4dab-acb3-b5e2adddce6c&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-04T15%3A14%3A32Z&ske=2026-05-05T15%3A14%3A32Z&sks=b&skv=2026-02-06&sig=bTVx50hdNmFCZteoYU6oqEfdzyXIYABJibvu72uWl3s%3D	[]	\N
sala_36b	Área 36: Salteadores Goblins (Quartel B)	Outro quartel idêntico. Utensílios velhos e armas quebradas amontoadas com armaduras gastas.	{"leste": "sala_36c", "norte": "sala_39", "oeste": "sala_36a"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-jygTPOopQKcnZqhN9GQaUd1h.png?st=2026-05-04T19%3A47%3A34Z&se=2026-05-04T21%3A47%3A34Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=38e27a3b-6174-4d3e-90ac-d7d9ad49543f&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-04T18%3A12%3A29Z&ske=2026-05-05T18%3A12%3A29Z&sks=b&skv=2026-02-06&sig=gsPXZEFQU6Garc9i20UO59MkzVu2lc%2BB3USCtHVbsQU%3D	[]	\N
\.


--
-- Data for Name: cenas_backup; Type: TABLE DATA; Schema: public; Owner: user_8W2mTA
--

COPY public.cenas_backup (cod_sala, nome_sala, descricao_visual, conexoes, imagem_url, loot_fixo) FROM stdin;
carvalhal	Vila de Carvalhal (Oakhurst)	A pequena vila de Oakhurst ergue-se precariamente na borda da ravina. O ar é frio e o cheiro de fumaça de lareira preenche as ruas lamacentas. Aldeões desconfiados observam através de janelas. A Taverna do Velho Javali é o único lugar que parece oferecer algum calor real.	{"norte": "estrada_velha"}	AgACAgEAAxkDAAIWzmnupRqCweTxgq8Iu3kpUecvOtktAAKODGsbd6B4Rw1I_bFlkFC3AQADAgADeQADOwQ	[]
estrada_velha	A Estrada Velha	Uma trilha de pedras arruinadas que serpenteia por quilômetros. Árvores retorcidas de galhos secos como garras observam seu avanço. O silêncio é interrompido apenas pelo vento. Carvalhos antigos formam uma abóbada sombria sobre o caminho.	{"sul": "carvalhal", "norte": "ravina_escura"}	AgACAgEAAxkDAAIVhWntJGAecZP5Z8DMt-eHF5A--aToAAIrDGsb_VNxR8WO3fkXKFqVAQADAgADeQADOwQ	[]
ravina_escura	Área 0: A Ravina	Uma fenda profunda e estreita abre-se na terra como uma cicatriz. Dois pilares de pedra ainda estão de pé, mas a maioria está inclinada para o abismo. Uma corda grossa com nós, amarrada a um pilar, desce 15 metros até a escuridão abaixo. Marcas de pés goblin estão gravadas na face do rochedo.	{"sul": "estrada_velha", "descer": "sala_01"}	AgACAgEAAxkDAAIViGntJLKecU9r-ehv3Bblc3imgZHuAAIsDGsb_VNxR41Y5jQYJXx4AQADAgADeQADOwQ	[]
sala_01	Área 1: O Parapeito	Um parapeito de areia domina um golfo subterrâneo de escuridão a oeste. Areia, pedregulhos e ossos de pequenos animais recobrem o solo. Uma escada talhada na pedra serpenteia pela lateral, descendo às trevas.	{"subir": "ravina_escura", "oeste": "sala_02"}	AgACAgEAAxkDAAIVi2ntJMgkcOb69-tou-oZgOhNwZW8AAItDGsb_VNxR63z_ojB3B5MAQADAgADeQADOwQ	[]
sala_02	Área 2: Escadas Sinuosas	Escadas de pedra rústica descem em espiral, cobertas por uma camada espessa de poeira e teias de aranha. Os degraus estão irregulares e perigosos, cobertos por musgo escorregadio e poças de água negra.	{"leste": "sala_01", "baixo": "sala_03"}	AgACAgEAAxkDAAIWGGnun82Jl0wvzjT3RDeE4XYF8lmLAAJ3DGsbd6B4R5T6Jv2-H_oYAQADAgADeQADOwQ	[]
sala_03	Área 3: Pátio em Ruínas	Um vasto pátio subterrâneo pavimentado, mas rachado. O ar é pesado e cheira a poeira secular. Estátuas sem cabeça de heróis do passado permanecem como sentinelas tristes. Portas de pedra levam para o interior da fortaleza em várias direções.	{"subir": "sala_02", "norte": "sala_04", "oeste": "sala_05", "leste": "sala_12"}	AgACAgEAAxkDAAIWHmnun-hd86DE2xXZFyw8-SAOZJ7hAAJ4DGsbd6B4R--GVbmjevm_AQADAgADeQADOwQ	[]
sala_04	Área 4: Torre em Ruínas	Uma torre circular de granito. O teto desabou há séculos. No chão, corpos de goblins em decomposição jazem espalhados. Um deles está empalado na parede oeste por uma lança enferrujada. Qualquer PJ que conheça Dracônico lerá a inscrição na parede: 'Ashardalon'.	{"sul": "sala_03", "oeste": "sala_06"}	AgACAgEAAxkDAAIWJGnuoAj37xfHjRoMxTesoQAB0Vr5HQACeQxrG3egeEeZWLEwRvxNNQEAAwIAA3kAAzsE	[]
sala_05	Área 5: Câmara Secreta	Uma câmara pequena e abafada, escondida atrás de uma porta secreta (Procurar CD 16). Prateleiras quebradas indicam uma antiga despensa. A passagem está armada com uma armadilha de agulha — embora o veneno já tenha evaporado, a agulha ainda causa 1 ponto de dano.	{"leste": "sala_03"}	AgACAgEAAxkDAAIW4GnupT5_PwWwCdeu14PgzsMSK6Q0AAKPDGsbd6B4R93JnLQmJw9KAQADAgADeQADOwQ	[]
sala_06	Área 6: Corredor da Aproximação	Um corredor longo com portas de pedra pesadas. O ar é estagnado e cheira a poeira secular. Manchas escuras no chão lembram sangue seco. Uma porta secreta na parede leva à Área 5.	{"leste": "sala_04", "oeste": "sala_07"}	AgACAgEAAxkDAAIWJ2nuoCifepqIQID1C-a-vgLM9R7BAAJ6DGsbd6B4R2IiZUOyavc6AQADAgADeQADOwQ	[]
sala_07	Área 7: Galeria das Notas de Forlorn	Um corredor amplo adornado com estátuas de dragão esculpidas em pedra vermelha. Dois pedestais de pedra sustentam globos cristalinos — o globo sul ainda emite um suave brilho e notas musicais tênues. Há um alçapão no chão que desce para o território goblin.	{"leste": "sala_06", "norte": "sala_08", "baixo": "sala_31"}	AgACAgEAAxkDAAIWKmnuoEnKEMAQgAfiBPM2-sjZNaGgAAJ7DGsbd6B4R_kNSXXkYx_xAQADAgADeQADOwQ	[]
sala_15	Área 15: Fora da Gaiola (Meepo)	Símbolos e grafias em tinta verde decoram essa câmara arruinada. Uma jaula metálica arrebentada e vazia fica na parede sul. O kobold Meepo dorme num sono repleto de pesadelos.	{"sul": "sala_13"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-jMqKDyC6XUE5ZvB4t504KXZ5.png?st=2026-05-01T23%3A31%3A06Z&se=2026-05-02T01%3A31%3A06Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=8eb2c87c-0531-4dab-acb3-b5e2adddce6c&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-01T14%3A13%3A39Z&ske=2026-05-02T14%3A13%3A39Z&sks=b&skv=2026-02-06&sig=nffuNOGd%2BcsHvjslFDKt%2Byi3i8y0uwZX3XNC07q6%2Ba8%3D	[]
sala_09	Área 9: O Enigma do Dragão	Uma câmara repleta de poeira como neve cinzenta. Na parede norte, uma escultura de dragão em mármore branco com relevos vermelhos. Resposta do enigma: ESTRELAS.	{"sul": "sala_08", "leste": "sala_10"}	\N	[]
sala_10	Área 10: A Guarda de Honra	Um corredor flanqueado por alcova nas paredes leste e oeste. Cada alcova contém uma figura humana vestida em mármore branco com véus vermelhos. As estátuas lembram cavaleiros em cotas de malha.	{"oeste": "sala_09", "norte": "sala_11", "sul": "sala_12"}	AgACAgEAAxkDAAIW6WnupXaJ2stGoqr7u6rs0efufe5qAAKRDGsbd6B4R5eB8plX3ctYAQADAgADeQADOwQ	[]
sala_11	Área 11: Tumba do Sacerdote do Dragão	O teto e as paredes estão rachados e quebrados. Um sarcófago de mármore maciço com mais de 2,5 metros jaz no centro. A pedra foi talhada com motivos dracônicos. Uma chama esverdeada permanente ilumina a câmara.	{"sul": "sala_10"}	AgACAgEAAxkDAAIW7mnupZOzGMi0J1mWqncF47vH7U1dAAKSDGsbd6B4RwaQzQXFas39AQADAgADeQADOwQ	[]
sala_12	Área 12: Saguão de Entrada Kobold	A entrada principal para o território Kobold. Barricadas e ossos espalhados marcam o lugar. O cheiro de escamas e fumaça preenche o ar. Ao norte começam os corredores controlados pela tribo de Yusdrayl.	{"oeste": "sala_03", "norte": "sala_13", "sul": "sala_10"}	AgACAgEAAxkDAAIW5mnupVmh_5I_6STP9oKJ6KfNHI9wAAKQDGsbd6B4Rwe5yaTjz3QcAQADAgADeQADOwQ	[]
sala_14	Área 14: Despensa do Dragão	Ratos e fezes enchem o aposento. Uma pequena barreira evita que os ratos escapem com facilidade. Os kobolds alimentavam os ratos com grilos para o filhote de dragão.	{"leste": "sala_13"}	\N	[]
sala_18	Área 18: Prisão de Guerra	Quatro humanóides pequenos com chifres estão amarrados aqui. Os kobolds mantêm guerreiros goblins capturados para resgate. Algemas corroídas nas paredes.	{"oeste": "sala_17"}	\N	[]
sala_19	Área 19: Salão dos Dragões	Fileira dupla de colunas de mármore esculpidas com dragões alados. Humanóides pequenos patrulham frequentemente a área.	{"sul": "sala_17", "norte": "sala_21", "leste": "sala_26"}	\N	[]
sala_20	Área 20: Colônia Kobold	Principal refugio dos kobolds. Diversas fogueiras iluminam o aposento. Utensílios de cozinha primitiva visíveis. Senha: 'milho que roda'.	{"leste": "sala_21"}	\N	[]
sala_21	Área 21: O Trono do Dragão (Yusdrayl)	Um trono baixo feito de altar quebrado. Yusdrayl governa com 6 sentinelas ao redor. Uma chave metálica está presa na boca do dragão esculpido.	{"sul": "sala_19", "norte": "sala_22", "oeste": "sala_20", "leste": "sala_25"}	\N	[]
sala_22	Área 22: Despensa Kobold	O odor de carne podre permeia esta câmara. Ganchos de ferro sustentam carcaças de grandes vermes e insetos.	{"sul": "sala_21", "norte": "sala_23"}	\N	[]
sala_23	Área 23: Acesso ao Subterrâneo	Pedras soltas revelam um túnel rústico. Carrinolas num canto. O túnel conduz a quilômetros de escuridão além da aventura.	{"sul": "sala_22"}	\N	[]
sala_24	Área 24: Passagem do Fosso	Corredor de 6 metros com alçapão escondido (armadilha goblin). Uma passarela de 30cm permite acesso seguro.	{"norte": "sala_26", "sul": "sala_17"}	\N	[]
sala_25	Área 25: Desolação	Vazia e escura, contém dejetos de ratos e manchas impossíveis de identificar. Trilhas de botas passaram por aqui recentemente.	{"oeste": "sala_21", "norte": "sala_29"}	\N	[]
sala_26	Área 26: Fonte Seca	Fonte ornamental seca com escultura de dragão. Inscrição em Dracônico: 'Que haja fogo' — invoca poção de sopro.	{"oeste": "sala_19", "norte": "sala_27", "sul": "sala_24"}	\N	[]
sala_27	Área 27: Santuário	Porta esculpida com dragões esqueletizados. Cinco sarcófagos guardam esqueletos protetores. Inscrição: 'Canalize o bem'.	{"sul": "sala_26", "norte": "sala_28"}	\N	[]
sala_28	Área 28: Celas Infestadas	Seis portas para pequenas celas. Três ratos atrozes habitam os ninhos de pedra, osso e fungos.	{"sul": "sala_27", "norte": "sala_29"}	\N	[]
sala_29	Área 29: Armadilhas Antigas	Alçapões abertos e bloqueados por ferro. Fonte seca com inscrição: 'Que haja morte' (nuvem de veneno).	{"sul": "sala_28", "norte": "sala_30", "leste": "sala_25"}	\N	[]
sala_30	Área 30: Mamãe Rato (Gutash)	Cheiro de carne podre. Um ninho particularmente grande abriga Gutash — a Mamãe Rato colossal de 1,8m.	{"sul": "sala_29"}	\N	[]
sala_31	Área 31: Câmara dos Estrepes	Aposento coberto com estrepes afiados. Parede de tijolos em ruínas. Ponto de emboscada goblin.	{"cima": "sala_07", "norte": "sala_32"}	AgACAgEAAxkDAAIWLWnuoGeF-VRbL0IN-pIvUZ0KdvwzAAJ8DGsbd6B4R3dLr2kZQ7ZnAQADAgADeQADOwQ	[]
sala_32	Área 32: Portão Goblin	Posto de guarda da tribo Durbuluk. Manchas na parede e odores de criaturas de má higiene.	{"sul": "sala_31", "norte": "sala_33"}	AgACAgEAAxkDAAIWMGnuoIHPNOb0dhGgiEkd9GP_t2KxAAJ9DGsbd6B4R1knkEr97k15AQADAgADeQADOwQ	[]
sala_33	Área 33: Sala de Prática	Goblins praticam azagaias em bonecos de estopa parecidos com humanos e elfos. Licor goblin pelo chão.	{"sul": "sala_32", "norte": "sala_36a", "leste": "sala_34"}	AgACAgEAAxkDAAIWN2nuoT9FeJRj_4vjOB-UARChD69BAAJ-DGsbd6B4R0638kLvLU1SAQADAgADeQADOwQ	[]
sala_34	Área 34: Prisão Militar Goblin	Imundície reina. Kobolds amarrados e o gnomo Erky Timbers definha dentro de uma jaula de ferro pequena demais.	{"oeste": "sala_33"}	AgACAgEAAxkDAAIWPWnuoZQl9EeL1cKNr2xbNc6bAAExagACfwxrG3egeEf9-z0_HElD2wEAAwIAA3kAAzsE	[]
sala_35	Área 35: Corredor com Armadilha	Corredor comum com alçapão no solo. No fundo do poço há um anel de ouro com safira.	{"norte": "sala_36a", "sul": "sala_37"}	\N	[]
sala_36a	Área 36: Salteadores Goblins (Quartel A)	Lixo e carne podre. Seis redes de peles em volta de um fogão de lenha. Seis goblins 'salteadores' habitam aqui.	{"sul": "sala_33", "norte": "sala_38", "leste": "sala_36b"}	AgACAgEAAxkDAAIWSWnuogproPP3bF2AUCVYsTddAoRlAAKADGsbd6B4R_AbvnlZA1ZCAQADAgADeQADOwQ	[]
sala_36b	Área 36: Salteadores Goblins (Quartel B)	Outro quartel idêntico. Utensílios velhos e armas quebradas amontoadas com armaduras gastas.	{"oeste": "sala_36a", "norte": "sala_39", "leste": "sala_36c"}	\N	[]
sala_36c	Área 36: Salteadores Goblins (Quartel C)	Terceiro quartel em condições deploráveis. Odres de vinho estragado e restos podres.	{"oeste": "sala_36b", "norte": "sala_40"}	\N	[]
sala_37	Área 37: Sala dos Troféus (Calcryx!)	Cabeças de animais empalhados. Camadas de gelo recobrem as paredes — aqui está Calcryx, o filhote de dragão branco.	{"norte": "sala_35", "leste": "sala_38"}	\N	[]
sala_38	Área 38: Passagem Goblin	Câmara de estoque: água, carne e óleo. Barris com a escrita: 'pudim elfico'.	{"sul": "sala_36a", "oeste": "sala_37", "norte": "sala_39"}	AgACAgEAAxkDAAIWUGnuooG7gvf0XSpbwIXiPhlUIXPRAAKBDGsbd6B4R1EdwPQ2FadOAQADAgADeQADOwQ	[]
sala_39	Área 39: Fumaça do Dragão	Saguão cheio de fumaça que atrapalha a visão. Fileira dupla de figuras de mármore com dragões enlaçados.	{"sul": "sala_36b", "oeste": "sala_38", "norte": "sala_40"}	AgACAgEAAxkDAAIWVWnuos_EzB29oasBqnBPKOKa92DfAAKCDGsbd6B4R4SCuSmxhDUMAQADAgADeQADOwQ	[]
sala_40	Área 40: Vilarejo Goblin	Antiga catedral agora covil goblin. Fungos com brilho violeta iluminam dezenas de goblins em seus afazeres.	{"sul": "sala_36c", "leste": "sala_39", "norte": "sala_41"}	AgACAgEAAxkDAAIWWmnuowMkDvCNJxttKTY7clnXtFMvAAKDDGsbd6B4RyEdOhPpMNTAAQADAgADeQADOwQ	[]
sala_41	Área 41: Câmara do Chefe Goblin (Durnn)	Trono de pedra e arca de ferro. Durnn, o robgoblin, rege a tribo acima do poço de vinhas que desce ao Bosque.	{"sul": "sala_40", "baixo": "sala_42"}	AgACAgEAAxkDAAIWXWnuoyjRVUiHQ0drqyRxiXxEuT2CAAKEDGsbd6B4R_CoF8TB5ZtpAQADAgADeQADOwQ	[]
sala_42	Área 42: Central de Adubo	Bosque do Crepúsculo. Ramos secos e esqueletos remexem adubo para nutrir as plantas de Belak.	{"cima": "sala_41", "norte": "sala_43"}	AgACAgEAAxkDAAIWYmnuo2rTQqaS88iJitX-ZXDQUly_AAKFDGsbd6B4R0CXp1TuJ2MpAQADAgADeQADOwQ	[]
sala_43	Área 43: O Grande Caçador (Balsag)	Chão rústico manchado. Balsag, o bugbear, e seus dois ratos caçadores habitam aqui.	{"sul": "sala_42", "norte": "sala_47", "leste": "sala_44"}	AgACAgEAAxkDAAIWZWnuo4PShcqiT6AmQfMyuHp5zVvIAAKGDGsbd6B4R3f9DTb2st_9AQADAgADeQADOwQ	[]
sala_44	Área 44: Fenda	Terra partida por desastre geológico. Cheiro de enxofre e buracos de 30cm no chão.	{"oeste": "sala_43", "norte": "sala_45"}	AgACAgEAAxkDAAIWaGnuo5prxbqvl5MU-10OKDgpYE5KAAKHDGsbd6B4R0ZONIDw9jYaAQADAgADeQADOwQ	[]
sala_45	Área 45: Nódulo da Fenda (Thoqqua)	Antecâmara de pedra com luz flamejante. Habitada por um thoqqua incandescente.	{"sul": "sala_44"}	AgACAgEAAxkDAAIWa2nuo68agf4CPGEkPAiZ0zBPIpmEAAKIDGsbd6B4R2R6GxkCuXIHAQADAgADeQADOwQ	[]
sala_46	Área 46: O Antigo Altar	Pedestal de metal na forma de um dragão ereto. Mosaicos desbotados recobrem as paredes.	{"leste": "sala_47"}	\N	[]
sala_47	Área 47: Comunidade Goblin de Belak	Colunas envoltas em fungos luminescentes. Goblins servos de Belak trabalham com pilões e argila.	{"sul": "sala_43", "oeste": "sala_46", "norte": "sala_49"}	AgACAgEAAxkDAAIWhmnuo-PyIH9MP96L1mLmmRIYARrVAAKJDGsbd6B4R1LyLq484Mt4AQADAgADeQADOwQ	[]
sala_48	Área 48: Galeria (Jardins de Belak)	Estufas de Belak. Vegetação da superfície crescendo no subterrâneo. Jardineiro bugbear com foice longa.	{"sul": "sala_47", "norte": "sala_49"}	\N	[]
sala_49	Área 49: Arvoredo (Centro do Bosque)	Quatro arvoredos com odor de podridão e brilho verde-pálido. Centro vital habitado por servos de Belak.	{"sul": "sala_47", "norte": "sala_54", "oeste": "sala_50", "leste": "sala_52"}	AgACAgEAAxkDAAIWi2nuo_uhbH1mC9vy5JvDQSzMW2scAAKKDGsbd6B4R4Fg9L_i_WCvAQADAgADeQADOwQ	[]
sala_50	Área 50: Templo de Ashardalon	Blocos de granito com dragões. Estátua de dragão com olhos vermelhos brilhantes. Uma Sombra espreita aqui.	{"leste": "sala_49", "norte": "sala_51"}	AgACAgEAAxkDAAIWjmnupBSnmugLVko96_ukQzS6J_W8AAKLDGsbd6B4R3iQUXIevQjzAQADAgADeQADOwQ	[]
sala_51	Área 51: Biblioteca dos Dragões	Estantes de pedra inclinadas e páginas queimadas. Pergaminhos valiosos escondidos sob o lixo.	{"sul": "sala_50", "norte": "sala_53"}	AgACAgEAAxkDAAIWk2nupCtp1eT5Y4W-Sq8KKSayWXWbAAKMDGsbd6B4R-iJysQjYIYRAQADAgADeQADOwQ	[]
sala_52	Área 52: Passagem Subterrânea	Degraus úmidos descendo sob a área 49. Passagem destruída e inundada.	{"oeste": "sala_49"}	\N	[]
sala_53	Área 53: Aposentos de Belak	Tomos e pergaminhos de Belak. Arbustos pálidos crescendo no solo sob fungos do teto.	{"sul": "sala_51"}	AgACAgEAAxkDAAIWlmnupEIOAnbSM94nP_NcvD5nr0RrAAKNDGsbd6B4R3XBixJ_I9H0AQADAgADeQADOwQ	[]
sala_54	Área 54: Portão do Bosque	Goblins separam galhos diante da caverna ampla. Nódulos de fungos iluminam o bosque de brotos doentes.	{"sul": "sala_49", "norte": "sala_55"}	\N	[]
sala_55	Área 55: Bosque do Crepúsculo	Vegetação pálida banhando-se na radiação fraca dos fungos. Ramos secos estão enraizados aqui.	{"sul": "sala_54", "norte": "sala_56"}	\N	[]
sala_56	Área 56: A Árvore Gulthias (BOSS FINAL)	Colossal abominação de madeira negra. Belak e os corrompidos Bradford e Sharwyn aguardam no centro.	{"sul": "sala_55"}	\N	[]
sala_13	Área 13: Corredor de Entrada Kobold	Um corredor com barricadas improvisadas de kobolds. O fedor de muitos corpos em área tão pequena saturou o ar. Um pequeno círculo de brasas no meio foi construído com lajes quebradas.	{"sul": "sala_12", "norte": "sala_15", "oeste": "sala_14", "leste": "sala_16"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-62Lymrf3u5J8ILoe1vGkAMlC.png?st=2026-05-01T23%3A28%3A59Z&se=2026-05-02T01%3A28%3A59Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=38e27a3b-6174-4d3e-90ac-d7d9ad49543f&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-01T14%3A16%3A55Z&ske=2026-05-02T14%3A16%3A55Z&sks=b&skv=2026-02-06&sig=Vau8MfFrhPEGtozazpw/x7D9Kc/IQdMqD0u0/ridncI%3D	[]
sala_16	Área 16: Kobolds Sentinelas	O fedor de muitos corpos saturou o ar. Um pequeno círculo de brasas no meio da câmara. Diversos humanóides pequenos com escamas habitam a câmara.	{"oeste": "sala_13", "leste": "sala_17"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-5e51BCbkpVvo0WqGQwB2i6gS.png?st=2026-05-01T23%3A31%3A52Z&se=2026-05-02T01%3A31%3A52Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=0e2a3d55-e963-40c9-9c89-2a1aa28cb3ac&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-01T11%3A19%3A35Z&ske=2026-05-02T11%3A19%3A35Z&sks=b&skv=2026-02-06&sig=sR8EDiXqfZVmaYJsIMhULyGvYeTKGWCUXCiOPwsrVos%3D	[]
sala_17	Área 17: Câmara Dracônica	Uma sala cerimonial ampla com pilares esculpidos com dragões. O chão está coberto por tapetes feitos de cabelo entrelaçado e plantas mortas.	{"oeste": "sala_16", "norte": "sala_19", "leste": "sala_18"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-UPwSfMAlCX34qNjTea6iNBq3.png?st=2026-05-01T23%3A33%3A42Z&se=2026-05-02T01%3A33%3A42Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=8eb2c87c-0531-4dab-acb3-b5e2adddce6c&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-05-01T13%3A44%3A10Z&ske=2026-05-02T13%3A44%3A10Z&sks=b&skv=2026-02-06&sig=UvWz0wmPvMCjpZ0F9vieOJ/OECFoiojAAidZDIU8hAs%3D	[]
sala_08	Área 8: Placas de Pressão	Uma pequena câmara com uma placa de pressão ligeiramente elevada no centro do chão. O mecanismo, se ativado, dispara setas da parte superior da porta oeste. O pó espesso e intocado sugere que esta câmara permaneceu selada há eras.	{"sul": "sala_07", "norte": "sala_09"}	https://oaidalleapiprodscus.blob.core.windows.net/private/org-MrOi5yR39Inx8BCr0KjHoizm/user-uUFJI3k6p29w5LlGglOZVu8g/img-4XIkHqJDOAlbxWnd0PhIZe2y.png?st=2026-04-28T19%3A56%3A59Z&se=2026-04-28T21%3A56%3A59Z&sp=r&sv=2026-02-06&sr=b&rscd=inline&rsct=image/png&skoid=ae240de5-197c-4e03-af8e-c66aed9a4539&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2026-04-28T14%3A00%3A43Z&ske=2026-04-29T14%3A00%3A43Z&sks=b&skv=2026-02-06&sig=Z9xPG89LGGGHR4VrtHcMMqCIDa8rlEjlT7Hde4Z8wbo%3D	[]
estrada_triboar	Emboscada na Estrada de Triboar	A estrada de terra se estreita aqui, com um barranco alto e moitas dos dois lados. Dois cavalos mortos, crivados de flechas negras, bloqueiam o caminho.	{"norte": "trilha_goblin"}	\N	[]
trilha_goblin	Trilha Goblin nos Matos	Uma trilha escura e traiçoeira serpenteia por um bosque denso. Marcas de arrasto no chão indicam que corpos foram puxados por aqui.	{"noroeste": "caverna_entrada", "sul": "estrada_triboar"}	\N	[]
caverna_entrada	Entrada da Caverna Dentefino	Uma larga abertura ao lado de um morro. Um riacho raso flui do interior da caverna, deixando um caminho estreito do lado direito.	{"leste": "caverna_vigias", "norte": "caverna_canil", "noroeste": "caverna_passagem", "sul": "trilha_goblin"}	\N	[]
caverna_vigias	Posto de Vigia	Clareira entre arbustos espinhosos. Tábuas formam um abrigo improvisado para os guardas goblins.	{"oeste": "caverna_entrada"}	\N	[]
caverna_canil	Canil dos Lobos	Câmara escura com cheiro de pelo molhado e carne podre. Estalagmites no chão e uma fissura que sobe como chaminé natural.	{"sul": "caverna_entrada", "acima": "caverna_klarg"}	\N	[]
caverna_passagem	Passagem Estreita e Ponte	O túnel sobe acompanhando o riacho. No alto, uma ponte frágil de madeira e cordas cruza a passagem nas sombras do teto.	{"sul": "caverna_entrada", "oeste": "caverna_covil", "norte": "caverna_tanques"}	\N	[]
caverna_covil	Covil dos Goblins	Gruta larga com degrau íngreme. Ar enfumaçado. Sildar Hallwinter está amarrado e amordaçado num canto.	{"leste": "caverna_passagem"}	\N	[]
caverna_tanques	Caverna dos Tanques Duplos	Barulho ensurdecedor de cachoeira. Dois tanques de água represada por muros frágeis de pedra.	{"sul": "caverna_passagem", "oeste": "caverna_klarg"}	\N	[]
caverna_klarg	Caverna de Klarg	Caverna ampla com fogueira no centro. Sacos e caixas com o símbolo do Leão Azul empilhados no fundo.	{"leste": "caverna_tanques", "abaixo": "caverna_canil"}	\N	[]
phandalin_centro	Praça de Phandalin	Vila rústica e poeirenta. Aqui ficam a Estalagem Colina de Pedra, Provisões Barthen e o Posto de Trocas Escudo do Leão.	{"norte": "mansao_tresendar_ext", "leste": "estrada_triboar"}	\N	[]
mansao_tresendar_ext	Ruínas da Mansão Tresendar	Fundações de pedra de uma mansão antiga. Um porão escuro desce para as profundezas.	{"sul": "phandalin_centro", "abaixo": "marcar_adega"}	\N	[]
marcar_adega	Adega dos Marcarrubras	Barris de cerveja e grande cisterna. Cheiro de umidade. Uma parede parece falsa...	{"acima": "mansao_tresendar_ext", "norte": "marcar_corredor", "segredo": "marcar_fenda"}	\N	[]
marcar_corredor	Corredor Principal	Corredor largo de pedra que conecta os cômodos do esconderijo.	{"sul": "marcar_adega", "leste": "marcar_barracas", "norte": "marcar_fenda"}	\N	[]
marcar_barracas	Alojamento dos Bandidos	Camas desarrumadas e restos de comida. Bandidos de mantos vermelhos jogam cartas.	{"oeste": "marcar_corredor"}	\N	[]
marcar_fenda	Caverna da Fenda	Fenda profunda e fria divide a caverna. Cheiro de carne podre. Algo brilha entre os detritos.	{"sul": "marcar_corredor", "oeste": "marcar_laboratorio"}	\N	[]
marcar_laboratorio	Laboratório de Iarno	Laboratório alquímico com livros, pergaminhos e frascos borbulhantes. Iarno, o mago renegado, trabalha aqui.	{"leste": "marcar_fenda"}	\N	[]
conyberry_agatha	Covil de Agatha (Conyberry)	Cabana de galhos numa aldeia abandonada. Ar frio e silêncio absoluto.	{"sul": "phandalin_centro"}	\N	[]
poco_coruja_velha	Poço da Coruja Velha	Ruínas de torre de vigia. Tenda colorida montada perto do poço.	{"oeste": "phandalin_centro"}	\N	[]
torre_wyvern	Torre de Wyvern	Afloramento rochoso com caverna rasa. Cheiro de carne podre e fumaça.	{"norte": "phandalin_centro"}	\N	[]
cragmaw_ext	Frente do Castelo Cragmaw	Ruínas de castelo com torres desmoronadas. Flechas espreitam das frestas escuras.	{"norte": "cragmaw_salao", "leste": "cragmaw_torre_urso"}	\N	[]
cragmaw_salao	Salão de Banquetes	Teto parcialmente caído. Mesas cobertas de restos de comida estragada.	{"sul": "cragmaw_ext", "oeste": "cragmaw_rei"}	\N	[]
cragmaw_torre_urso	Torre do Urso-Coruja	Chão coberto de ossos roídos e penas. Teto desabado, aberto ao céu.	{"oeste": "cragmaw_ext"}	\N	[]
cragmaw_rei	Aposentos do Rei Grol	Cama de peles nojentas. Gundren está caído e ferido. Mapas sobre uma mesa improvisada.	{"leste": "cragmaw_salao"}	\N	[]
thundertree_ruinas	Ruínas de Thundertree	Casas destruídas por erupção. Arbustos mortos com espinhos. Uma torre no alto da colina.	{"norte": "thundertree_torre", "leste": "wave_entrada_mina"}	\N	[]
thundertree_torre	Torre de Venomfang	Torre no topo da colina. Ar com cheiro de cloro. Tesouros velhos cobrem o chão.	{"sul": "thundertree_ruinas"}	\N	[]
wave_entrada_mina	Entrada dos Túneis da Mina	Rede de túneis antigos. Esqueletos de anões e orcs jazem aqui.	{"norte": "wave_caverna_fungos", "sul": "thundertree_ruinas", "oeste": "wave_escritorio"}	\N	[]
wave_escritorio	Escritório dos Avaliadores	Mesas empoeiradas e livros apodrecidos. Cofre de ferro aberto.	{"leste": "wave_entrada_mina"}	\N	[]
wave_caverna_fungos	Caverna dos Fungos	Tapete de cogumelos fosforescentes. Vapor estranho e esporos flutuando.	{"sul": "wave_entrada_mina", "norte": "wave_grande_caverna"}	\N	[]
wave_grande_caverna	A Grande Caverna	Câmara vasta com estalactites imensas. Som ensurdecedor das 'ondas' ecoa.	{"sul": "wave_caverna_fungos", "norte": "caverna_eco_forja", "leste": "wave_aposentos_mago"}	\N	[]
wave_aposentos_mago	Aposentos do Mago (Mormesk)	Sala luxuosa em ruínas. Mormesk, o Espectro, flutua sobre uma cama apodrecida.	{"oeste": "wave_grande_caverna"}	\N	[]
caverna_eco_forja	A Forja das Magias	Fogo verde em braseiro esférico. Crânio Flamejante guarda a sala. Runas anãs nas paredes.	{"sul": "wave_grande_caverna"}	\N	[]
caverna_eco_templo	Templo de Dumathoin	Colunas anãs esculpidas. Nezznar analisa mapas. Teias gigantes nas paredes.	{"oeste": "wave_grande_caverna"}	\N	[]
wave_caverna_estrelada	Caverna Estrelada	Cristais no teto brilham como estrelas. Beleza que contrasta com o perigo.	{"norte": "caverna_eco_templo", "sul": "wave_grande_caverna"}	\N	[]
\.


--
-- Data for Name: combate_states; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.combate_states (id, room_id, party_id, turn_index, round, status, participants_order, created_at, updated_at) FROM stdin;
4	sala_01	PTY-HN0ER	0	1	active	[{"type": "character", "id": "5326646936", "nome": "poc"}, {"type": "monster_group", "id": 40, "nome": "Rato Atroz", "quantidade": 3, "ini_bonus": 1}]	2026-05-06T17:53:14.954561	2026-05-06T17:53:14.954577
\.


--
-- Data for Name: criacao_ficha; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.criacao_ficha (telefone, etapa, dados_temp, criado_em, atualizado_em) FROM stdin;
\.


--
-- Data for Name: diario_thorak; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.diario_thorak (id, data_hora, evento, sala_atual, hp_restante) FROM stdin;
1	2026-02-19 16:48:06.591611	O anão Thorak encarou Belak e a Árvore Gulthias. O destino de Carvalhal foi selado.	clareira_44	8
\.


--
-- Data for Name: documentos_aventura; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.documentos_aventura (id, nome_item, conteudo_texto, sala_onde_encontra) FROM stdin;
1	O Mapa de Belak	Um rascunho em couro mostrando a conexão entre a fenda (Área 45) e o mundo exterior. Revela que o druida tinha planos de expandir o bosque para a superfície.	laboratorio_35
2	Inscrição da Árvore	Diz a lenda que a árvore nasceu de uma estaca cravada no coração de um vampiro chamado Gulthias. O mal dele agora flui pela seiva.	clareira_44
3	Registros de Oakhurst	Uma lista de nomes de aldeões que compraram a maçã branca nos últimos 10 anos. Muitos deles desapareceram ou "mudaram de personalidade".	conclusao_46
\.


--
-- Data for Name: encontros; Type: TABLE DATA; Schema: public; Owner: user_8W2mTA
--

COPY public.encontros (id, cod_sala, quantidade, condicao_aparecimento, ativo, nome_inimigo, dificuldade, item_drop, multiplicador_ameaca) FROM stdin;
90	sala_32	2	sempre	t	Goblin Salteador	\N	\N	1
91	sala_33	3	sempre	t	Goblin Salteador	\N	\N	1
92	sala_40	4	sempre	t	Goblin Salteador	\N	\N	1
93	sala_41	2	sempre	t	Hobgoblin Guarda-costas	\N	\N	1
94	sala_41	1	sempre	t	Grenl (Xamã)	\N	\N	1
95	sala_43	2	sempre	t	Rato Atroz de Estimação	\N	\N	1
96	sala_45	1	sempre	t	Thoqqua	\N	\N	1
97	sala_56	4	sempre	t	Muda de Arvoredo	\N	\N	1
98	sala_56	1	sempre	t	Sapo Gigante	\N	\N	1
131	sala_54	4	sempre	t	Goblin Salteador	\N	\N	1
132	sala_55	4	sempre	t	Muda de Arvoredo	\N	\N	1
40	sala_01	3	sempre	t	Rato Atroz	\N	\N	1
41	sala_05	3	sempre	t	Esqueleto Guardião	\N	\N	1
42	sala_11	1	sempre	t	Sacerdote-Troll	\N	\N	1
43	sala_16	3	sempre	t	Kobold Sentinela	\N	\N	1
44	sala_21	1	sempre	t	Yusdrayl (Feiticeira)	\N	\N	1
45	sala_30	1	sempre	t	Rato Atroz (Gutash)	\N	\N	1
46	sala_36a	6	sempre	t	Goblin Salteador	\N	\N	1
47	sala_37	1	sempre	t	Calcryx (Filhote Dragão)	\N	\N	1
48	sala_41	1	sempre	t	Durnn (Chefe Goblin)	\N	\N	1
49	sala_43	1	sempre	t	Balsag (Bugbear)	\N	\N	1
50	sala_48	1	sempre	t	Bugbear Jardineiro	\N	\N	1
51	sala_56	1	sempre	t	Belak o Proscrito	\N	\N	1
52	sala_56	1	sempre	t	Sir Bradford (Corrompido)	\N	\N	1
53	sala_56	1	sempre	t	Sharwyn (Corrompida)	\N	\N	1
99	estrada_triboar	4	sempre	t	Goblin Salteador	\N	\N	1
100	caverna_vigias	2	sempre	t	Goblin Salteador	\N	\N	1
101	caverna_canil	3	sempre	t	Lobo	\N	\N	1
102	caverna_passagem	1	sempre	t	Goblin Salteador	\N	\N	1
103	caverna_covil	5	sempre	t	Goblin Salteador	\N	\N	1
104	caverna_covil	1	sempre	t	Yeemik (Líder Goblin)	\N	\N	1
105	caverna_tanques	3	sempre	t	Goblin Salteador	\N	\N	1
106	caverna_klarg	1	sempre	t	Klarg (Bugbear Chefe)	\N	\N	1
107	caverna_klarg	1	sempre	t	Lobo	\N	\N	1
108	caverna_klarg	2	sempre	t	Goblin Salteador	\N	\N	1
109	marcar_barracas	3	sempre	t	Bandido Marcarrubra	\N	\N	1
110	marcar_fenda	1	sempre	t	Nothic	\N	\N	1
111	marcar_laboratorio	1	sempre	t	Iarno 'Bastão de Vidro'	\N	\N	1
112	conyberry_agatha	1	sempre	t	Agatha (Banshee)	\N	\N	1
113	poco_coruja_velha	1	sempre	t	Hamun Kost (Mago Maligno)	\N	\N	1
114	poco_coruja_velha	12	sempre	t	Zumbi de Hamun	\N	\N	1
115	torre_wyvern	1	sempre	t	Brughor Axebiter (Líder Orc)	\N	\N	1
116	torre_wyvern	1	sempre	t	Ogre (Grog)	\N	\N	1
117	torre_wyvern	6	sempre	t	Goblin Salteador	\N	\N	1
118	cragmaw_salao	4	sempre	t	Hobgoblin	\N	\N	1
119	cragmaw_torre_urso	1	sempre	t	Urso-Coruja	\N	\N	1
120	cragmaw_rei	1	sempre	t	Rei Grol	\N	\N	1
121	cragmaw_rei	1	sempre	t	Doppelganger	\N	\N	1
122	thundertree_ruinas	3	sempre	t	Zumbi das Cinzas	\N	\N	1
123	thundertree_torre	1	sempre	t	Venomfang (Dragão Verde Jovem)	\N	\N	1
124	wave_entrada_mina	3	sempre	t	Ghouls Famintos	\N	\N	1
125	wave_caverna_fungos	5	sempre	t	Zumbi de Hamun	\N	\N	1
126	wave_grande_caverna	2	sempre	t	Verme da Cripta	\N	\N	1
127	wave_aposentos_mago	1	sempre	t	Mormesk, o Espectro	\N	\N	1
128	caverna_eco_forja	1	sempre	t	Crânio Flamejante	\N	\N	1
129	caverna_eco_templo	2	sempre	t	Aranha Gigante	\N	\N	1
130	caverna_eco_templo	1	sempre	t	Nezznar, o Aranha Negra	\N	\N	1
137	sala_15	1	sempre	t	Meepo (Kobold)	\N	\N	1
138	sala_21	6	sempre	t	Kobold	\N	\N	1
\.


--
-- Data for Name: encontros_aleatorios; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.encontros_aleatorios (id, cod_sala, nome_inimigo, quantidade, chance) FROM stdin;
\.


--
-- Data for Name: encontros_salas; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.encontros_salas (id, cod_sala, nome_inimigo, quantidade, condicao_aparecimento, ativo) FROM stdin;
1	sala_01	Rato Atroz	3	sempre	t
2	sala_05	Esqueleto Guardião	3	sempre	t
3	sala_11	Sacerdote-Troll	1	sempre	t
4	sala_16	Kobold Sentinela	3	sempre	t
5	sala_21	Yusdrayl (Feiticeira)	1	sempre	t
6	sala_30	Rato Atroz (Gutash)	1	sempre	t
7	sala_36a	Goblin Salteador	6	sempre	t
8	sala_37	Calcryx (Filhote Dragão)	1	sempre	t
9	sala_41	Durnn (Chefe Goblin)	1	sempre	t
10	sala_43	Balsag (Bugbear)	1	sempre	t
11	sala_48	Bugbear Jardineiro	1	sempre	t
12	sala_56	Belak o Proscrito	1	sempre	t
13	sala_56	Sir Bradford (Corrompido)	1	sempre	t
14	sala_56	Sharwyn (Corrompida)	1	sempre	t
\.


--
-- Data for Name: estatisticas_jogador; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.estatisticas_jogador (jogador_telefone, inimigos_derrotados, vezes_derrotado, danos_causados_total, danos_recebidos_total, total_ataques_acertados, total_ataques_errados, criticos_acertados, fumbles_rolados, salas_visitadas, salas_desbloqueadas_count, xp_ganho_total, ouro_ganho_total, ouro_perdido_total, testes_realizados, testes_sucesso, testes_falha, descansos_curtos, intervencoes_divinas, primeira_sessao, ultima_sessao, tempo_jogo_minutos) FROM stdin;
5326646936	0	0	0	0	0	0	0	0	["carvalhal"]	1	0	0	0	0	0	0	0	0	2026-04-28T00:31:07.075020	2026-04-28T00:31:07.077025	0
\.


--
-- Data for Name: estatisticas_jogadores; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.estatisticas_jogadores (jogador_telefone, inimigos_derrotados, vezes_derrotado, total_ataques_acertados, total_ataques_errados, danos_causados_total, danos_recebidos_total, criticos_acertados, fumbles_rolados, salas_visitadas, salas_desbloqueadas_count, xp_ganho_total, ouro_ganho_total, ouro_perdido_total, testes_realizados, testes_sucesso, testes_falha, descansos_curtos, intervencoes_divinas, primeira_sessao, ultima_sessao, tempo_jogo_minutos) FROM stdin;
6519451215	0	0	0	0	0	0	0	0	["carvalhal", "estrada_velha", "ravina_escura", "sala_01"]	4	0	0	0	0	0	0	0	0	2026-04-23T23:07:42.257983	2026-04-23T23:07:42.259948	8
7957386305	0	0	0	0	0	0	0	0	["carvalhal"]	1	0	0	0	0	0	0	0	0	2026-04-30T02:58:20.181990	2026-04-30T02:58:20.183607	2
5326646936	0	0	0	0	0	0	0	0	["carvalhal"]	1	0	0	0	0	0	0	0	0	2026-05-07T14:03:53.017070	2026-05-07T14:03:53.338876	8
121065310	0	0	0	0	0	0	0	0	["carvalhal"]	1	0	0	0	0	0	0	0	0	2026-04-30T19:00:42.138597	2026-05-01T04:37:13.486361	14
\.


--
-- Data for Name: grimorio_cidadela; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.grimorio_cidadela (id, nome_magia, nivel, alcance, efeito) FROM stdin;
1	Mísseis Mágicos	1	30 metros	Cria 3 dardos de energia que acertam automaticamente. Dano: 1d4+1 por dardo.
2	Curar Ferimentos Leves	1	Toque	Cura 1d8+1 pontos de vida de uma criatura.
3	Emaranhar	1	120 metros	Plantas prendem as criaturas em uma área. Exige teste de Reflexos (CD 13) para não ficar imóvel.
4	Clava Mística (Shillelagh)	0	Toque	Transforma um pedaço de madeira em uma arma mágica. Dano aumenta para 1d6+2.
5	Mísseis Mágicos	1	30 metros	Cria 3 dardos de energia que acertam automaticamente. Dano: 1d4+1 por dardo.
6	Curar Ferimentos Leves	1	Toque	Cura 1d8+1 pontos de vida de uma criatura.
7	Emaranhar	1	120 metros	Plantas prendem as criaturas em uma área. Exige teste de Reflexos (CD 13) para não ficar imóvel.
8	Clava Mística (Shillelagh)	0	Toque	Transforma um pedaço de madeira em uma arma mágica. Dano aumenta para 1d6+2.
\.


--
-- Data for Name: historico_partidas; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.historico_partidas (id, jogador_telefone, data_inicio, data_fim, resultado, inimigos_derrotados, ouro_coletado, xp_ganho, sala_final) FROM stdin;
8	7957386305	2026-04-30T02:58:20.183628	\N	em_andamento	0	0	0	carvalhal
9	121065310	2026-04-30T19:00:42.140502	\N	em_andamento	0	0	0	carvalhal
19	121065310	2026-05-01T04:37:13.486385	\N	em_andamento	0	0	0	carvalhal
36	5326646936	2026-05-07T14:03:53.338876	\N	em_andamento	0	0	0	carvalhal
\.


--
-- Data for Name: inimigos; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.inimigos (id, nome, hp_max, ca, ataque, dano, imagem_url, xp_recompensa, ouro_recompensa, is_boss, loot_especial) FROM stdin;
1	Rato Atroz	7	10	+4	\N	\N	25	1	f	[]
2	Ramo Seco	4	10	+1	\N	\N	10	0	f	[]
3	Kobold Sentinela	5	12	+4	\N	\N	25	2	f	[]
4	Goblin Salteador	7	13	+4	\N	\N	50	3	f	[]
5	Goblin Guerreiro	10	15	+4	\N	\N	50	5	f	[]
6	Robgoblin Guerreiro	11	18	+3	\N	\N	100	10	f	[]
8	Calcryx (Filhote Dragão)	33	17	+7	\N	\N	450	100	f	[]
9	Belak o Proscrito	40	15	+4	\N	\N	700	200	f	[]
10	Sacerdote-Troll	45	15	+5	\N	\N	450	50	f	[]
7	Durnn (Chefe Goblin)	25	16	+5	\N	\N	450	50	t	["Espada Longa de Durnn", "Chave do Chefe"]
11	Lobo	11	13	+4	2d4+2	\N	50	0	f	[]
12	Yeemik (Líder Goblin)	12	15	+4	1d6+2	\N	50	5	f	["Po\\u00e7\\u00e3o de Cura"]
13	Klarg (Bugbear Chefe)	45	16	+5	2d8+3	\N	200	15	t	["Estrela da Manh\\u00e3 do Klarg"]
14	Bandido Marcarrubra	16	14	+4	1d6+2	\N	100	5	f	[]
15	Nothic	45	15	+4	1d6+3	\N	450	0	f	[]
16	Iarno 'Bastão de Vidro'	38	13	+4	2d10	\N	200	50	t	["Bast\\u00e3o de Vidro", "Pergaminho de M\\u00edsseis M\\u00e1gicos"]
17	Agatha (Banshee)	58	12	+4	3d6+2	\N	1100	0	t	[]
18	Hamun Kost (Mago Maligno)	35	12	+4	1d10	\N	450	35	f	["Anel de Prote\\u00e7\\u00e3o"]
19	Zumbi de Hamun	22	8	+3	1d6+1	\N	50	0	f	[]
20	Brughor Axebiter (Líder Orc)	30	13	+5	1d12+3	\N	200	10	t	[]
21	Ogre (Grog)	59	11	+6	2d8+4	\N	450	0	f	[]
22	Hobgoblin	11	18	+3	1d8+1	\N	100	2	f	["Espada Longa"]
23	Urso-Coruja	59	13	+7	1d10+5	\N	700	0	t	[]
24	Rei Grol	85	17	+6	1d12+4	\N	450	50	t	[]
25	Doppelganger	52	14	+6	1d6+4	\N	700	15	f	[]
26	Zumbi das Cinzas	22	8	+3	1d6+1	\N	50	0	f	[]
27	Venomfang (Dragão Verde Jovem)	165	18	+7	2d10+4	\N	3900	200	t	[]
28	Crânio Flamejante	40	13	+5	2d6	\N	1100	0	t	[]
29	Aranha Gigante	26	14	+5	1d8+3	\N	200	0	f	[]
30	Mormesk, o Espectro	45	13	+5	3d6+3	\N	1100	0	t	[]
31	Ghouls Famintos	22	12	+2	2d6+2	\N	200	0	f	[]
32	Verme da Cripta	33	11	+4	2d4+2	\N	450	0	f	[]
33	Nezznar, o Aranha Negra	75	15	+5	1d8+3	\N	2300	150	t	["Cajado da Aranha", "Pingente do Le\\u00e3o de Ouro"]
34	Sharwyn (Corrompida)	7	\N	\N	\N	\N	\N	\N	t	[]
35	Muda de Arvoredo	5	\N	\N	\N	\N	\N	\N	f	[]
36	Esqueleto Guardião	9	\N	\N	\N	\N	\N	\N	f	[]
37	Rato Atroz de Estimação	5	\N	\N	\N	\N	\N	\N	f	[]
38	Thoqqua	16	\N	\N	\N	\N	\N	\N	f	[]
39	Hobgoblin Guarda-costas	6	\N	\N	\N	\N	\N	\N	f	[]
40	Balsag (Bugbear)	36	\N	\N	\N	\N	\N	\N	t	[]
41	Bugbear Jardineiro	16	\N	\N	\N	\N	\N	\N	f	[]
42	Sir Bradford (Corrompido)	12	\N	\N	\N	\N	\N	\N	t	[]
43	Sapo Gigante	16	\N	\N	\N	\N	\N	\N	f	[]
44	Yusdrayl (Feiticeira)	21	\N	\N	\N	\N	\N	\N	t	[]
45	Grenl (Xamã)	8	\N	\N	\N	\N	\N	\N	t	[]
46	Rato Atroz (Gutash)	18	\N	\N	\N	\N	\N	\N	t	[]
\.


--
-- Data for Name: interativos; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.interativos (id, cod_sala, nome, descricao, tipo, cd_teste, atributo_teste, recompensa, dano_falha, ativo) FROM stdin;
1	trilha_goblin	Armadilha de Laço	Laço escondido que puxa a vítima pelas pernas.	armadilha	12	DEX	[]	3	t
2	trilha_goblin	Fosso Camuflado	Buraco de 3m sob lona e folhas.	armadilha	15	WIS	[]	4	t
3	caverna_canil	Chaminé Natural	Buraco escorregadio que sobe direto para a sala do chefe.	segredo	10	STR	[]	3	t
4	caverna_tanques	Muro da Represa	Muros frágeis que podem ser destruídos para causar enchente.	alavanca	15	STR	[]	0	t
5	caverna_covil	Baú Goblin	Baú tosco atrás das camas.	bau	12	DEX	["3 Dentes de Ouro", "15 PP"]	0	t
6	caverna_klarg	Caixas do Leão Azul	Sacos e caixas com símbolo de leão azul.	bau	10	STR	["600 PC", "110 PP", "Po\\u00e7\\u00e3o de Cura", "Po\\u00e7\\u00e3o de Cura", "Estatueta de Sapo de Jade"]	0	t
7	marcar_adega	Porta Secreta	Trecho da parede parece falso.	segredo	15	INT	["Acesso \\u00e0 Caverna da Fenda"]	0	t
8	marcar_fenda	Olhar Estranho (Nothic)	Voz na mente oferece segredos em troca de carne.	dialogo	12	CHA	["Evita combate com Nothic"]	0	t
9	marcar_fenda	Espada Longa 'Talon'	Espada de prata com punho de águia brilha entre os detritos.	bau	10	INT	["Espada Longa +1 (Talon)"]	0	t
10	conyberry_agatha	Pente de Prata	Dar o presente de Garaele para Agatha.	dialogo	12	CHA	["Informa\\u00e7\\u00e3o sobre o Grim\\u00f3rio"]	0	t
11	poco_coruja_velha	Negociar com Hamun Kost	Mago quer saber sobre a torre ou a Banshee.	dialogo	15	INT	["Informa\\u00e7\\u00e3o sobre Thundertree"]	0	t
12	cragmaw_ext	Armadilha de Desmoronamento	Pedras soltas perto da entrada.	armadilha	15	DEX	[]	6	t
13	cragmaw_torre_urso	Ninho do Urso-Coruja	Algo brilha entre os ossos.	bau	12	WIS	["90 PO", "Pergaminho de Reviver"]	0	t
14	cragmaw_rei	Mapa da Mina	Mapa detalhado da Caverna Eco Ondulante.	bau	10	INT	["Mapa da Caverna Eco Ondulante", "220 PP"]	0	t
15	thundertree_torre	Negociar com Venomfang	Convencer o dragão a sair sem lutar.	dialogo	18	CHA	["Evita combate, perde tesouro"]	0	t
16	thundertree_torre	Tesouro de Venomfang	Moedas e itens entre os ossos.	bau	14	DEX	["800 PP", "150 PO", "Machado M\\u00e1gico Hew"]	0	t
17	wave_caverna_fungos	Esporos Venenosos	Caminhar descuidadamente libera esporos.	armadilha	13	CON	[]	5	t
18	wave_aposentos_mago	Pechinchar com Mormesk	Espectro pode poupar o grupo.	dialogo	14	CHA	["Acesso livre", "Dica sobre Nezznar"]	0	t
19	wave_aposentos_mago	Cachimbo de Prata	Cachimbo antigo sobre a mesa.	bau	10	WIS	["Cachimbo de Prata", "Grim\\u00f3rio Antigo"]	0	t
20	caverna_eco_forja	Braseiro Verde	Chama que encanta armas temporariamente.	magia	10	INT	["Arma +1 (1 hora)"]	2	t
21	caverna_eco_forja	Forja das Magias	Itens mágicos podem ser encontrados aqui.	bau	14	INT	["Ma\\u00e7a M\\u00e1gica Iluminadora", "Cota de Malha +1"]	0	t
22	caverna_eco_templo	Tesouro de Nezznar	Documentos roubados e um diamante.	bau	15	DEX	["Diamante de 100 PO"]	0	t
\.


--
-- Data for Name: itens_magicos; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.itens_magicos (id, nome, propriedades, valor_ouro) FROM stdin;
1	Shatterspike (Quebra-Espadas)	Espada Longa +1. Se o portador tentar quebrar a arma ou objeto de um inimigo, o dano é sempre considerado um Crítico.	2000
2	Cajado de Entalhe (Gulthias Staff)	Cajado de madeira negra. Permite ao portador usar a magia "Emaranhar" 1x por dia. O portador não é atacado por Ramos Secos (Twigs).	1500
3	Fruto da Árvore Gulthias (Vermelho)	Maçã milagrosa. Cura todas as doenças e recupera todos os PVs instantaneamente.	0
4	Fruto da Árvore Gulthias (Branco)	Maçã da Morte. Contém sementes que, se plantadas, dão origem a um novo Ramo Seco. Se ingerida, funciona como um veneno potente.	0
\.


--
-- Data for Name: jogadores; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.jogadores (telefone, party_id, cena_atual, cena_anterior, nome, classe, raca, background, nivel, xp, hp_atual, hp_maximo, str, dex, con, "int", wis, cha, mod_str, mod_dex, mod_con, mod_int, mod_wis, mod_cha, modificador_ataque, modificador_defesa, proficiencia, arma_equipada, armadura_equipada, dano_dado, mod_dano, gold, inventario, slots_magia, slots_magia_max, descanso_curto_disponivel, status_efeitos, hit_dice_max, hit_dice_atual, sexo, descricao) FROM stdin;
121065310	\N	carvalhal	\N	Rasputin	Mago	Gnomo	Sábio	1	0	8	8	7	16	14	19	12	11	-2	3	2	4	1	0	0	13	2	Adaga	Trajes Comuns	1d6	-2	15	["Grim\\u00f3rio", "Foco Arcano", "Adaga", "Pacote de Estudioso"]	2	2	t	[]	\N	\N	Masculino	\N
5326646936	PTY-90A7Y	carvalhal	\N	Psock	Bárbaro	Meio-Orc	Forasteiro	1	75	14	14	18	15	14	12	9	9	4	2	2	1	-1	-1	6	13	2	Machado Grande	Trajes Comuns	1d12	4	18	["Machado Grande", "2 Machadinhas", "4 Azagaias", "Pacote de Explorador"]	2	2	t	[]	1	1	Masculino	\N
\.


--
-- Data for Name: logs_navegacao; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.logs_navegacao (id, telefone, sala_origem, texto_digitado, sala_destino, sucesso, created_at) FROM stdin;
1	5326646936	null	sigo pelo parapeito	\N	f	2026-03-12 18:03:26.698248
2	5326646936	ravina	sigo pelo parapeito	undefined	t	2026-03-12 18:07:22.213238
3	5326646936	parapeito_01	Grishnu olha para as duas opções. Saguão de Entrada — ali pode ter informação.\nSigo para o Saguão de Entrada.	undefined	t	2026-03-12 18:08:20.14525
4	5326646936	saguao_02	🚶 Grishnu se move para Saguão de Entrada\n\nUm hall de entrada em colapso. O teto parcialmente desabou, deixando pilhas de entulho pelo chão. Colunas rachadas ainda sustentam o que resta da estrutura. Através da poeira, você vê marcas de tochas nas paredes — alguém esteve aqui recentemente.\n\n━━━━━━━━━━━━━━━━\n🗺️ Saídas disponíveis: O Parapeito, Pátio das Estátuas, Escadas Sinuosas\n\n❓ O que você faz?	undefined	t	2026-03-12 18:08:55.493864
5	5326646936	saguao_02	examino as marcas de tocha nas paredes	\N	f	2026-03-12 18:17:24.225271
6	5326646936	saguao_02	Você se aproxima das marcas de tocha nas paredes, notando que a poeira acumulada revela um padrão que sugere uma passagem frequente. As marcas parecem frescas, como se alguém tivesse passado por aqui recentemente, talvez em busca de abrigo ou para explorar a cidadela abandonada. Enquanto observa, você percebe que algumas áreas nas paredes estão mais desgastadas, indicando que as tochas foram retiradas e colocadas de volta com regularidade.\n\nNo entanto, ao se concentrar nas marcas, uma sensação de alerta surge. Você nota uma corda esticada entre duas colunas, quase invisível na penumbra, que parece ser uma armadilha rudimentar. Se você não tomar cuidado, pode acionar uma queda de pedras. O saguão de entrada continua a se desmoronar ao seu redor, e você se pergunta se deve prosseguir com cautela ou explorar mais a fundo. O que você faz?	\N	f	2026-03-12 18:18:03.403522
7	5326646936	saguao_02	examino a armadilha com cuidado para tentar desarmá-la	\N	f	2026-03-12 18:26:43.699104
8	5326646936	saguao_02	Já mandei 3 mensagens e não mexe o fluxo	\N	f	2026-03-12 18:26:43.759805
9	5326646936	saguao_02	examino a armadilha com cuidado para tentar desarmá-la	\N	f	2026-03-12 18:26:44.375271
10	5326646936	saguao_02	examino a armadilha com cuidado para tentar desarmá-la	\N	f	2026-03-12 18:26:45.174934
11	5326646936	saguao_02	Grishnu sorri. Alguém montou isso aqui — goblins ou kobolds provavelmente. Segue em frente.\nSigo pelas Escadas Sinuosas.	escadas_02	t	2026-03-12 18:27:47.800323
12	5326646936	escadas_02	Grishnu olha para os três ratos. Sorri.\nAtaco o rato mais próximo com meu machado!	\N	f	2026-03-12 18:33:48.484565
13	5326646936	escadas_02	Grishnu olha para os três ratos. Sorri.\nAtaco o rato mais próximo com meu machado!	\N	f	2026-03-12 18:36:52.780003
14	5326646936	escadas_02	/decanso_curto	\N	f	2026-03-12 18:37:47.893872
15	5326646936	escadas_02	/decanso_curto	\N	f	2026-03-12 18:45:47.74435
16	5326646936	escadas_02	/descanso	\N	f	2026-03-12 18:48:44.43242
\.


--
-- Data for Name: masmorra_cenas; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.masmorra_cenas (id, sala_id, nome_sala, descricao, inimigos, saidas) FROM stdin;
1	cidadela_entrada	O Desfiladeiro de Old Road	Uma fenda enorme se abre no chão. Escadas de pedra precárias descem para a escuridão da Cidadela. O ar é frio e cheira a terra antiga.	nenhum	baixo
\.


--
-- Data for Name: missoes; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.missoes (id, jogador_telefone, npc_nome, titulo, descricao, objetivo_item, objetivo_quantidade, recompensa_xp, recompensa_ouro, recompensa_item, concluida) FROM stdin;
2	121065310	Ferreiro de Carvalhal	Lâminas e Dentes	Goblins têm atacado as caravanas. Traz-me 3 Dentes de Goblin como prova de abate na masmorra.	Dente de Goblin	3	150	50	\N	f
3	MULTI	Gundren Buscapedra	A Entrega em Phandalin	Escoltar a carroça de suprimentos até Barthen Provisões.	Carroça de Suprimentos	1	50	10	\N	f
4	MULTI	Sildar Hallwinter	Escolta de Sildar	Garantir que Sildar chegue em segurança à Phandalin.	Sildar a salvo	1	50	50	\N	f
5	MULTI	Linene Vento Cinza	Mercadorias Roubadas	Recuperar as caixas do Leão Azul roubadas pelos goblins.	Caixas da Leão Escudo	1	50	50	\N	f
6	MULTI	Halia Thornton	Líder dos Marcarrubras	Eliminar ou capturar o líder dos Marcarrubras.	Iarno Derrotado	1	100	100	\N	f
7	MULTI	Irmã Garaele	O Pedido da Banshee	Oferecer um pente de prata à Banshee Agatha.	Resposta de Agatha	1	150	0	Poção de Cura	f
8	MULTI	Sildar Hallwinter	Resgatar Gundren	Encontrar o Castelo Cragmaw e resgatar Gundren.	Gundren Resgatado	1	200	200	\N	f
9	MULTI	Reidoth	Expulsar o Dragão	Fazer Venomfang ir embora de Thundertree.	Venomfang Expulso	1	500	0	\N	f
10	MULTI	Gundren Buscapedra	Retomar a Mina	Derrotar o Aranha Negra e limpar a Caverna Eco Ondulante.	Nezznar Derrotado	1	1000	500	10% dos lucros da mina	f
\.


--
-- Data for Name: monster_templates; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.monster_templates (id, nome, hp_base, ca, ataque_bonus, dano_dice, xp) FROM stdin;
1	Goblin	7	15	4	1d6+2	50
2	Orc	15	13	5	1d12+3	100
3	Lobo	11	13	4	2d4+2	50
4	Esqueleto	13	13	4	1d6+2	50
5	Ogre	59	11	6	2d8+4	450
6	Dragão Jovem	136	18	10	2d10+4	2900
\.


--
-- Data for Name: npcs; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.npcs (id, cod_sala, nome, descricao, dialogo_base, dialogo_item_especial, item_gatilho) FROM stdin;
\.


--
-- Data for Name: objetos_destrutiveis; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.objetos_destrutiveis (id, cod_sala, nome, descricao, hp_atual, hp_max, ca, break_threshold, resistencias, vulnerabilidades, recompensa_ao_destruir, ativo) FROM stdin;
\.


--
-- Data for Name: regras_cache; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.regras_cache (nome, openai_file_id, atualizado_em) FROM stdin;
\.


--
-- Data for Name: turnos; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.turnos (grupo_id, indice) FROM stdin;
\.


--
-- Data for Name: z_old_encontros_salas; Type: TABLE DATA; Schema: public; Owner: rpg
--

COPY public.z_old_encontros_salas (id, cod_sala, nome_inimigo, quantidade, condicao_aparecimento, ativo) FROM stdin;
103	sala_01	Rato Atroz	3	sempre	t
104	sala_05	Esqueleto Guardião	3	sempre	t
105	sala_11	Sacerdote-Troll	1	sempre	t
106	sala_16	Kobold Sentinela	3	sempre	t
107	sala_21	Yusdrayl (Feiticeira)	1	sempre	t
108	sala_30	Rato Atroz (Gutash)	1	sempre	t
109	sala_36a	Goblin Salteador	6	sempre	t
110	sala_37	Calcryx (Filhote Dragão)	1	sempre	t
111	sala_41	Durnn (Chefe Goblin)	1	sempre	t
112	sala_43	Balsag (Bugbear)	1	sempre	t
113	sala_48	Bugbear Jardineiro	1	sempre	t
114	sala_56	Belak o Proscrito	1	sempre	t
115	sala_56	Sir Bradford (Corrompido)	1	sempre	t
116	sala_56	Sharwyn (Corrompida)	1	sempre	t
\.


--
-- Name: aliados_e_npcs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.aliados_e_npcs_id_seq', 3, true);


--
-- Name: aventuras_catalogo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.aventuras_catalogo_id_seq', 3, true);


--
-- Name: aventuras_inventario_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.aventuras_inventario_id_seq', 1, false);


--
-- Name: aventuras_paragrafos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.aventuras_paragrafos_id_seq', 6, true);


--
-- Name: aventuras_progresso_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.aventuras_progresso_id_seq', 5, true);


--
-- Name: aventuras_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.aventuras_stats_id_seq', 1, false);


--
-- Name: campanhas_cenas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.campanhas_cenas_id_seq', 1, true);


--
-- Name: combate_states_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.combate_states_id_seq', 4, true);


--
-- Name: diario_thorak_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.diario_thorak_id_seq', 1, true);


--
-- Name: documentos_aventura_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.documentos_aventura_id_seq', 3, true);


--
-- Name: encontros_aleatorios_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.encontros_aleatorios_id_seq', 1, false);


--
-- Name: encontros_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user_8W2mTA
--

SELECT pg_catalog.setval('public.encontros_id_seq', 138, true);


--
-- Name: encontros_salas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.encontros_salas_id_seq', 116, true);


--
-- Name: encontros_salas_id_seq1; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.encontros_salas_id_seq1', 14, true);


--
-- Name: grimorio_cidadela_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.grimorio_cidadela_id_seq', 8, true);


--
-- Name: historico_partidas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.historico_partidas_id_seq', 36, true);


--
-- Name: inimigos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.inimigos_id_seq', 46, true);


--
-- Name: interativos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.interativos_id_seq', 22, true);


--
-- Name: itens_magicos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.itens_magicos_id_seq', 4, true);


--
-- Name: logs_navegacao_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.logs_navegacao_id_seq', 16, true);


--
-- Name: masmorra_cenas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.masmorra_cenas_id_seq', 1, true);


--
-- Name: missoes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.missoes_id_seq', 13, true);


--
-- Name: monster_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.monster_templates_id_seq', 6, true);


--
-- Name: npcs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.npcs_id_seq', 1, false);


--
-- Name: objetos_destrutiveis_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rpg
--

SELECT pg_catalog.setval('public.objetos_destrutiveis_id_seq', 1, false);


--
-- Name: aliados_e_npcs aliados_e_npcs_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aliados_e_npcs
    ADD CONSTRAINT aliados_e_npcs_pkey PRIMARY KEY (id);


--
-- Name: aventura_cidadela aventura_cidadela_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventura_cidadela
    ADD CONSTRAINT aventura_cidadela_pkey PRIMARY KEY (cod_sala);


--
-- Name: aventuras_catalogo aventuras_catalogo_nome_key; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_catalogo
    ADD CONSTRAINT aventuras_catalogo_nome_key UNIQUE (nome);


--
-- Name: aventuras_catalogo aventuras_catalogo_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_catalogo
    ADD CONSTRAINT aventuras_catalogo_pkey PRIMARY KEY (id);


--
-- Name: aventuras_inventario aventuras_inventario_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_inventario
    ADD CONSTRAINT aventuras_inventario_pkey PRIMARY KEY (id);


--
-- Name: aventuras_paragrafos aventuras_paragrafos_aventura_nome_numero_key; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_paragrafos
    ADD CONSTRAINT aventuras_paragrafos_aventura_nome_numero_key UNIQUE (aventura_nome, numero);


--
-- Name: aventuras_paragrafos aventuras_paragrafos_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_paragrafos
    ADD CONSTRAINT aventuras_paragrafos_pkey PRIMARY KEY (id);


--
-- Name: aventuras aventuras_pkey; Type: CONSTRAINT; Schema: public; Owner: user_8W2mTA
--

ALTER TABLE ONLY public.aventuras
    ADD CONSTRAINT aventuras_pkey PRIMARY KEY (id);


--
-- Name: aventuras_progresso aventuras_progresso_jogador_id_aventura_nome_key; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_progresso
    ADD CONSTRAINT aventuras_progresso_jogador_id_aventura_nome_key UNIQUE (jogador_id, aventura_nome);


--
-- Name: aventuras_progresso aventuras_progresso_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_progresso
    ADD CONSTRAINT aventuras_progresso_pkey PRIMARY KEY (id);


--
-- Name: aventuras_stats aventuras_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_stats
    ADD CONSTRAINT aventuras_stats_pkey PRIMARY KEY (id);


--
-- Name: bestiario_cidadela bestiario_cidadela_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.bestiario_cidadela
    ADD CONSTRAINT bestiario_cidadela_pkey PRIMARY KEY (nome);


--
-- Name: campanhas_cenas campanhas_cenas_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.campanhas_cenas
    ADD CONSTRAINT campanhas_cenas_pkey PRIMARY KEY (id);


--
-- Name: campanhas campanhas_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.campanhas
    ADD CONSTRAINT campanhas_pkey PRIMARY KEY (party_id);


--
-- Name: cenas cenas_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.cenas
    ADD CONSTRAINT cenas_pkey PRIMARY KEY (cod_sala);


--
-- Name: combate_states combate_states_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.combate_states
    ADD CONSTRAINT combate_states_pkey PRIMARY KEY (id);


--
-- Name: combate_states combate_states_room_id_key; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.combate_states
    ADD CONSTRAINT combate_states_room_id_key UNIQUE (room_id);


--
-- Name: criacao_ficha criacao_ficha_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.criacao_ficha
    ADD CONSTRAINT criacao_ficha_pkey PRIMARY KEY (telefone);


--
-- Name: diario_thorak diario_thorak_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.diario_thorak
    ADD CONSTRAINT diario_thorak_pkey PRIMARY KEY (id);


--
-- Name: documentos_aventura documentos_aventura_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.documentos_aventura
    ADD CONSTRAINT documentos_aventura_pkey PRIMARY KEY (id);


--
-- Name: encontros_aleatorios encontros_aleatorios_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.encontros_aleatorios
    ADD CONSTRAINT encontros_aleatorios_pkey PRIMARY KEY (id);


--
-- Name: encontros encontros_pkey; Type: CONSTRAINT; Schema: public; Owner: user_8W2mTA
--

ALTER TABLE ONLY public.encontros
    ADD CONSTRAINT encontros_pkey PRIMARY KEY (id);


--
-- Name: z_old_encontros_salas encontros_salas_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.z_old_encontros_salas
    ADD CONSTRAINT encontros_salas_pkey PRIMARY KEY (id);


--
-- Name: encontros_salas encontros_salas_pkey1; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.encontros_salas
    ADD CONSTRAINT encontros_salas_pkey1 PRIMARY KEY (id);


--
-- Name: estatisticas_jogador estatisticas_jogador_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.estatisticas_jogador
    ADD CONSTRAINT estatisticas_jogador_pkey PRIMARY KEY (jogador_telefone);


--
-- Name: estatisticas_jogadores estatisticas_jogadores_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.estatisticas_jogadores
    ADD CONSTRAINT estatisticas_jogadores_pkey PRIMARY KEY (jogador_telefone);


--
-- Name: grimorio_cidadela grimorio_cidadela_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.grimorio_cidadela
    ADD CONSTRAINT grimorio_cidadela_pkey PRIMARY KEY (id);


--
-- Name: historico_partidas historico_partidas_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.historico_partidas
    ADD CONSTRAINT historico_partidas_pkey PRIMARY KEY (id);


--
-- Name: inimigos inimigos_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.inimigos
    ADD CONSTRAINT inimigos_pkey PRIMARY KEY (id);


--
-- Name: interativos interativos_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.interativos
    ADD CONSTRAINT interativos_pkey PRIMARY KEY (id);


--
-- Name: itens_magicos itens_magicos_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.itens_magicos
    ADD CONSTRAINT itens_magicos_pkey PRIMARY KEY (id);


--
-- Name: jogadores jogadores_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.jogadores
    ADD CONSTRAINT jogadores_pkey PRIMARY KEY (telefone);


--
-- Name: logs_navegacao logs_navegacao_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.logs_navegacao
    ADD CONSTRAINT logs_navegacao_pkey PRIMARY KEY (id);


--
-- Name: masmorra_cenas masmorra_cenas_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.masmorra_cenas
    ADD CONSTRAINT masmorra_cenas_pkey PRIMARY KEY (id);


--
-- Name: masmorra_cenas masmorra_cenas_sala_id_key; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.masmorra_cenas
    ADD CONSTRAINT masmorra_cenas_sala_id_key UNIQUE (sala_id);


--
-- Name: missoes missoes_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.missoes
    ADD CONSTRAINT missoes_pkey PRIMARY KEY (id);


--
-- Name: monster_templates monster_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.monster_templates
    ADD CONSTRAINT monster_templates_pkey PRIMARY KEY (id);


--
-- Name: npcs npcs_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.npcs
    ADD CONSTRAINT npcs_pkey PRIMARY KEY (id);


--
-- Name: objetos_destrutiveis objetos_destrutiveis_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.objetos_destrutiveis
    ADD CONSTRAINT objetos_destrutiveis_pkey PRIMARY KEY (id);


--
-- Name: regras_cache regras_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.regras_cache
    ADD CONSTRAINT regras_cache_pkey PRIMARY KEY (nome);


--
-- Name: turnos turnos_pkey; Type: CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.turnos
    ADD CONSTRAINT turnos_pkey PRIMARY KEY (grupo_id);


--
-- Name: idx_aventuras_nome; Type: INDEX; Schema: public; Owner: rpg
--

CREATE INDEX idx_aventuras_nome ON public.aventuras_catalogo USING btree (nome);


--
-- Name: idx_cenas_aventura; Type: INDEX; Schema: public; Owner: rpg
--

CREATE INDEX idx_cenas_aventura ON public.campanhas_cenas USING btree (aventura_ref, cena_id);


--
-- Name: idx_criacao_telefone; Type: INDEX; Schema: public; Owner: rpg
--

CREATE INDEX idx_criacao_telefone ON public.criacao_ficha USING btree (telefone);


--
-- Name: idx_paragrafos_aventura_numero; Type: INDEX; Schema: public; Owner: rpg
--

CREATE INDEX idx_paragrafos_aventura_numero ON public.aventuras_paragrafos USING btree (aventura_nome, numero);


--
-- Name: idx_progresso_jogador; Type: INDEX; Schema: public; Owner: rpg
--

CREATE INDEX idx_progresso_jogador ON public.aventuras_progresso USING btree (jogador_id);


--
-- Name: ix_campanhas_party_id; Type: INDEX; Schema: public; Owner: rpg
--

CREATE INDEX ix_campanhas_party_id ON public.campanhas USING btree (party_id);


--
-- Name: ix_combate_states_party_id; Type: INDEX; Schema: public; Owner: rpg
--

CREATE INDEX ix_combate_states_party_id ON public.combate_states USING btree (party_id);


--
-- Name: ix_jogadores_party_id; Type: INDEX; Schema: public; Owner: rpg
--

CREATE INDEX ix_jogadores_party_id ON public.jogadores USING btree (party_id);


--
-- Name: aventuras_inventario aventuras_inventario_progresso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_inventario
    ADD CONSTRAINT aventuras_inventario_progresso_id_fkey FOREIGN KEY (progresso_id) REFERENCES public.aventuras_progresso(id) ON DELETE CASCADE;


--
-- Name: aventuras_paragrafos aventuras_paragrafos_aventura_nome_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_paragrafos
    ADD CONSTRAINT aventuras_paragrafos_aventura_nome_fkey FOREIGN KEY (aventura_nome) REFERENCES public.aventuras_catalogo(nome) ON DELETE CASCADE;


--
-- Name: aventuras_progresso aventuras_progresso_aventura_nome_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_progresso
    ADD CONSTRAINT aventuras_progresso_aventura_nome_fkey FOREIGN KEY (aventura_nome) REFERENCES public.aventuras_catalogo(nome) ON DELETE CASCADE;


--
-- Name: aventuras_stats aventuras_stats_aventura_nome_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rpg
--

ALTER TABLE ONLY public.aventuras_stats
    ADD CONSTRAINT aventuras_stats_aventura_nome_fkey FOREIGN KEY (aventura_nome) REFERENCES public.aventuras_catalogo(nome) ON DELETE CASCADE;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT USAGE ON SCHEMA public TO rpg;


--
-- PostgreSQL database dump complete
--

