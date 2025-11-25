from flask import Blueprint, jsonify, request
from database.conector import DatabaseManager

carros_blueprint = Blueprint("carros", __name__)

# ============================================================
# Helpers
# ============================================================


def bad_request(msg, fields=None):
    resp = {"erro": msg}
    if fields:
        resp["faltando"] = fields
    return jsonify(resp), 400


def internal_error(msg="Erro interno no servidor"):
    return jsonify({"erro": msg}), 500


def validate_fields(data, required):
    missing = [f for f in required if f not in data or data[f] in (None, "")]
    return missing

# ============================================================
# 1. Listar todos os carros
# ============================================================


@carros_blueprint.route("/carros", methods=["GET"])
def listar_carros():
    db = DatabaseManager()
    try:
        query = """
            SELECT
                max(c.placa) as placa,
                c.nome, 
                c.tipo_categoria, 
                c.imagem_url AS imagem,
                cat.preco_diaria AS preco,
                cat.descricao
            FROM Carro c
            JOIN Categoria cat ON cat.tipo = c.tipo_categoria
            GROUP BY c.nome,c.tipo_categoria,c.imagem_url,cat.preco_diaria,cat.descricao
            ORDER BY c.nome;
        """
        carros = db.execute_select_all(query)
        return jsonify({"carros": carros}), 200
    except Exception as e:
        print(f"Erro: {e}")
        return internal_error()

# ============================================================
# 2. Obter carro por placa
# ============================================================


@carros_blueprint.route("/carros/<placa>", methods=["GET"])
def obter_carro(placa):
    db = DatabaseManager()
    try:
        query = """
            SELECT 
                c.placa, 
                c.nome, 
                c.ano,
                c.quilometragem,
                c.chassi,
                c.tipo_categoria, 
                c.imagem_url AS imagem,
                c.status_carro,
                cat.descricao,
                cat.preco_diaria AS preco
            FROM Carro c
            JOIN Categoria cat ON cat.tipo = c.tipo_categoria
            WHERE c.placa = %s;
        """
        carro = db.execute_select_one(query, (placa,))

        if not carro:
            return jsonify({"erro": "Carro não encontrado"}), 404

        return jsonify(carro), 200
    except Exception:
        return internal_error()

# ============================================================
# 3. Listar Placas Disponíveis por Modelo (Para o Select de Aluguel)
# ============================================================


@carros_blueprint.route("/carros/placas/<nome_modelo>", methods=["GET"])
def listar_placas_por_modelo(nome_modelo):
    db = DatabaseManager()
    try:
        query = """
            SELECT placa 
            FROM Carro 
            WHERE nome ILIKE %s AND status_carro = 'DISPONIVEL';
        """
        placas = db.execute_select_all(query, (f"%{nome_modelo}%",))
        return jsonify({"placas": [p["placa"] for p in placas]}), 200
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"erro": "Erro ao buscar placas"}), 500

# ============================================================
# 4. Criar carro
# ============================================================


