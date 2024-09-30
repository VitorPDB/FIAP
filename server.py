from flask import Flask, render_template, jsonify, request, redirect, url_for
import requests
import math

app = Flask(__name__)

# URL do Firebase
firebase_url = "https://challenge-36ea0.firebaseio.com/sensor_data.json"
SCALE_PIXELS_TO_METERS = 10


# Mapeamento de IDs de kits para seus nomes
kit_ids = {
    1: 'kit_a_1',
    2: 'kit_b_1',
    3: 'kit_c_1',
    4: 'kit_a_2',
    5: 'kit_a_3',
    6: 'kit_b_2',
    7: 'kit_b_3',
    8: 'kit_c_2',
    9: 'kit_c_3',
}

# Dados dos kits-carros
kit_carros = [
    {"id": 1, "sensor_id": "kit_a_1", "status": "reabastecimento", "last_status": "reabastecimento", "x": 20, "y": 50,
     "reabastecimento_x": 2, "reabastecimento_y": 5, "producao_x": 22, "producao_y": 12},
    {"id": 2, "sensor_id": "kit_b_1", "status": "produção", "last_status": "produção", "x": 35, "y": 65,
     "reabastecimento_x": 2, "reabastecimento_y": 16, "producao_x": 36, "producao_y": 15},
    {"id": 3, "sensor_id": "kit_c_1", "status": "reabastecimento", "last_status": "reabastecimento", "x": 50, "y": 80,
     "reabastecimento_x": 2, "reabastecimento_y": 28, "producao_x": 50, "producao_y": 25},
    {"id": 4, "sensor_id": "kit_a_2", "status": "reabastecimento", "last_status": "reabastecimento", "x": 25, "y": 55,
     "reabastecimento_x": 2, "reabastecimento_y": 5, "producao_x": 25, "producao_y": 18},
    {"id": 5, "sensor_id": "kit_a_3", "status": "produção", "last_status": "produção", "x": 30, "y": 60,
     "reabastecimento_x": 2, "reabastecimento_y": 5, "producao_x": 28, "producao_y": 20},
    {"id": 6, "sensor_id": "kit_b_2", "status": "produção", "last_status": "produção", "x": 40, "y": 70,
     "reabastecimento_x": 2, "reabastecimento_y": 16, "producao_x": 36, "producao_y": 20},
    {"id": 7, "sensor_id": "kit_b_3", "status": "reabastecimento", "last_status": "reabastecimento", "x": 45, "y": 75,
     "reabastecimento_x": 2, "reabastecimento_y": 16, "producao_x": 40, "producao_y": 25},
    {"id": 8, "sensor_id": "kit_c_2", "status": "reabastecimento", "last_status": "reabastecimento", "x": 50, "y": 85,
     "reabastecimento_x": 2, "reabastecimento_y": 28, "producao_x": 53, "producao_y": 28},
    {"id": 9, "sensor_id": "kit_c_3", "status": "produção", "last_status": "produção", "x": 55, "y": 90,
     "reabastecimento_x": 2, "reabastecimento_y": 28, "producao_x": 55, "producao_y": 30}
]

# Dados dos rebocadores
rebocadores = [
    {
        "id": 1,
        "sensor_id": "esp32",
        "x": 10,
        "y": 15,
        "kits_assigned": [],
        "status": "livre",
        "notifications": [],
        "processedNotifications": [],
        "rebocados": [],
        "emCurso": [],
        "kits_para_rebocar": [],
        "ultimoKitDeixado": None
    },
    {
        "id": 2,
        "sensor_id": "rebocador2",
        "x": 10,
        "y": 10,
        "kits_assigned": [],
        "status": "livre",
        "notifications": [],
        "processedNotifications": [],
        "rebocados": [],
        "emCurso": [],
        "kits_para_rebocar": [],
        "ultimoKitDeixado": None
    }
]

deliveries = []

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/montadores_a')
def montadores_a():
    return render_template('montadores_a.html')

@app.route('/montadores_b')
def montadores_b():
    return render_template('montadores_b.html')

@app.route('/montadores_c')
def montadores_c():
    return render_template('montadores_c.html')

@app.route('/rebocador1')
def rebocador1_page():
    return render_template('rebocador1.html', rebocadores=rebocadores)

@app.route('/rebocador2')
def rebocador2_page():
    return render_template('rebocador2.html', rebocadores=rebocadores)

