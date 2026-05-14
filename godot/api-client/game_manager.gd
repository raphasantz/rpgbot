# game_manager.gd
extends Node2D

@onready var hud = $HUD
@onready var background = $Background
@onready var enemy_container = $EnemyContainer
@onready var player_sprite = $PlayerSprite

var current_telegram_id: String = "123456789" # Vem do ecrã de login
var player_data: Dictionary = {}
var scene_data: Dictionary = {}

func _ready():
	# Conecta os sinais do nosso Client API
	ApiClient.login_success.connect(_on_login_success)
	ApiClient.action_success.connect(_on_action_success)
	ApiClient.api_error.connect(_on_api_error)
	
	# Inicia a sessão
	ApiClient.login(current_telegram_id)

func _on_login_success(p_data: Dictionary, s_data: Dictionary):
	player_data = p_data
	scene_data = s_data
	update_hud()
	load_scene()

func _on_action_success(response: Dictionary):
	player_data = response.jogador
	scene_data = response.cena
	
	update_hud()
	
	# Se houve combate, animamos PRIMEIRO. Depois atualizamos a sala.
	if response.combate != null:
		await animate_combat(response.combate)
	
	if response.vitoria:
		hud.get_node("CombatLog").text += "\n🏆 VITÓRIA!"
		if response.loot.size() > 0:
			hud.get_node("CombatLog").text += "\n🎁 Loot: " + ", ".join(response.loot)
		if response.nivel_subiu:
			hud.get_node("CombatLog").text += "\n🌟 LEVEL UP!"
	
	# Atualiza os inimigos na tela (remove mortos, adiciona novos se moveu de sala)
	load_scene()

func _on_api_error(error_msg: String):
	print("ERRO DE API: ", error_msg)
	hud.get_node("CombatLog").text += "\n[ERRO] " + error_msg

# ==========================================================
# RENDERIZAÇÃO
# ==========================================================

func load_scene():
	# 1. Atualiza Fundo (Placeholder se não tiver URL)
	if scene_data.imagem_url != null:
		# Lógica de download de imagem do DALL-E (requer lógica assíncrona extra)
		pass
	else:
		# background.texture = preload("res://assets/placeholder.png")
		pass
	
	# 2. Limpa inimigos antigos
	for child in enemy_container.get_children():
		child.queue_free()
		
	# 3. Instancia os novos inimigos baseado no JSON do Python
	for enemy in scene_data.inimigos:
		var enemy_scene = preload("res://scenes/enemy_sprite.tscn").instantiate()
		
		# Distribui os inimigos pela tela (Estilo Final Fantasy)
		var index = enemy_container.get_child_count()
		enemy_scene.position = Vector2(400 + index * 150, 200)
		
		enemy_scene.setup(enemy.id_instancia, enemy.nome, enemy.hp_atual, enemy.hp_maximo, enemy.is_boss)
		enemy_scene.enemy_clicked.connect(_on_enemy_clicked)
		
		enemy_container.add_child(enemy_scene)

func update_hud():
	hud.get_node("HPBar").value = (float(player_data.hp_atual) / float(player_data.hp_maximo)) * 100
	hud.get_node("HPLabel").text = "HP: %d/%d" % [player_data.hp_atual, player_data.hp_maximo]
	hud.get_node("GoldLabel").text = "Ouro: %d" % player_data.gold

# ==========================================================
# AÇÕES DO JOGADOR
# ==========================================================

func _on_enemy_clicked(instance_id: String):
	# Desativa botões enquanto a animação rola
	set_process_input(false)
	ApiClient.execute_action(current_telegram_id, "COMBATE", instance_id)

func _on_north_button_pressed():
	ApiClient.execute_action(current_telegram_id, "NAVEGAR", "", "norte")

func _on_south_button_pressed():
	ApiClient.execute_action(current_telegram_id, "NAVEGAR", "", "sul")

# ==========================================================
# ANIMAÇÕES
# ==========================================================

func animate_combat(combat_data: Dictionary) -> void:
	# 1. Jogador Ataca
	player_sprite.play_attack()
	await player_sprite.animation_finished
	
	# 2. Resultado do Ataque no Inimigo
	if combat_data.acertou:
		var target_node = get_enemy_node_by_id(combat_data.id_alvo)
		if target_node:
			target_node.take_damage(combat_data.dano_causado)
			spawn_floating_text(target_node.position, str(combat_data.dano_causado), Color.RED)
			
			if combat_data.critico:
				spawn_floating_text(target_node.position + Vector2(0, -30), "CRÍTICO!", Color.YELLOW)
			
			if combat_data.inimigo_morto:
				await get_tree().create_timer(0.3).timeout
				target_node.die()
	else:
		spawn_floating_text(player_sprite.position, "MISS", Color.GRAY)
	
	# 3. Revide do Inimigo
	if combat_data.revide_acertos > 0:
		await get_tree().create_timer(0.5).timeout
		
		# Animação genérica dos inimigos atacando
		for enemy in enemy_container.get_children():
			enemy.position.x -= 20 # Simula um "pulso" para a frente
			await get_tree().create_timer(0.1).timeout
			enemy.position.x += 20
		
		player_sprite.play_hit()
		spawn_floating_text(player_sprite.position, str(combat_data.revide_dano_total), Color.ORANGE)
		
		# Screen Shake
		$Camera2D.offset = Vector2(randf_range(-5, 5), randf_range(-5, 5))
		await get_tree().create_timer(0.1).timeout
		$Camera2D.offset = Vector2.ZERO

	# Reativa inputs no fim da animação
	set_process_input(true)

# Função auxiliar para encontrar o nó do inimigo pelo ID
func get_enemy_node_by_id(id: String) -> Node:
	for enemy in enemy_container.get_children():
		if enemy.instance_id == id:
			return enemy
	return null

# Sistema de texto flutuante (requer uma cena FloatingText.tscn com Label + script de movimento)
func spawn_floating_text(pos: Vector2, text: String, color: Color):
	var ft = preload("res://scenes/floating_text.tscn").instantiate()
	ft.position = pos
	ft.text = text
	ft.modulate = color
	add_child(ft)