@carros_blueprint.route("/carros", methods=["POST"])
def criar_carro():
    data = request.json or {}

    # Campos obrigatórios conforme novo banco
    required = ["placa", "nome", "chassi", "ano", "tipo_categoria"]
    missing = validate_fields(data, required)

    if missing:
        return jsonify({"erro": "Campos faltando", "campos": missing}), 400

    db = DatabaseManager()
    try:
        # Verificar se placa já existe
        carro_existente = db.execute_select_one(
            "SELECT placa FROM Carro WHERE placa = %s",
            (data["placa"],)
        )
        if carro_existente:
            return jsonify({"erro": "Placa já cadastrada"}), 400

        # Verificar se chassi já existe
        chassi_existente = db.execute_select_one(
            "SELECT chassi FROM Carro WHERE chassi = %s",
            (data["chassi"],)
        )
        if chassi_existente:
            return jsonify({"erro": "Chassi já cadastrado"}), 400

        query = """
            INSERT INTO Carro (placa, nome, chassi, ano, tipo_categoria, imagem_url, status_carro, quilometragem)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        db.execute_statement(
            query,
            (
                data["placa"],
                data["nome"],
                data["chassi"],
                data["ano"],
                data["tipo_categoria"],
                data.get("imagem_url", "placeholder.png"),
                data.get("status_carro", "DISPONIVEL"),
                data.get("quilometragem", 0)
            ),
        )

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({"mensagem": "Carro cadastrado com sucesso!"}), 201
    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        print(f"Erro: {e}")
        return internal_error()

# ============================================================
# 5. Atualizar carro
# ============================================================


@carros_blueprint.route("/carros/<placa>", methods=["PUT"])
def atualizar_carro(placa):
    data = request.json or {}

    db = DatabaseManager()
    try:
        # Verificar se carro existe
        carro_existente = db.execute_select_one(
            "SELECT placa FROM Carro WHERE placa = %s",
            (placa,)
        )
        if not carro_existente:
            return jsonify({"erro": "Carro não encontrado"}), 404

        query = """
            UPDATE Carro
            SET nome = COALESCE(%s, nome),
                ano = COALESCE(%s, ano),
                quilometragem = COALESCE(%s, quilometragem),
                tipo_categoria = COALESCE(%s, tipo_categoria),
                imagem_url = COALESCE(%s, imagem_url),
                status_carro = COALESCE(%s, status_carro)
            WHERE placa = %s;
        """
        db.execute_statement(
            query,
            (
                data.get("nome"),
                data.get("ano"),
                data.get("quilometragem"),
                data.get("tipo_categoria"),
                data.get("imagem_url"),
                data.get("status_carro"),
                placa,
            ),
        )

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({"mensagem": "Carro atualizado com sucesso!"}), 200
    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        print("ERRO:", e)
        return internal_error()

# ============================================================
# 6. Remover carro
# ============================================================


@carros_blueprint.route("/carros/<placa>", methods=["DELETE"])
def deletar_carro(placa):
    db = DatabaseManager()
    try:
        # Verificar se carro existe
        carro = db.execute_select_one(
            "SELECT placa, status_carro FROM Carro WHERE placa = %s",
            (placa,)
        )
        if not carro:
            return jsonify({"erro": "Carro não encontrado"}), 404

        # Verificar se carro está alugado
        if carro["status_carro"] == "ALUGADO":
            return jsonify({"erro": "Não é possível remover carro alugado"}), 400

        # Verificar se existe aluguel ativo para este carro
        aluguel_ativo = db.execute_select_one("""
            SELECT 1 FROM Aluguel a 
            WHERE a.placa = %s 
            AND NOT EXISTS (
                SELECT 1 FROM Devolucao d WHERE d.num_locacao = a.num_locacao
            )
        """, (placa,))

        if aluguel_ativo:
            return jsonify({"erro": "Carro possui aluguel em andamento"}), 400

        query = "DELETE FROM Carro WHERE placa = %s;"
        success = db.execute_statement(query, (placa,))

        if not success:
            return jsonify({"erro": "Não foi possível remover o carro"}), 400

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({"mensagem": "Carro removido com sucesso!"}), 200
    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return internal_error(str(e))

# ============================================================
# 7. Listar categorias
# ============================================================


@carros_blueprint.route("/categorias", methods=["GET"])
def listar_categorias():
    db = DatabaseManager()
    try:
        query = "SELECT tipo, preco_diaria AS preco, descricao FROM Categoria ORDER BY tipo;"
        categorias = db.execute_select_all(query)
        return jsonify({"categorias": categorias}), 200
    except Exception as e:
        return internal_error(str(e))

# ============================================================
# 8. Carros disponíveis - CORRIGIDO
# ============================================================


@carros_blueprint.route("/carros/disponiveis", methods=["GET"])
def carros_disponiveis():
    db = DatabaseManager()
    try:
        query = """
            SELECT DISTINCT
                c.placa as placa, 
                c.nome, 
                c.tipo_categoria, 
                c.imagem_url AS imagem,
                c.status_carro,
                cat.preco_diaria AS preco,
                cat.descricao AS descricao_categoria,
                c.ano,
                c.quilometragem
            FROM Carro c
            JOIN Categoria cat ON cat.tipo = c.tipo_categoria
            inner join (select max(placa) as placa, nome from Carro where status_carro = 'DISPONIVEL' group by nome) c2
                on c2.placa = c.placa
            WHERE c.status_carro = 'DISPONIVEL'
            ORDER BY c.nome;
        """
        carros = db.execute_select_all(query)
        return jsonify({"carros": carros}), 200
    except Exception as e:
        print(f"Erro: {e}")
        return internal_error()

# ============================================================
# 9. Carros em manutenção - CORRIGIDO
# ============================================================


@carros_blueprint.route("/carros/manutencao", methods=["GET"])
def carros_em_manutencao():
    db = DatabaseManager()
    try:
        query = """
            SELECT 
                c.placa,
                c.nome,
                c.tipo_categoria,
                c.imagem_url AS imagem,
                m.num_manutencao,
                m.custo,
                m.data_inicio,
                m.descricao,
                cat.preco_diaria AS preco
            FROM Carro c
            JOIN Manutencao m ON c.placa = m.placa_carro
            JOIN Categoria cat ON c.tipo_categoria = cat.tipo
            WHERE m.data_retorno IS NULL
            ORDER BY m.data_inicio DESC;
        """
        dados = db.execute_select_all(query)
        return jsonify({"carros_manutencao": dados}), 200
    except Exception as e:
        print(f"Erro: {e}")
        return internal_error()

# ============================================================
# 10. Atualizar status do carro
# ============================================================


@carros_blueprint.route("/carros/<placa>/status", methods=["PUT"])
def atualizar_status_carro(placa):
    data = request.json or {}

    if "status_carro" not in data:
        return jsonify({"erro": "Campo 'status_carro' é obrigatório"}), 400

    status = data["status_carro"]
    status_validos = ['DISPONIVEL', 'ALUGADO', 'MANUTENCAO']

    if status not in status_validos:
        return jsonify({"erro": f"Status inválido. Deve ser: {', '.join(status_validos)}"}), 400

    db = DatabaseManager()
    try:
        # Verificar se carro existe
        carro = db.execute_select_one(
            "SELECT placa FROM Carro WHERE placa = %s",
            (placa,)
        )
        if not carro:
            return jsonify({"erro": "Carro não encontrado"}), 404

        query = "UPDATE Carro SET status_carro = %s WHERE placa = %s;"
        db.execute_statement(query, (status, placa))

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({"mensagem": "Status atualizado com sucesso!"}), 200
    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return internal_error(str(e))

# ============================================================
# 11. Buscar carros por categoria
# ============================================================


@carros_blueprint.route("/carros/categoria/<categoria>", methods=["GET"])
def carros_por_categoria(categoria):
    db = DatabaseManager()
    try:
        query = """
            SELECT 
                c.placa, 
                c.nome, 
                c.tipo_categoria, 
                c.imagem_url AS imagem,
                c.status_carro,
                cat.preco_diaria AS preco,
                cat.descricao AS descricao_categoria
            FROM Carro c
            JOIN Categoria cat ON cat.tipo = c.tipo_categoria
            WHERE c.tipo_categoria = %s
            ORDER BY c.nome;
        """
        carros = db.execute_select_all(query, (categoria,))
        return jsonify({"carros": carros}), 200
    except Exception as e:
        print(f"Erro: {e}")
        return internal_error()

# ============================================================
# 12. Estatísticas dos carros
# ============================================================


@carros_blueprint.route("/carros/estatisticas", methods=["GET"])
def estatisticas_carros():
    db = DatabaseManager()
    try:
        query = """
            SELECT 
                COUNT(*) as total_carros,
                COUNT(CASE WHEN status_carro = 'DISPONIVEL' THEN 1 END) as disponiveis,
                COUNT(CASE WHEN status_carro = 'ALUGADO' THEN 1 END) as alugados,
                COUNT(CASE WHEN status_carro = 'MANUTENCAO' THEN 1 END) as manutencao,
                AVG(quilometragem) as media_km,
                MIN(ano) as ano_mais_antigo,
                MAX(ano) as ano_mais_novo
            FROM Carro;
        """
        estatisticas = db.execute_select_one(query)

        # Estatísticas por categoria
        query_categorias = """
            SELECT 
                tipo_categoria,
                COUNT(*) as quantidade,
                AVG(quilometragem) as media_km
            FROM Carro
            GROUP BY tipo_categoria
            ORDER BY quantidade DESC;
        """
        categorias_stats = db.execute_select_all(query_categorias)

        return jsonify({
            "estatisticas_gerais": estatisticas,
            "estatisticas_categorias": categorias_stats
        }), 200
    except Exception as e:
        print(f"Erro: {e}")
        return internal_error()

# ============================================================
# 13. Carros que precisam de manutenção (alta quilometragem)
# ============================================================


@carros_blueprint.route("/carros/manutencao-preventiva", methods=["GET"])
def carros_manutencao_preventiva():
    db = DatabaseManager()
    try:
        query = """
            SELECT 
                c.placa,
                c.nome,
                c.tipo_categoria,
                c.quilometragem,
                c.ano,
                cat.preco_diaria AS preco,
                CASE 
                    WHEN c.quilometragem > 100000 THEN 'ALTA'
                    WHEN c.quilometragem > 50000 THEN 'MEDIA'
                    ELSE 'BAIXA'
                END as prioridade_manutencao
            FROM Carro c
            JOIN Categoria cat ON c.tipo_categoria = cat.tipo
            WHERE c.status_carro != 'MANUTENCAO'
            AND c.quilometragem > 30000  # Acima de 30k km pode precisar de revisão
            ORDER BY c.quilometragem DESC;
        """
        carros = db.execute_select_all(query)
        return jsonify({"carros_manutencao_preventiva": carros}), 200
    except Exception as e:
        print(f"Erro: {e}")
        return internal_error()
