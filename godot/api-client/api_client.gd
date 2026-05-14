# api_client.gd
extends Node
class_name ApiClient

signal login_success(player_data: Dictionary, scene_data: Dictionary)
signal action_success(response_data: Dictionary)
signal api_error(error_message: String)

# Substitui pelo IP do teu VPS onde o Docker está a rodar
@export var base_url: String = "http://127.0.0.1:8000" 

var http_request: HTTPRequest
var current_callback: String = ""

func _ready():
	http_request = HTTPRequest.new()
	add_child(http_request)
	http_request.request_completed.connect(_on_request_completed)

# ---------------------------------------------------------
# 1. FUNÇÃO DE LOGIN
# ---------------------------------------------------------
func login(telegram_id: String) -> void:
	current_callback = "login"
	var url = base_url + "/api/login"
	var body = JSON.stringify({"codigo_acesso": telegram_id})
	var headers = ["Content-Type: application/json"]
	
	print("Enviando login para: ", url)
	var error = http_request.request(url, headers, HTTPClient.METHOD_POST, body)
	if error != OK:
		emit_signal("api_error", "Falha ao enviar pedido de login.")

# ---------------------------------------------------------
# 2. FUNÇÃO DE PEDIR ESTADO DA CENA
# ---------------------------------------------------------
func get_scene(telegram_id: String) -> void:
	current_callback = "scene"
	var url = base_url + "/api/scene/" + telegram_id
	var headers = ["Content-Type: application/json"]
	
	var error = http_request.request(url, headers, HTTPClient.METHOD_GET)
	if error != OK:
		emit_signal("api_error", "Falha ao buscar dados da cena.")

# ---------------------------------------------------------
# 3. FUNÇÃO DE EXECUTAR AÇÃO (Mover, Atacar, Interagir)
# ---------------------------------------------------------
func execute_action(telegram_id: String, intention: String, direction: String = "", target_id: int = 0) -> void:
	current_callback = "action"
	var url = base_url + "/api/action/" + telegram_id
	var body_dict = {
		"intencao": intention,
		"direcao": direction,
		"target_id": target_id
	}
	var body = JSON.stringify(body_dict)
	var headers = ["Content-Type: application/json"]
	
	print("Executando ação: ", intention)
	var error = http_request.request(url, headers, HTTPClient.METHOD_POST, body)
	if error != OK:
		emit_signal("api_error", "Falha ao enviar ação.")

# ---------------------------------------------------------
# CALLBACK DE RESPOSTA (O cérebro que lê o teu JSON)
# ---------------------------------------------------------
func _on_request_completed(result, code, headers, body):
	if result != HTTPRequest.RESULT_SUCCESS:
		emit_signal("api_error", "Erro de conexão com o servidor.")
		return
		
	var json = JSON.new()
	var error = json.parse(body.get_string_from_utf8())
	if error != OK:
		emit_signal("api_error", "Erro ao ler JSON do servidor.")
		return
		
	var data = json.data
	
	if code >= 400:
		var detail = data.get("detail", "Erro desconhecido no servidor.")
		emit_signal("api_error", detail)
		return

	# Roteamento baseado na callback que pedimos
	match current_callback:
		"login":
			emit_signal("login_success", data.jogador, data.cena)
		"scene":
			# O Godot vai usar isto para redesenhar a tela
			emit_signal("action_success", data) # Reaproveitamos o sinal para atualizar a UI
		"action":
			emit_signal("action_success", data)

	current_callback = "" # Limpa a callback