# Função para adicionar um kit à lista de rebocados e em curso no backend
def add_kit_to_rebocados(rebocador, kit_id):
    if kit_id not in rebocador["rebocados"]:
        rebocador["rebocados"].append(kit_id)
    if kit_id not in rebocador["emCurso"]:
        rebocador["emCurso"].append(kit_id)

# Função para remover um kit das listas
def remove_kit_from_rebocados(rebocador, kit_id):
    rebocador["rebocados"] = [k for k in rebocador["rebocados"] if k != kit_id]
    rebocador["emCurso"] = [k for k in rebocador["emCurso"] if k != kit_id]


# Rota para atualizar o status dos kit-carros (Montadores)
@app.route('/update_kit_status', methods=['POST'])
def update_kit_status():
    data = request.json
    kit_ids_list = data.get('kit_ids')
    new_status = data.get('status')
    
    if not kit_ids_list or len(kit_ids_list) == 0:
        return jsonify({"error": "Nenhum kit foi selecionado"}), 400

    if not new_status:
        return jsonify({"error": "Novo status não foi fornecido"}), 400    
    
    for kit_id in kit_ids_list:
        found = False
        for kit in kit_carros:
            if kit['id'] == kit_id:
                kit['status'] = new_status
                if new_status in ['reabastecimento', 'produção']:
                    kit['last_status'] = new_status
                    if new_status == 'reabastecimento':
                        assign_rebocador_to_kit(kit)  # Aqui notifica o rebocador
                found = True
                break
        if not found:
            return jsonify({"error": f"Kit-Carro com id {kit_id} não encontrado"}), 404

    return jsonify({"success": True})

def assign_rebocador_to_kit(kit):
    # Encontrar o rebocador mais próximo
    rebocador_mais_proximo = find_nearest_rebocador(kit)

    if rebocador_mais_proximo:
        # Adicionar o kit ao rebocador mais próximo
        if kit['id'] not in rebocador_mais_proximo['rebocados']:
            add_kit_to_rebocados(rebocador_mais_proximo, kit['id'])
            rebocador_mais_proximo['status'] = 'ocupado'
            kit['status'] = 'rebocador_a_caminho'
            
            # Notificar apenas o rebocador mais próximo
            notification = f"O kit {kit['sensor_id']} precisa ser rebocado Por você {rebocador_mais_proximo['id']}."
            if notification not in rebocador_mais_proximo['notifications']:
                rebocador_mais_proximo['notifications'].append(notification)
                print(rebocador_mais_proximo)
                

            # Remover notificações de todos os outros rebocadores
            for rebocador in rebocadores:
                if rebocador['id'] != rebocador_mais_proximo['id'] and notification in rebocador['notifications']:
                    rebocador['notifications'].remove(notification)
        
        return True  # Retorna True para indicar que um rebocador foi atribuído
    return False  # Retorna False se nenhum rebocador disponível foi encontrado


def find_nearest_rebocador(kit):
    menor_distancia = float('inf')
    rebocador_mais_proximo = None
    
    for rebocador in rebocadores:
        if rebocador['status'] == 'livre':
            distancia = calcular_distancia(kit['x'], kit['y'], rebocador['x'], rebocador['y'])
            print(f"Distância entre {rebocador['sensor_id']} e o kit {kit['sensor_id']}: {distancia} metros")
            if distancia < menor_distancia:
                menor_distancia = distancia
                rebocador_mais_proximo = rebocador

    return rebocador_mais_proximo


