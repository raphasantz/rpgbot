# floating_text.gd
extends Label

var lifetime: float = 1.0
var velocity: Vector2 = Vector2(0, -50)

func _ready():
	# Auto-destrói-se depois de um tempo
	var tween = create_tween()
	tween.tween_property(self, "modulate:a", 0, lifetime)
	tween.tween_callback(queue_free)

func _process(delta):
	position += velocity * delta
