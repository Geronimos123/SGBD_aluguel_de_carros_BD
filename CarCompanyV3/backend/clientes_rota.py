from flask import Blueprint, request, jsonify
from database.conector import DatabaseManager
import re

clientes_blueprint = Blueprint("clientes", __name__)

# ============================================================
# Helpers
# ============================================================
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

# ============================================================
# 1. Listar clientes - CORRIGIDO
# ============================================================
@clientes_blueprint.route("/clientes", methods=["GET"])
def listar_clientes():
    db = DatabaseManager()
    try:
        query = """
            SELECT 
                cpf, 
                nome, 
                endereco, 
                telefone,
                (SELECT COUNT(*) FROM Aluguel WHERE cpf_cliente = cpf) as total_alugueis
            FROM Cliente
            ORDER BY nome;
        """
        clientes = db.execute_select_all(query)
        return jsonify({"clientes": clientes}), 200
    except Exception as e:
        return internal_error(str(e))

# ============================================================
# 2. Obter cliente por CPF - CORRIGIDO
# ============================================================
@clientes_blueprint.route("/clientes/<cpf>", methods=["GET"])
def obter_cliente(cpf):
    db = DatabaseManager()
    try:
        cpf_formatado = formatar_cpf(cpf)
        if not cpf_formatado:
            return bad_request("CPF inválido")

        query = """
            SELECT 
                cpf, 
                nome, 
                endereco, 
                telefone,
                (SELECT COUNT(*) FROM Aluguel WHERE cpf_cliente = Cliente.cpf) as total_alugueis,
                (SELECT MAX(data_retirada) FROM Aluguel WHERE cpf_cliente = Cliente.cpf) as ultimo_aluguel
            FROM Cliente 
            WHERE cpf = %s;
        """
        cliente = db.execute_select_one(query, (cpf_formatado,))

        if not cliente:
            return jsonify({"erro": "Cliente não encontrado"}), 404

        return jsonify(cliente), 200
    except Exception as e:
        return internal_error(str(e))

# ============================================================
# 3. Buscar por parte do nome - CORRIGIDO
# ============================================================
@clientes_blueprint.route("/clientes/busca/<nome>", methods=["GET"])
def buscar_por_nome(nome):
    db = DatabaseManager()
    try:
        if len(nome) < 2:
            return bad_request("Termo de busca deve ter pelo menos 2 caracteres")

        query = """
            SELECT 
                cpf, 
                nome, 
                endereco, 
                telefone,
                (SELECT COUNT(*) FROM Aluguel WHERE cpf_cliente = Cliente.cpf) as total_alugueis
            FROM Cliente
            WHERE nome ILIKE %s
            ORDER BY nome;
        """
        dados = db.execute_select_all(query, (f"%{nome}%",))
        return jsonify({"clientes": dados}), 200
    except Exception as e:
        return internal_error(str(e))

# ============================================================
# 4. Criar cliente - CORRIGIDO
# ============================================================
@clientes_blueprint.route("/clientes", methods=["POST"])
def criar_cliente():
    data = request.json or {}

    required = ["cpf", "nome"]
    missing = validate_fields(data, required)
    if missing:
        return bad_request("Campos obrigatórios ausentes", missing)

    # Validar CPF
    cpf_formatado = formatar_cpf(data["cpf"])
    if not cpf_formatado:
        return bad_request("CPF inválido. Deve conter 11 dígitos numéricos.")

    db = DatabaseManager()
    try:
        # Verificar se CPF já existe
        cliente_existente = db.execute_select_one(
            "SELECT cpf FROM Cliente WHERE cpf = %s", 
            (cpf_formatado,)
        )
        if cliente_existente:
            return bad_request("CPF já cadastrado")

        query = """
            INSERT INTO Cliente (cpf, nome, endereco, telefone)
            VALUES (%s, %s, %s, %s);
        """
        
        success = db.execute_statement(
            query,
            (
                cpf_formatado,
                data["nome"].strip(),
                data.get("endereco", "").strip(),
                data.get("telefone", "").strip(),
            ),
        )

        if not success:
            return internal_error("Falha ao cadastrar cliente")

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({
            "mensagem": "Cliente cadastrado com sucesso!",
            "cpf": cpf_formatado
        }), 201

    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return internal_error(str(e))