def calcular_distancia(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

@app.route('/get_positions', methods=['GET'])
def get_positions():
    response = requests.get(firebase_url)
    data = response.json()

    # Dicionário para armazenar as últimas posições dos kits
    kits_positions = {}

    if data:
        for entry in data.values():
            sensor_id = entry.get('sensor_id')
            timestamp = int(entry.get('timestamp', 0))
            x_position = entry.get('x_position')
            y_position = entry.get('y_position')

            # Atualiza a posição dos rebocadores
            for rebocador in rebocadores:
                if rebocador['sensor_id'] == sensor_id and timestamp > rebocador.get('timestamp', -1):
                    rebocador['x'] = x_position
                    rebocador['y'] = y_position
                    rebocador['timestamp'] = timestamp
                    print('REBOCADOR LALALALALALALALA', rebocador)
                    

            # Atualiza a posição dos kits
            if sensor_id not in ['esp32', 'rebocador2']:  # Exclui IDs de rebocadores
                if sensor_id in kits_positions:
                    if timestamp > kits_positions[sensor_id]['timestamp']:
                        kits_positions[sensor_id] = {'x': x_position, 'y': y_position, 'timestamp': timestamp}
                else:
                    kits_positions[sensor_id] = {'x': x_position, 'y': y_position, 'timestamp': timestamp}

    # Prepara as posições dos kits
    kits = []
    for kit in kit_carros:
        sensor_id = kit['sensor_id']
        kit_x_meters = None
        kit_y_meters = None
        if kit['status'] == 'em_curso':
            # Se o kit está em curso, sua posição é a do rebocador correspondente
            for rebocador in rebocadores:
                print(rebocador)
                if kit['id'] in rebocador['rebocados']:
                    kit_x_meters = rebocador['x']
                    kit_y_meters = rebocador['y']
                    break
        else:
            # Busca a posição mais recente do kit no Firebase
            kit_data = kits_positions.get(sensor_id)
            if kit_data:
                kit_x_meters = kit_data['x']
                kit_y_meters = kit_data['y']
            else:
                # Se não houver dados no Firebase, usa a posição estática
                kit_x_meters = kit['x'] / SCALE_PIXELS_TO_METERS
                kit_y_meters = kit['y'] / SCALE_PIXELS_TO_METERS

        kits.append({
            "id": kit['id'],
            "sensor_id": sensor_id,
            "status": kit['status'],
            "x": kit_x_meters,
            "y": kit_y_meters
        })

    return jsonify({
        "rebocadores": rebocadores,
        "kits": kits
    })

def get_positions_for_rebocador(rebocador_id):
    # Faz a requisição ao Firebase ou outra fonte de dados
    response = requests.get(firebase_url)
    data = response.json()

    # Variáveis para armazenar as posições do rebocador e kits
    x_rebocador = None
    y_rebocador = None
    rebocador_timestamp = -1
    kits_positions = {}

    if data:
        for entry in data.values():
            sensor_id = entry.get('sensor_id')
            timestamp = int(entry.get('timestamp', 0))
            x_position = entry.get('x_position')
            y_position = entry.get('y_position')

            # Verifica se o sensor_id corresponde ao rebocador especificado
            if sensor_id == f'rebocador_{rebocador_id}' and timestamp > rebocador_timestamp:
                x_rebocador = x_position
                y_rebocador = y_position
                rebocador_timestamp = timestamp
                print('REBOCADOR mmmmmmmmmmmmmmmmmmm', x_rebocador, y_rebocador)
            # Trata os kits da mesma maneira
            elif "kit" in sensor_id:
                if sensor_id in kits_positions:
                    if timestamp > kits_positions[sensor_id]['timestamp']:
                        kits_positions[sensor_id] = {'x': x_position, 'y': y_position, 'timestamp': timestamp}
                else:
                    kits_positions[sensor_id] = {'x': x_position, 'y': y_position, 'timestamp': timestamp}

    # Retorna as posições do rebocador e dos kits
    return {
        "rebocador": {"x": x_rebocador, "y": y_rebocador},
        "kits": kits_positions
    }

@app.route('/get_distances', methods=['GET'])
def get_distances():
    # Reutiliza a lógica de get_positions para obter as posições
    positions_data = get_positions().get_json()
    rebocador = next((r for r in positions_data['rebocadores'] if r['id'] == rebocador_id), None)
    if rebocador:
        x_rebocador = rebocador['x']
        y_rebocador = rebocador['y']
    else:
        x_rebocador = None
        y_rebocador = None
        kits = positions_data['kits']

    distances = []

    for kit in kits:
        if kit['status'] == 'em_curso':
            distance = 0.0
        else:
            distance = calcular_distancia(kit['x'], kit['y'], x_rebocador, y_rebocador)

        distances.append({
            "kit_id": kit['id'],
            "distance": distance
        })

    return jsonify({"distances": distances})

@app.route('/deliver_kit', methods=['POST'])
def deliver_kit():
    data = request.json
    kit_id = data.get('kit_id')

    # Atualiza o status do kit para 'entrega_pendente'
    for kit in kit_carros:
        if kit['id'] == kit_id:
            kit['status'] = 'entrega_pendente'
            break

    # Adiciona a entrega à lista de entregas pendentes
    deliveries.append({
        'kit_id': kit_id,
        'sensor_id': kit['sensor_id'],
        'classe': kit['sensor_id'].split('_')[1]  # Extrai a classe do sensor_id
    })

    return jsonify({'success': True})

@app.route('/get_kits', methods=['GET'])
def get_kits():
    classe = request.args.get('classe')

    response = requests.get(firebase_url)
    data = response.json()

    positions = {}
    if data:
        for entry in data.values():
            sensor_id = entry.get('sensor_id')
            timestamp = int(entry.get('timestamp', 0))
            x_position = entry.get('x_position')
            y_position = entry.get('y_position')

            if sensor_id:
                if sensor_id not in positions or positions[sensor_id]['timestamp'] < timestamp:
                    positions[sensor_id] = {
                        'timestamp': timestamp,
                        'x_position': x_position,
                        'y_position': y_position
                    }

    kits = []
    for kit in kit_carros:
        if classe == 'a' and 'kit_a' in kit['sensor_id']:
            sensor_id = kit['sensor_id']
            position = positions.get(sensor_id, {'x_position': None, 'y_position': None})
            kits.append({
                'id': kit['id'],
                'sensor_id': sensor_id,
                'status': kit['status'],
                'x_position': position['x_position'],
                'y_position': position['y_position']
            })
        elif classe == 'b' and 'kit_b' in kit['sensor_id']:
            sensor_id = kit['sensor_id']
            position = positions.get(sensor_id, {'x_position': None, 'y_position': None})
            kits.append({
                'id': kit['id'],
                'sensor_id': sensor_id,
                'status': kit['status'],
                'x_position': position['x_position'],
                'y_position': position['y_position']
            })
        elif classe == 'c' and 'kit_c' in kit['sensor_id']:
            sensor_id = kit['sensor_id']
            position = positions.get(sensor_id, {'x_position': None, 'y_position': None})
            kits.append({
                'id': kit['id'],
                'sensor_id': sensor_id,
                'status': kit['status'],
                'x_position': position['x_position'],
                'y_position': position['y_position']
            })

    return jsonify(kits)

@app.route('/get_deliveries', methods=['GET'])
def get_deliveries():
    classe = request.args.get('classe')
    relevant_deliveries = []
    for delivery in deliveries:
        if delivery['classe'] == classe:
            relevant_deliveries.append(delivery)
    return jsonify({'deliveries': relevant_deliveries})

@app.route('/confirm_delivery', methods=['POST'])
def confirm_delivery():
    data = request.json
    kit_id = data.get('kit_id')

    # Atualiza o status do kit para 'produção' ou 'reabastecimento'
    for kit in kit_carros:
        if kit['id'] == kit_id:
            kit['status'] = 'produção'
            kit['last_status'] = 'produção'
            break

    # Remove a entrega pendente
    global deliveries
    deliveries = [d for d in deliveries if d['kit_id'] != kit_id]

    # Remova o kit da lista de kits em curso do rebocador
    for rebocador in rebocadores:
        if kit_id in rebocador['rebocados']:
            rebocador['rebocados'].remove(kit_id)
            rebocador['emCurso'].remove(kit_id)
            # Verifica se o rebocador tem mais kits para rebocar
            rebocador['status'] = 'livre' if len(rebocador['rebocados']) == 0 else 'ocupado'
    print(rebocadores)
    return jsonify({'success': True})

@app.route('/decline_delivery', methods=['POST'])
def decline_delivery():
    data = request.json
    kit_id = data.get('kit_id')

    # Notifica o rebocador que o kit foi deixado no lugar errado
    if kit_id in kit_ids:
        notification = f"O kit-carro {kit_ids[kit_id]} foi deixado no lugar errado."
    else:
        notification = f"Kit ID {kit_id} não encontrado"
    # Adiciona a notificação ao rebocador se ela ainda não estiver presente

    # Atualiza o status do kit de volta para 'em_curso'
    for kit in kit_carros:
        if kit['id'] == kit_id:
            kit['status'] = 'em_curso'  # Volta para 'em_curso' para tentar a entrega novamente
            break

    # Remove a entrega pendente
    global deliveries
    deliveries = [d for d in deliveries if d['kit_id'] != kit_id]

    return jsonify({'success': True})

@app.route('/request_kits', methods=['POST'])
def request_kits():
    data = request.json
    kit_ids_list = data.get('kit_ids')

    for kit_id in kit_ids_list:
        found = False
        for kit in kit_carros:
            if kit['id'] == kit_id and kit['status'] == 'produção':
                kit['status'] = 'reabastecimento'
                kit['last_status'] = 'reabastecimento'

                # Encontrar o rebocador mais próximo para adicionar o kit à sua lista
                closest_rebocador = find_nearest_rebocador(kit)

                if closest_rebocador:
                    # Adicionar o kit à lista de kits_para_rebocar do rebocador
                    if kit_id not in closest_rebocador['kits_para_rebocar']:
                        closest_rebocador['kits_para_rebocar'].append(kit_id)
                        assign_rebocador_to_kit(kit)  # Enviar notificação ao rebocador mais próximo
                    else:
                        print(f"Kit {kit_id} já está na lista de {closest_rebocador['sensor_id']}")
                else:
                    print("Nenhum rebocador encontrado")

                found = True
                break

        if not found:
            return jsonify({"error": f"Kit-Carro com id {kit_id} não encontrado ou não está disponível."}), 404

    return jsonify({"success": True})


@app.route('/get_kits_para_rebocar')
def get_kits_para_rebocar():
    rebocador_id = request.args.get('rebocador_id')
    
    if rebocador_id is None:
        return jsonify({"error": "rebocador_id is required"}), 400

    # Agora usamos a função find_rebocador_by_id para localizar o rebocador
    rebocador = find_rebocador_by_id(rebocador_id)
    
    if rebocador is None:
        return jsonify({"error": "Rebocador not found"}), 404

    # Retorna a lista de kits para rebocar deste rebocador
    kits_para_rebocar = rebocador.get("kits_para_rebocar", [])
    return jsonify({"kits": kits_para_rebocar}), 200

def find_rebocador_by_id(rebocador_id):
    for rebocador in rebocadores:
        if rebocador["id"] == int(rebocador_id):
            # Certifica-se de que a chave 'kits_para_rebocar' está presente
            if "kits_para_rebocar" not in rebocador:
                rebocador["kits_para_rebocar"] = []  # Inicializa a lista se ela não existe
            return rebocador
    return None

@app.route('/update_kits_para_rebocar', methods=['POST'])
def update_kits_para_rebocar():
    data = request.json
    rebocador_id = data.get('rebocador_id')
    kits_para_rebocar = data.get('kits', [])

    rebocador = find_rebocador_by_id(rebocador_id)

    if rebocador:
        # Atualiza a lista de kits para rebocar do rebocador específico
        rebocador['kits_para_rebocar'] = kits_para_rebocar
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Rebocador não encontrado"}), 404

@app.route('/confirm_rebocador_notification', methods=['POST'])
def confirm_rebocador_notification():
    data = request.json
    rebocador_id = data.get('rebocador_id', None)
    notification = data.get('notification', None)

    if rebocador_id is None or notification is None:
        return jsonify({"error": "rebocador_id ou notification não fornecido"}), 400

    try:
        rebocador_id = int(rebocador_id)
    except ValueError:
        return jsonify({"error": "rebocador_id inválido"}), 400

    for rebocador in rebocadores:
        if rebocador['id'] == rebocador_id:
            if notification in rebocador['notifications']:
                rebocador['notifications'].remove(notification)
                
                if "deixado no lugar errado" in notification:
                    kitId = extractKitIdFromNotification(notification)
                    rebocador['ultimoKitDeixado'] = kitId
                
                return jsonify({"success": True})

    return jsonify({"error": "Notificação não encontrada"}), 404

@app.route('/get_rebocador_data', methods=['GET'])
def get_rebocador_data():
    rebocador_id = int(request.args.get('rebocador_id'))
    
    for rebocador in rebocadores:
        if rebocador['id'] == rebocador_id:
            return jsonify({
                'success': True,
                'rebocados': rebocador.get('rebocados', []),  # Garante que seja uma lista
                'emCurso': rebocador.get('emCurso', [])       # Garante que seja uma lista
            })
    
    return jsonify({"success": False, "error": "Rebocador não encontrado"}), 404


@app.route('/get_rebocador_notifications', methods=['GET'])
def get_rebocador_notifications():
    rebocador_id = request.args.get('rebocador_id', None)
    if rebocador_id is not None:
        try:
            rebocador_id = int(rebocador_id)
        except ValueError:
            return jsonify({"error": "rebocador_id inválido"}), 400
    else:
        return jsonify({"error": "rebocador_id não fornecido"}), 400

    for rebocador in rebocadores:
        if rebocador['id'] == rebocador_id:
            notifications = rebocador.get('notifications', [])
            return jsonify({"notifications": notifications})
    return jsonify({"notifications": []})

if __name__ == '__main__':
    app.run(debug=True)
