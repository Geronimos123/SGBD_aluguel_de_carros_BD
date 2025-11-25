from flask import Blueprint, request, jsonify
from database.conector import DatabaseManager
import re
from datetime import datetime, date
from psycopg2 import IntegrityError

funcionarios_blueprint = Blueprint("funcionarios", __name__)

# ----------------------
# Helpers
# ----------------------
def bad_request(msg, fields=None):
    resp = {"erro": msg}
    if fields:
        resp["faltando"] = fields
    return jsonify(resp), 400

def internal_error(msg="Erro interno no servidor"):
    print(f"DEBUG: {msg}")
    return jsonify({"erro": msg}), 500

def validate_fields(data, required):
    missing = [f for f in required if f not in data or data[f] in (None, "")]
    return missing

def validar_cpf(cpf: str):
    """Valida formato do CPF (11 dígitos numéricos)"""
    if not cpf or not isinstance(cpf, str):
        return False
    cpf_limpo = re.sub(r'\D', '', cpf)
    return len(cpf_limpo) == 11 and cpf_limpo.isdigit()

def formatar_cpf(cpf: str):
    """Remove formatação do CPF"""
    return re.sub(r'\D', '', cpf) if cpf else None

def validar_data(data_str):
    """Valida formato de data YYYY-MM-DD"""
    try:
        datetime.strptime(data_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

# ----------------------
# 1 — Listar funcionários (para dropdown / lista completa) - CORRIGIDO
# ----------------------
@funcionarios_blueprint.route("/funcionarios", methods=["GET"])
def listar_funcionarios():
    db = DatabaseManager()
    try:
        query = """
            SELECT 
                num_funcionario, 
                cpf, 
                nome, 
                data_inicio, 
                endereco, 
                telefone, 
                qnt_vendas,
                (CURRENT_DATE - data_inicio) as dias_empresa,
                CASE 
                    WHEN (CURRENT_DATE - data_inicio) > 365 THEN 'SENIOR'
                    WHEN (CURRENT_DATE - data_inicio) > 180 THEN 'EXPERIENTE'
                    ELSE 'NOVATO'
                END as experiencia
            FROM Funcionario
            ORDER BY qnt_vendas DESC, nome;
        """
        dados = db.execute_select_all(query)
        return jsonify({"funcionarios": dados}), 200
    except Exception as e:
        return internal_error(str(e))

# ----------------------
# 2 — Criar funcionário - CORRIGIDO
# ----------------------
@funcionarios_blueprint.route("/funcionarios", methods=["POST"])
def criar_funcionario():
    data = request.json or {}
    required = ["cpf", "nome", "data_inicio"]
    missing = validate_fields(data, required)
    if missing:
        return bad_request("Campos faltando", missing)

    # Validar CPF
    cpf_formatado = formatar_cpf(data["cpf"])
    if not cpf_formatado:
        return bad_request("CPF inválido. Deve conter 11 dígitos numéricos.")

    # Validar data
    if not validar_data(data["data_inicio"]):
        return bad_request("Data de início inválida. Use formato YYYY-MM-DD.")

    # Validar data não futura
    data_inicio = datetime.strptime(data["data_inicio"], "%Y-%m-%d").date()
    if data_inicio > date.today():
        return bad_request("Data de início não pode ser futura.")

    db = DatabaseManager()
    try:
        # Verificar se CPF já existe
        funcionario_existente = db.execute_select_one(
            "SELECT cpf FROM Funcionario WHERE cpf = %s", 
            (cpf_formatado,)
        )
        if funcionario_existente:
            return bad_request("CPF já cadastrado")

        query = """
            INSERT INTO Funcionario (cpf, nome, data_inicio, endereco, telefone, qnt_vendas)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING num_funcionario;
        """
        res = db.execute_insert_returning(query, (
            cpf_formatado,
            data["nome"].strip(),
            data_inicio,
            data.get("endereco", "").strip(),
            data.get("telefone", "").strip(),
            data.get("qnt_vendas", 0)
        ))
        
        if not res:
            return internal_error("Falha ao criar funcionário")

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({
            "mensagem": "Funcionário cadastrado com sucesso!", 
            "num_funcionario": res["num_funcionario"]
        }), 201

    except IntegrityError as ie:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return bad_request("Erro de integridade: possível CPF duplicado ou dado inválido.")
    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return internal_error(str(e))

# ----------------------
# 3 — Obter funcionário por ID - CORRIGIDO
# ----------------------
@funcionarios_blueprint.route("/funcionarios/<int:num_funcionario>", methods=["GET"])
def obter_funcionario(num_funcionario):
    db = DatabaseManager()
    try:
        query = """
            SELECT 
                num_funcionario, 
                cpf, 
                nome, 
                data_inicio, 
                endereco, 
                telefone, 
                qnt_vendas,
                (CURRENT_DATE - data_inicio) as dias_empresa,
                (SELECT COUNT(*) FROM Aluguel WHERE num_funcionario = %s) as total_alugueis,
                (SELECT COALESCE(SUM(valor_previsto), 0) FROM Aluguel WHERE num_funcionario = %s) as valor_total_vendas
            FROM Funcionario
            WHERE num_funcionario = %s;
        """
        funcionario = db.execute_select_one(query, (num_funcionario, num_funcionario, num_funcionario))
        if not funcionario:
            return jsonify({"erro": "Funcionário não encontrado"}), 404
        return jsonify(funcionario), 200
    except Exception as e:
        return internal_error(str(e))

# ----------------------
# 4 — Atualizar funcionário (dinâmico) - CORRIGIDO
# ----------------------
@funcionarios_blueprint.route("/funcionarios/<int:num_funcionario>", methods=["PUT"])
def atualizar_funcionario(num_funcionario):
    data = request.json or {}
    
    if not data:
        return bad_request("Nenhum dado fornecido para atualização")

    db = DatabaseManager()
    try:
        # Verificar se funcionário existe
        funcionario_existente = db.execute_select_one(
            "SELECT num_funcionario FROM Funcionario WHERE num_funcionario = %s", 
            (num_funcionario,)
        )
        if not funcionario_existente:
            return jsonify({"erro": "Funcionário não encontrado"}), 404

        # se CPF presente, validar
        if "cpf" in data and data["cpf"]:
            cpf_formatado = formatar_cpf(data["cpf"])
            if not cpf_formatado:
                return bad_request("CPF inválido. Deve conter 11 dígitos numéricos.")
            data["cpf"] = cpf_formatado

        # Validar data se fornecida
        if "data_inicio" in data and data["data_inicio"]:
            if not validar_data(data["data_inicio"]):
                return bad_request("Data de início inválida. Use formato YYYY-MM-DD.")
            data_inicio = datetime.strptime(data["data_inicio"], "%Y-%m-%d").date()
            if data_inicio > date.today():
                return bad_request("Data de início não pode ser futura.")

        query = """
            UPDATE Funcionario
            SET cpf = COALESCE(%s, cpf),
                nome = COALESCE(%s, nome),
                data_inicio = COALESCE(%s, data_inicio),
                endereco = COALESCE(%s, endereco),
                telefone = COALESCE(%s, telefone),
                qnt_vendas = COALESCE(%s, qnt_vendas)
            WHERE num_funcionario = %s;
        """
        success = db.execute_statement(
            query,
            (
                data.get("cpf"),
                data.get("nome"),
                data.get("data_inicio"),
                data.get("endereco"),
                data.get("telefone"),
                data.get("qnt_vendas"),
                num_funcionario,
            ),
        )

        if not success:
            return internal_error("Falha ao atualizar funcionário")

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({"mensagem": "Funcionário atualizado com sucesso!"}), 200

    except IntegrityError:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return bad_request("Erro de integridade ao atualizar (ex: CPF duplicado).")
    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return internal_error(str(e))

# ----------------------
# 5 — Deletar funcionário - CORRIGIDO
# ----------------------
@funcionarios_blueprint.route("/funcionarios/<int:num_funcionario>", methods=["DELETE"])
def deletar_funcionario(num_funcionario):
    db = DatabaseManager()
    try:
        # Verificar se funcionário existe
        funcionario = db.execute_select_one(
            "SELECT num_funcionario, nome FROM Funcionario WHERE num_funcionario = %s", 
            (num_funcionario,)
        )
        if not funcionario:
            return jsonify({"erro": "Funcionário não encontrado"}), 404

        # Verificar se funcionário tem aluguéis associados
        alugueis_associados = db.execute_select_one(
            "SELECT COUNT(*) as total FROM Aluguel WHERE num_funcionario = %s",
            (num_funcionario,)
        )

        if alugueis_associados and alugueis_associados["total"] > 0:
            return jsonify({
                "erro": "Não é possível remover funcionário com aluguéis associados",
                "total_alugueis": alugueis_associados["total"]
            }), 400

        query = "DELETE FROM Funcionario WHERE num_funcionario = %s;"
        success = db.execute_statement(query, (num_funcionario,))
        
        if not success:
            return internal_error("Falha ao remover funcionário")

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({"mensagem": "Funcionário removido com sucesso!"}), 200

    except IntegrityError:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return bad_request("Não foi possível remover: existe referência a este funcionário (FK).")
    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return internal_error(str(e))

# ----------------------
# 6 — Ranking de Vendas - CORRIGIDO
# ----------------------
@funcionarios_blueprint.route("/funcionarios/ranking", methods=["GET"])
def ranking_vendas():
    db = DatabaseManager()
    try:
        query = """
            SELECT 
                num_funcionario, 
                cpf, 
                nome, 
                qnt_vendas,
                (SELECT COUNT(*) FROM Aluguel WHERE num_funcionario = Funcionario.num_funcionario) as total_alugueis,
                (SELECT COALESCE(SUM(valor_previsto), 0) FROM Aluguel WHERE num_funcionario = Funcionario.num_funcionario) as valor_total_vendas,
                (CURRENT_DATE - data_inicio) as dias_empresa,
                CASE 
                    WHEN qnt_vendas > 0 THEN 
                        ROUND((qnt_vendas::decimal / (SELECT COUNT(*) FROM Aluguel WHERE num_funcionario = Funcionario.num_funcionario)) * 100, 2)
                    ELSE 0
                END as taxa_conversao
            FROM Funcionario
            ORDER BY qnt_vendas DESC, valor_total_vendas DESC;
        """
        dados = db.execute_select_all(query)
        return jsonify({"ranking": dados}), 200
    except Exception as e:
        return internal_error(str(e))

# ----------------------
# 7 — Estatísticas dos funcionários
# ----------------------
@funcionarios_blueprint.route("/funcionarios/estatisticas", methods=["GET"])
def estatisticas_funcionarios():
    db = DatabaseManager()
    try:
        query = """
            SELECT 
                COUNT(*) as total_funcionarios,
                AVG(qnt_vendas) as media_vendas,
                MAX(qnt_vendas) as max_vendas,
                MIN(qnt_vendas) as min_vendas,
                SUM(qnt_vendas) as total_vendas,
                AVG((CURRENT_DATE - data_inicio)) as media_dias_empresa,
                COUNT(CASE WHEN (CURRENT_DATE - data_inicio) > 365 THEN 1 END) as funcionarios_senior
            FROM Funcionario;
        """
        estatisticas = db.execute_select_one(query)
        
        # Vendas por mês (últimos 6 meses)
        query_vendas_mensais = """
            SELECT 
                TO_CHAR(data_retirada, 'YYYY-MM') as mes,
                COUNT(*) as total_alugueis,
                SUM(valor_previsto) as valor_total
            FROM Aluguel 
            WHERE data_retirada >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(data_retirada, 'YYYY-MM')
            ORDER BY mes DESC;
        """
        vendas_mensais = db.execute_select_all(query_vendas_mensais)
        
        return jsonify({
            "estatisticas_gerais": estatisticas,
            "vendas_mensais": vendas_mensais
        }), 200
    except Exception as e:
        return internal_error(str(e))

# ----------------------
# 8 — Buscar funcionários por nome
# ----------------------
@funcionarios_blueprint.route("/funcionarios/busca/<nome>", methods=["GET"])
def buscar_funcionarios_por_nome(nome):
    db = DatabaseManager()
    try:
        if len(nome) < 2:
            return bad_request("Termo de busca deve ter pelo menos 2 caracteres")

        query = """
            SELECT 
                num_funcionario, 
                cpf, 
                nome, 
                data_inicio, 
                endereco, 
                telefone, 
                qnt_vendas
            FROM Funcionario
            WHERE nome ILIKE %s
            ORDER BY qnt_vendas DESC, nome;
        """
        dados = db.execute_select_all(query, (f"%{nome}%",))
        return jsonify({"funcionarios": dados}), 200
    except Exception as e:
        return internal_error(str(e))

# ----------------------
# 9 — Atualizar contador de vendas
# ----------------------
@funcionarios_blueprint.route("/funcionarios/<int:num_funcionario>/vendas", methods=["PUT"])
def atualizar_vendas_funcionario(num_funcionario):
    data = request.json or {}
    
    if "qnt_vendas" not in data:
        return bad_request("Campo 'qnt_vendas' é obrigatório")

    try:
        qnt_vendas = int(data["qnt_vendas"])
        if qnt_vendas < 0:
            return bad_request("Quantidade de vendas não pode ser negativa")
    except (ValueError, TypeError):
        return bad_request("Quantidade de vendas deve ser um número inteiro")

    db = DatabaseManager()
    try:
        # Verificar se funcionário existe
        funcionario_existente = db.execute_select_one(
            "SELECT num_funcionario FROM Funcionario WHERE num_funcionario = %s", 
            (num_funcionario,)
        )
        if not funcionario_existente:
            return jsonify({"erro": "Funcionário não encontrado"}), 404

        query = "UPDATE Funcionario SET qnt_vendas = %s WHERE num_funcionario = %s;"
        success = db.execute_statement(query, (qnt_vendas, num_funcionario))

        if not success:
            return internal_error("Falha ao atualizar vendas")

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({"mensagem": "Vendas atualizadas com sucesso!"}), 200

    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return internal_error(str(e))

# ----------------------
# 10 — Incrementar contador de vendas
# ----------------------
@funcionarios_blueprint.route("/funcionarios/<int:num_funcionario>/incrementar-vendas", methods=["POST"])
def incrementar_vendas_funcionario(num_funcionario):
    db = DatabaseManager()
    try:
        # Verificar se funcionário existe
        funcionario_existente = db.execute_select_one(
            "SELECT num_funcionario, qnt_vendas FROM Funcionario WHERE num_funcionario = %s", 
            (num_funcionario,)
        )
        if not funcionario_existente:
            return jsonify({"erro": "Funcionário não encontrado"}), 404

        query = "UPDATE Funcionario SET qnt_vendas = qnt_vendas + 1 WHERE num_funcionario = %s;"
        success = db.execute_statement(query, (num_funcionario,))

        if not success:
            return internal_error("Falha ao incrementar vendas")

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        novas_vendas = funcionario_existente["qnt_vendas"] + 1

        return jsonify({
            "mensagem": "Vendas incrementadas com sucesso!",
            "novo_total": novas_vendas
        }), 200

    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return internal_error(str(e))

# ----------------------
# 11 — Histórico de aluguéis por funcionário
# ----------------------
@funcionarios_blueprint.route("/funcionarios/<int:num_funcionario>/alugueis", methods=["GET"])
def historico_alugueis_funcionario(num_funcionario):
    db = DatabaseManager()
    try:
        # Verificar se funcionário existe
        funcionario = db.execute_select_one(
            "SELECT nome FROM Funcionario WHERE num_funcionario = %s", 
            (num_funcionario,)
        )
        if not funcionario:
            return jsonify({"erro": "Funcionário não encontrado"}), 404

        query = """
            SELECT 
                a.num_locacao,
                a.data_retirada,
                a.data_prevista_devolucao,
                a.valor_previsto,
                a.placa,
                c.nome as nome_carro,
                c.tipo_categoria,
                cli.nome as nome_cliente,
                cli.cpf as cpf_cliente,
                CASE 
                    WHEN EXISTS (SELECT 1 FROM Devolucao d WHERE d.num_locacao = a.num_locacao) 
                    THEN 'FINALIZADO' 
                    ELSE 'EM ANDAMENTO' 
                END as status
            FROM Aluguel a
            JOIN Carro c ON c.placa = a.placa
            JOIN Cliente cli ON cli.cpf = a.cpf_cliente
            WHERE a.num_funcionario = %s
            ORDER BY a.data_retirada DESC;
        """
        alugueis = db.execute_select_all(query, (num_funcionario,))
        
        # Estatísticas do funcionário
        estatisticas = db.execute_select_one("""
            SELECT 
                COUNT(*) as total_alugueis,
                SUM(valor_previsto) as valor_total,
                AVG(valor_previsto) as valor_medio,
                MIN(data_retirada) as primeiro_aluguel,
                MAX(data_retirada) as ultimo_aluguel
            FROM Aluguel 
            WHERE num_funcionario = %s
        """, (num_funcionario,))

        return jsonify({
            "funcionario": funcionario["nome"],
            "num_funcionario": num_funcionario,
            "alugueis": alugueis,
            "estatisticas": estatisticas
        }), 200

    except Exception as e:
        return internal_error(str(e))

# ----------------------
# 12 — Funcionários do mês (top performers)
# ----------------------
@funcionarios_blueprint.route("/funcionarios/top-mes", methods=["GET"])
def top_funcionarios_mes():
    db = DatabaseManager()
    try:
        query = """
            SELECT 
                f.num_funcionario,
                f.nome,
                COUNT(a.num_locacao) as alugueis_mes,
                SUM(a.valor_previsto) as valor_mes
            FROM Funcionario f
            JOIN Aluguel a ON a.num_funcionario = f.num_funcionario
            WHERE EXTRACT(MONTH FROM a.data_retirada) = EXTRACT(MONTH FROM CURRENT_DATE)
            AND EXTRACT(YEAR FROM a.data_retirada) = EXTRACT(YEAR FROM CURRENT_DATE)
            GROUP BY f.num_funcionario, f.nome
            ORDER BY valor_mes DESC
            LIMIT 5;
        """
        top_funcionarios = db.execute_select_all(query)
        return jsonify({"top_funcionarios_mes": top_funcionarios}), 200
    except Exception as e:
        return internal_error(str(e))