# ============================================================
# 5. Atualizar cliente - CORRIGIDO
# ============================================================
@clientes_blueprint.route("/clientes/<cpf>", methods=["PUT"])
def atualizar_cliente(cpf):
    data = request.json or {}
    
    if not data:
        return bad_request("Nenhum dado fornecido para atualização")

    cpf_formatado = formatar_cpf(cpf)
    if not cpf_formatado:
        return bad_request("CPF inválido")

    db = DatabaseManager()
    try:
        # Verificar se cliente existe
        cliente_existente = db.execute_select_one(
            "SELECT cpf FROM Cliente WHERE cpf = %s", 
            (cpf_formatado,)
        )
        if not cliente_existente:
            return jsonify({"erro": "Cliente não encontrado"}), 404

        query = """
            UPDATE Cliente
            SET nome = COALESCE(%s, nome),
                endereco = COALESCE(%s, endereco),
                telefone = COALESCE(%s, telefone)
            WHERE cpf = %s;
        """
        
        success = db.execute_statement(
            query,
            (
                data.get("nome", "").strip() or None,
                data.get("endereco", "").strip() or None,
                data.get("telefone", "").strip() or None,
                cpf_formatado,
            ),
        )

        if not success:
            return internal_error("Falha ao atualizar cliente")

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({"mensagem": "Cliente atualizado com sucesso!"}), 200

    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return internal_error(str(e))

# ============================================================
# 6. Remover cliente - CORRIGIDO
# ============================================================
@clientes_blueprint.route("/clientes/<cpf>", methods=["DELETE"])
def deletar_cliente(cpf):
    cpf_formatado = formatar_cpf(cpf)
    if not cpf_formatado:
        return bad_request("CPF inválido")

    db = DatabaseManager()
    try:
        # Verificar se cliente existe
        cliente = db.execute_select_one(
            "SELECT cpf, nome FROM Cliente WHERE cpf = %s", 
            (cpf_formatado,)
        )
        if not cliente:
            return jsonify({"erro": "Cliente não encontrado"}), 404

        # Verificar se cliente tem aluguéis ativos
        aluguel_ativo = db.execute_select_one("""
            SELECT 1 FROM Aluguel 
            WHERE cpf_cliente = %s 
            AND NOT EXISTS (
                SELECT 1 FROM Devolucao WHERE num_locacao = Aluguel.num_locacao
            )
        """, (cpf_formatado,))

        if aluguel_ativo:
            return jsonify({"erro": "Não é possível remover cliente com aluguel em andamento"}), 400

        # Verificar histórico geral de aluguéis
        historico_alugueis = db.execute_select_one(
            "SELECT COUNT(*) as total FROM Aluguel WHERE cpf_cliente = %s",
            (cpf_formatado,)
        )

        if historico_alugueis and historico_alugueis["total"] > 0:
            return jsonify({
                "erro": "Não é possível remover cliente com histórico de aluguel",
                "total_alugueis": historico_alugueis["total"]
            }), 400

        query = "DELETE FROM Cliente WHERE cpf = %s;"
        success = db.execute_statement(query, (cpf_formatado,))
        
        if not success:
            return internal_error("Falha ao remover cliente")

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({"mensagem": "Cliente removido com sucesso!"}), 200

    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return internal_error(str(e))

