# enemy_sprite.gd
extends Area2D

signal enemy_clicked(instance_id: String)

@onready var sprite = $Sprite2D
@onready var hp_bar = $HPBar

var instance_id: String = ""
var enemy_name: String = ""
var hp: int = 0
var max_hp: int = 0
var is_boss: bool = false

func setup(id: String, nome: String, current_hp: int, maximum_hp: int, boss: bool):
	instance_id = id
	enemy_name = nome
	hp = current_hp
	max_hp = maximum_hp
	is_boss = boss
	
	# Atualiza a UI inicial
	$HPBar.max_value = max_hp
	$HPBar.value = hp
	# Aqui podias carregar a textura baseada no nome, se tiveres os assets localmente
	# sprite.texture = load("res://assets/enemies/" + nome.to_snake_case() + ".png")

func take_damage(damage: int):
	hp = max(0, hp - damage)
	$HPBar.value = hp
	
	# Animação de dano (Flash Branco)
	var tween = create_tween()
	tween.tween_property(sprite, "modulate", Color.RED, 0.1)
	tween.tween_property(sprite, "modulate", Color.WHITE, 0.2)

func die():
	# Animação de Morte
	var tween = create_tween()
	tween.tween_property(self, "modulate", Color.TRANSPARENT, 0.5)
	tween.tween_callback(queue_free)

func _on_input_event(_viewport, event, _shape_idx):
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		emit_signal("enemy_clicked", instance_id)
