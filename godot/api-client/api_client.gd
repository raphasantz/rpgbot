# api_client.gd
extends Node

signal login_success(player_data: Dictionary, scene_data: Dictionary)
signal action_success(response_data: Dictionary)
signal api_error(error_message: String)

@export var base_url: String = "http://127.0.0.1:8000" # Muda para o IP do teu VPS

var http_request: HTTPRequest
var current_callback: String = ""

func _ready():
	http_request = HTTPRequest.new()
	add_child(http_request)
	http_request.request_completed.connect(_on_request_completed)

func login(telegram_id: String) -> void:
	current_callback = "login"
	var url = base_url + "/api/login"
	var body = JSON.stringify({"codigo_acesso": telegram_id})
	var headers = ["Content-Type: application/json"]
	
	var error = http_request.request(url, headers, HTTPClient.METHOD_POST, body)
	if error != OK:
		emit_signal("api_error", "Falha ao enviar pedido de login.")

func get_scene(telegram_id: String) -> void:
	current_callback = "scene"
	var url = base_url + "/api/scene/" + telegram_id
	var headers = ["Content-Type: application/json"]
	
	var error = http_request.request(url, headers, HTTPClient.METHOD_GET)
	if error != OK:
		emit_signal("api_error", "Falha ao buscar dados da cena.")

func execute_action(telegram_id: String, intention: String, target_id: String = "", direction: String = "") -> void:
	current_callback = "action"
	var url = base_url + "/api/action/" + telegram_id
	var body_dict = {
		"intencao": intention,
		"direcao": direction,
		"target_id": target_id
	}
	var body = JSON.stringify(body_dict)
	var headers = ["Content-Type: application/json"]
	
	var error = http_request.request(url, headers, HTTPClient.METHOD_POST, body)
	if error != OK:
		emit_signal("api_error", "Falha ao enviar ação.")

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

	match current_callback:
		"login":
			emit_signal("login_success", data.jogador, data.cena)
		"scene", "action":
			emit_signal("action_success", data)

	current_callback = ""