# ============================================================
# 7. Histórico de locações - CORRIGIDO
# ============================================================
@clientes_blueprint.route("/clientes/<cpf>/historico", methods=["GET"])
def historico_cliente(cpf):
    cpf_formatado = formatar_cpf(cpf)
    if not cpf_formatado:
        return bad_request("CPF inválido")

    db = DatabaseManager()
    try:
        # Verificar se cliente existe
        cliente = db.execute_select_one(
            "SELECT nome FROM Cliente WHERE cpf = %s", 
            (cpf_formatado,)
        )
        if not cliente:
            return jsonify({"erro": "Cliente não encontrado"}), 404

        query = """
            SELECT 
                a.num_locacao,
                a.data_retirada,
                a.data_prevista_devolucao,
                a.valor_previsto,
                a.placa,
                c.nome as nome_carro,
                c.tipo_categoria,
                cat.preco_diaria,
                CASE 
                    WHEN EXISTS (SELECT 1 FROM Devolucao d WHERE d.num_locacao = a.num_locacao) 
                    THEN 'FINALIZADO' 
                    ELSE 'EM ANDAMENTO' 
                END as status,
                d.data_real_devolucao,
                p.valor_total as valor_final
            FROM Aluguel a
            JOIN Carro c ON c.placa = a.placa
            JOIN Categoria cat ON c.tipo_categoria = cat.tipo
            LEFT JOIN Devolucao d ON d.num_locacao = a.num_locacao
            LEFT JOIN Pagamento p ON p.num_pagamento = d.num_pagamento
            WHERE a.cpf_cliente = %s
            ORDER BY a.data_retirada DESC;
        """
        dados = db.execute_select_all(query, (cpf_formatado,))
        
        # Calcular estatísticas
        total_alugueis = len(dados)
        alugueis_ativos = len([a for a in dados if a["status"] == "EM ANDAMENTO"])
        total_gasto = sum([a["valor_final"] or a["valor_previsto"] for a in dados if a["valor_final"] or a["valor_previsto"]])

        return jsonify({
            "cliente": cliente["nome"],
            "cpf": cpf_formatado,
            "historico": dados,
            "estatisticas": {
                "total_alugueis": total_alugueis,
                "alugueis_ativos": alugueis_ativos,
                "total_gasto": total_gasto
            }
        }), 200

    except Exception as e:
        return internal_error(str(e))

# ============================================================
# 8. Promoção — Clientes que alugaram TODAS as categorias
# ============================================================
@clientes_blueprint.route("/clientes/promocao/todas-categorias", methods=["GET"])
def clientes_todas_categorias():
    db = DatabaseManager()
    try:
        query = """
            SELECT cli.cpf, cli.nome, COUNT(DISTINCT car.tipo_categoria) as categorias_utilizadas
            FROM Cliente cli
            JOIN Aluguel al ON al.cpf_cliente = cli.cpf
            JOIN Carro car ON car.placa = al.placa
            GROUP BY cli.cpf, cli.nome
            HAVING COUNT(DISTINCT car.tipo_categoria) = (SELECT COUNT(*) FROM Categoria)
            ORDER BY cli.nome;
        """
        dados = db.execute_select_all(query)
        return jsonify({"clientes_elite": dados}), 200
    except Exception as e:
        return internal_error(str(e))

# ============================================================
# 9. Promoção — Clientes que usaram TODOS os acessórios
# ============================================================
@clientes_blueprint.route("/clientes/promocao/todos-acessorios", methods=["GET"])
def clientes_todos_acessorios():
    db = DatabaseManager()
    try:
        query = """
            SELECT cli.cpf, cli.nome, COUNT(DISTINCT aa.tipo_acessorio) as acessorios_utilizados
            FROM Cliente cli
            JOIN Aluguel al ON al.cpf_cliente = cli.cpf
            JOIN Aluguel_Acessorio aa ON aa.num_locacao = al.num_locacao
            GROUP BY cli.cpf, cli.nome
            HAVING COUNT(DISTINCT aa.tipo_acessorio) = (SELECT COUNT(*) FROM Acessorio)
            ORDER BY cli.nome;
        """
        dados = db.execute_select_all(query)
        return jsonify({"clientes_premium": dados}), 200
    except Exception as e:
        return internal_error(str(e))

# ============================================================
# 10. Estatísticas dos clientes
# ============================================================
@clientes_blueprint.route("/clientes/estatisticas", methods=["GET"])
def estatisticas_clientes():
    db = DatabaseManager()
    try:
        query = """
            SELECT 
                COUNT(*) as total_clientes,
                COUNT(CASE WHEN EXISTS (
                    SELECT 1 FROM Aluguel WHERE cpf_cliente = Cliente.cpf
                ) THEN 1 END) as clientes_ativos,
                AVG((SELECT COUNT(*) FROM Aluguel WHERE cpf_cliente = Cliente.cpf)) as media_alugueis_por_cliente,
                MAX((SELECT COUNT(*) FROM Aluguel WHERE cpf_cliente = Cliente.cpf)) as max_alugueis_cliente
            FROM Cliente;
        """
        estatisticas = db.execute_select_one(query)
        
        # Top clientes
        query_top = """
            SELECT 
                c.cpf,
                c.nome,
                COUNT(a.num_locacao) as total_alugueis,
                SUM(COALESCE(p.valor_total, a.valor_previsto)) as total_gasto
            FROM Cliente c
            LEFT JOIN Aluguel a ON a.cpf_cliente = c.cpf
            LEFT JOIN Devolucao d ON d.num_locacao = a.num_locacao
            LEFT JOIN Pagamento p ON p.num_pagamento = d.num_pagamento
            GROUP BY c.cpf, c.nome
            ORDER BY total_gasto DESC NULLS LAST
            LIMIT 10;
        """
        top_clientes = db.execute_select_all(query_top)
        
        return jsonify({
            "estatisticas_gerais": estatisticas,
            "top_clientes": top_clientes
        }), 200
    except Exception as e:
        return internal_error(str(e))

# ============================================================
# 11. Verificar se cliente existe
# ============================================================
@clientes_blueprint.route("/clientes/<cpf>/existe", methods=["GET"])
def verificar_cliente_existe(cpf):
    cpf_formatado = formatar_cpf(cpf)
    if not cpf_formatado:
        return jsonify({"existe": False, "erro": "CPF inválido"}), 400

    db = DatabaseManager()
    try:
        cliente = db.execute_select_one(
            "SELECT nome FROM Cliente WHERE cpf = %s", 
            (cpf_formatado,)
        )
        
        if cliente:
            return jsonify({
                "existe": True,
                "cliente": {
                    "cpf": cpf_formatado,
                    "nome": cliente["nome"]
                }
            }), 200
        else:
            return jsonify({"existe": False}), 200

    except Exception as e:
        return internal_error(str(e))

# ============================================================
# 12. Criar ou atualizar cliente (UPSERT)
# ============================================================
@clientes_blueprint.route("/clientes/upsert", methods=["POST"])
def upsert_cliente():
    data = request.json or {}

    required = ["cpf", "nome"]
    missing = validate_fields(data, required)
    if missing:
        return bad_request("Campos obrigatórios ausentes", missing)

    cpf_formatado = formatar_cpf(data["cpf"])
    if not cpf_formatado:
        return bad_request("CPF inválido. Deve conter 11 dígitos numéricos.")

    db = DatabaseManager()
    try:
        # Verificar se cliente já existe
        cliente_existente = db.execute_select_one(
            "SELECT cpf FROM Cliente WHERE cpf = %s", 
            (cpf_formatado,)
        )

        if cliente_existente:
            # Atualizar cliente existente
            query = """
                UPDATE Cliente
                SET nome = %s,
                    endereco = COALESCE(%s, endereco),
                    telefone = COALESCE(%s, telefone)
                WHERE cpf = %s;
            """
            success = db.execute_statement(
                query,
                (
                    data["nome"].strip(),
                    data.get("endereco", "").strip() or None,
                    data.get("telefone", "").strip() or None,
                    cpf_formatado,
                ),
            )
            acao = "atualizado"
        else:
            # Criar novo cliente
            query = """
                INSERT INTO Cliente (cpf, nome, endereco, telefone)
                VALUES (%s, %s, %s, %s);
            """
            success = db.execute_statement(
                query,
                (
                    cpf_formatado,
                    data["nome"].strip(),
                    data.get("endereco", "").strip(),
                    data.get("telefone", "").strip(),
                ),
            )
            acao = "criado"

        if not success:
            return internal_error(f"Falha ao {acao} cliente")

        # Commit da transação
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({
            "mensagem": f"Cliente {acao} com sucesso!",
            "cpf": cpf_formatado,
            "acao": acao
        }), 200

    except Exception as e:
        # Rollback em caso de erro
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return internal_error(str(e))