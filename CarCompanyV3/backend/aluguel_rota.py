from flask import Blueprint, request, jsonify
from database.conector import DatabaseManager
from datetime import datetime, date, timedelta
import re

aluguel_blueprint = Blueprint("aluguel", __name__)

# =========================================================
# Helpers
# =========================================================
# normaliza valores vindos do DB para datetime.date


def to_date_obj(v):
    """
    Converte v para datetime.date quando possível.
    Aceita datetime.date, datetime.datetime, strings em ISO (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS).
    Retorna None se não conseguir converter.
    """
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        # tenta ISO date ou datetime
        try:
            # datetime.fromisoformat lida com 'YYYY-MM-DD' e 'YYYY-MM-DDTHH:MM:SS'
            return datetime.fromisoformat(v).date()
        except Exception:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except Exception:
                return None
    return None


def internal_error(msg="Erro interno no servidor"):
    print(f"DEBUG: {msg}")
    return jsonify({"erro": msg}), 500


def validate_fields(data, required_fields):
    missing = [
        f for f in required_fields if f not in data or data[f] in (None, "")]
    return missing


def parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

# =========================================================
# Funções de Cálculo de Multas
# =========================================================


def calcular_multa_atraso(db, num_locacao, data_devolucao):
    """Calcula multa por atraso na devolução"""
    try:
        # Buscar data prevista e preço da diária
        query = """
            SELECT a.data_prevista_devolucao, cat.preco_diaria
            FROM Aluguel a
            JOIN Carro c ON a.placa = c.placa
            JOIN Categoria cat ON c.tipo_categoria = cat.tipo
            WHERE a.num_locacao = %s
        """
        aluguel = db.execute_select_one(query, (num_locacao,))

        if not aluguel:
            return 0, 0

        data_prevista_raw = aluguel.get('data_prevista_devolucao')
        data_prevista = to_date_obj(data_prevista_raw)
        preco_diaria = float(aluguel.get('preco_diaria') or 0)

        # normaliza data_devolucao para date
        data_dev_date = to_date_obj(data_devolucao) if not isinstance(
            data_devolucao, date) else data_devolucao

        if not data_prevista or not data_dev_date:
            return 0, 0

        if data_dev_date <= data_prevista:
            return 0, 0

        dias_atraso = (data_dev_date - data_prevista).days
        valor_multa = dias_atraso * preco_diaria * 0.5  # 50% da diária por dia

        return valor_multa, dias_atraso

    except Exception as e:
        print(f"Erro ao calcular multa por atraso: {e}")
        return 0, 0


def calcular_multa_tanque(combustivel_completo):
    """Calcula multa por tanque não cheio"""
    if not combustivel_completo:
        return 100.00  # Valor fixo de R$ 100,00
    return 0.00


def calcular_multa_danos(valor_danos):
    """Calcula multa por danos no veículo"""
    try:
        return float(valor_danos or 0)
    except (ValueError, TypeError):
        return 0.00


def calcular_multa_km(db, num_locacao, km_registro):
    """Calcula multa por excesso de quilometragem"""
    try:
        # Buscar km previsto
        query = "SELECT km_previsto FROM Aluguel WHERE num_locacao = %s"
        aluguel = db.execute_select_one(query, (num_locacao,))

        if not aluguel or not aluguel.get('km_previsto'):
            return 0, 0

        km_previsto = aluguel['km_previsto']
        km_excedente = max(km_registro - km_previsto, 0)
        valor_por_km = 0.50  # R$ 0,50 por km excedente
        valor_multa = km_excedente * valor_por_km

        return valor_multa, km_excedente

    except Exception as e:
        print(f"Erro ao calcular multa por km: {e}")
        return 0, 0


def calcular_multa_atraso_progressivo(db, num_locacao, data_devolucao):
    """Calcula multa progressiva por atraso"""
    try:
        query = """
            SELECT a.data_prevista_devolucao, cat.preco_diaria
            FROM Aluguel a
            JOIN Carro c ON a.placa = c.placa
            JOIN Categoria cat ON c.tipo_categoria = cat.tipo
            WHERE a.num_locacao = %s
        """
        aluguel = db.execute_select_one(query, (num_locacao,))

        if not aluguel:
            return 0, 0

        data_prevista_raw = aluguel.get('data_prevista_devolucao')
        data_prevista = to_date_obj(data_prevista_raw)
        preco_diaria = float(aluguel.get('preco_diaria') or 0)

        data_dev_date = to_date_obj(data_devolucao) if not isinstance(
            data_devolucao, date) else data_devolucao

        if not data_prevista or not data_dev_date:
            return 0, 0

        if data_dev_date <= data_prevista:
            return 0, 0

        dias_atraso = (data_dev_date - data_prevista).days

        # Faixas progressivas
        if dias_atraso <= 3:
            multiplicador = 0.5  # 50% da diária
        elif dias_atraso <= 7:
            multiplicador = 1.0  # 100% da diária
        else:
            multiplicador = 1.5  # 150% da diária

        valor_multa = dias_atraso * preco_diaria * multiplicador
        return valor_multa, dias_atraso

    except Exception as e:
        print(f"Erro ao calcular multa progressiva: {e}")
        return 0, 0

# =========================================================
# Funções de Cálculo de Descontos
# =========================================================


def calcular_desconto_cliente_fiel(db, cpf_cliente):
    """Desconto para clientes com 5 ou mais locações"""
    try:
        query = "SELECT COUNT(*) as total FROM Aluguel WHERE cpf_cliente = %s"
        resultado = db.execute_select_one(query, (cpf_cliente,))

        if resultado and resultado['total'] >= 5:
            return 50.00  # R$ 50,00 fixo
        return 0.00
    except Exception as e:
        print(f"Erro ao calcular desconto fidelidade: {e}")
        return 0.00


def calcular_desconto_reserva_antecipada(db, num_locacao):
    """Desconto por reserva antecipada (mais de 7 dias)"""
    try:
        query = "SELECT data_retirada FROM Aluguel WHERE num_locacao = %s"
        aluguel = db.execute_select_one(query, (num_locacao,))

        if not aluguel:
            return 0.00

        data_retirada_raw = aluguel.get('data_retirada')
        data_retirada = to_date_obj(data_retirada_raw)
        if not data_retirada:
            return 0.00

        # Se a data de retirada for mais de 7 dias após a data atual de criação
        # (Aqui estamos usando a data atual como proxy para data da reserva)
        dias_antecedencia = (data_retirada - date.today()).days

        if dias_antecedencia >= 7:
            return 30.00  # R$ 30,00 fixo
        return 0.00

    except Exception as e:
        print(f"Erro ao calcular desconto reserva antecipada: {e}")
        return 0.00


def calcular_desconto_sem_multas(db, cpf_cliente, num_locacao_atual):
    """Desconto por não ter multas nas últimas 5 locações"""
    try:
        # Buscar últimas 5 locações (excluindo a atual)
        query = """
            SELECT a.num_locacao
            FROM Aluguel a
            WHERE a.cpf_cliente = %s AND a.num_locacao != %s
            ORDER BY a.data_retirada DESC
            LIMIT 5
        """
        locacoes = db.execute_select_all(
            query, (cpf_cliente, num_locacao_atual))

        if len(locacoes) < 5:
            return 0.00

        # Verificar se alguma dessas locações teve multa
        for locacao in locacoes:
            query_multas = """
                SELECT 1 FROM Multa m
                JOIN Pagamento p ON m.num_pagamento = p.num_pagamento
                JOIN Devolucao d ON d.num_pagamento = p.num_pagamento
                WHERE d.num_locacao = %s
            """
            tem_multa = db.execute_select_one(
                query_multas, (locacao['num_locacao'],))
            if tem_multa:
                return 0.00

        return 40.00  # R$ 40,00 fixo

    except Exception as e:
        print(f"Erro ao calcular desconto sem multas: {e}")
        return 0.00


def calcular_desconto_todas_categorias(db, cpf_cliente):
    """Desconto por ter alugado todas as categorias"""
    try:
        query = """
            SELECT COUNT(DISTINCT c.tipo_categoria) as categorias_utilizadas
            FROM Aluguel a
            JOIN Carro c ON a.placa = c.placa
            WHERE a.cpf_cliente = %s
        """
        resultado = db.execute_select_one(query, (cpf_cliente,))

        total_categorias_query = "SELECT COUNT(*) as total FROM Categoria"
        total_categorias = db.execute_select_one(total_categorias_query)

        if (resultado and total_categorias and
                resultado['categorias_utilizadas'] == total_categorias['total']):
            return 60.00  # R$ 60,00 fixo
        return 0.00

    except Exception as e:
        print(f"Erro ao calcular desconto todas categorias: {e}")
        return 0.00


def calcular_desconto_todos_acessorios(db, cpf_cliente):
    """Desconto por ter usado todos os acessórios"""
    try:
        query = """
            SELECT COUNT(DISTINCT aa.tipo_acessorio) as acessorios_utilizados
            FROM Aluguel a
            JOIN Aluguel_Acessorio aa ON a.num_locacao = aa.num_locacao
            WHERE a.cpf_cliente = %s
        """
        resultado = db.execute_select_one(query, (cpf_cliente,))

        total_acessorios_query = "SELECT COUNT(*) as total FROM Acessorio"
        total_acessorios = db.execute_select_one(total_acessorios_query)

        if (resultado and total_acessorios and
                resultado['acessorios_utilizados'] == total_acessorios['total']):
            return 45.00  # R$ 45,00 fixo
        return 0.00

    except Exception as e:
        print(f"Erro ao calcular desconto todos acessórios: {e}")
        return 0.00


# =========================================================
# 4) REALIZAR DEVOLUÇÃO - ATUALIZADA COM MULTAS E DESCONTOS
# =========================================================

db = DatabaseManager()


@aluguel_blueprint.route("/aluguel", methods=["POST"])
def criar_aluguel():
    data = request.json or {}
    # exigir cpf_cliente mesmo que Aluguel não guarde — vamos inserir em HistoricoAluguel
    required = ["placa", "num_funcionario",
                "data_retirada", "data_prevista_devolucao"]
    missing = validate_fields(data, required)
    if missing:
        return jsonify({"erro": "Campos faltando", "campos": missing}), 400

    # parse datas
    data_retirada = parse_date(data["data_retirada"])
    data_prevista = parse_date(data["data_prevista_devolucao"])
    if not data_retirada or not data_prevista:
        return jsonify({"erro": "Formato de data inválido. Use YYYY-MM-DD."}), 400
    if data_prevista < data_retirada:
        return jsonify({"erro": "data_prevista_devolucao não pode ser anterior a data_retirada."}), 400

    db = DatabaseManager()
    try:
        # 1) verificar se o carro existe
        carro = db.execute_select_one(
            "SELECT placa, tipo_categoria FROM Carro WHERE placa = %s", (data["placa"],))
        if not carro:
            return jsonify({"erro": "Carro inexistente"}), 404

        # 2) verificar manutenção associada (Carro.num_manutencao -> Manutencao.data_retorno)
        num_m = carro.get("num_manutencao")
        if num_m:
            man = db.execute_select_one(
                "SELECT data_retorno FROM Manutencao WHERE num_manutencao = %s", (num_m,))
            if man and (man.get("data_retorno") is None or to_date_obj(man.get("data_retorno")) > datetime.today().date()):
                return jsonify({"erro": "Carro em manutenção e indisponível."}), 400

        novo_status = "ALUGADO"
        db.execute_statement(
            "UPDATE Carro SET status_carro = %s WHERE placa = %s",
            (novo_status, (data["placa"],))
        )

        # 3) verificar se já existe aluguel ativo para essa placa (Aluguel sem Devolucao)
        check_active = """
            SELECT 1 FROM Aluguel a
            LEFT JOIN Devolucao d ON d.num_locacao = a.num_locacao
            WHERE a.placa = %s AND d.num_locacao IS NULL
            LIMIT 1;
        """
        ativo = db.execute_select_one(check_active, (data["placa"],))
        if ativo:
            return jsonify({"erro": "Carro já está alugado (aluguel sem devolução)."}), 400

        # 4) inserir Aluguel
        # tipo_acessorio na tabela é VARCHAR(50) — se o cliente enviar lista, juntamos por ', '
        acessorios = data.get("acessorios")
        if isinstance(acessorios, list):
            # cortar para caber no campo se preciso
            tipo_acessorio = ", ".join(acessorios)[:50]
        else:
            tipo_acessorio = (acessorios or data.get("tipo_acessorio") or None)
            if tipo_acessorio and len(tipo_acessorio) > 50:
                tipo_acessorio = tipo_acessorio[:50]
        cpf_cliente = data.get("cpf_cliente")
        query_aluguel = """
            INSERT INTO Aluguel
            (data_retirada, data_prevista_devolucao, valor_previsto, num_funcionario, placa, cpf_cliente)
            VALUES (%s, %s, %s,%s,%s,%s)
            RETURNING num_locacao;
        """

        def parse_currency(value):
            if not value:
                return 0

            # Remove símbolo de moeda e espaços especiais (inclui \xa0)
            cleaned = (
                value.replace("R$", "")
                .replace("\xa0", "")
                .strip()
            )

            # Troca vírgula por ponto
            cleaned = cleaned.replace(".", "").replace(",", ".")

            return float(cleaned)

        valor_previsto = parse_currency(data.get("valor_previsto"))
        loc = db.execute_insert_returning(query_aluguel, (
            data_retirada,
            data_prevista,
            valor_previsto,
            data["num_funcionario"],
            data["placa"],
            cpf_cliente
        ))
        num_locacao = loc["num_locacao"]

        # 5) registrar histórico do cliente na tabela HistoricoAluguel
        cpf = data["cpf_cliente"]
        db.execute_statement(
            "INSERT INTO HistoricoAluguel (num_locacao, cpf) VALUES (%s, %s)",
            (num_locacao, cpf)
        )

        # Se o seu DatabaseManager expõe conn, comitar explicitamente
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.commit()
        except Exception:
            pass

        return jsonify({"mensagem": "Locação realizada!", "num_locacao": num_locacao}), 201

    except Exception as e:
        # tentar rollback se possível
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except Exception:
            pass
        return internal_error(f"Erro ao abrir locação: {str(e)}")


@aluguel_blueprint.route("/aluguel/devolver", methods=["POST"])
def devolver_carro():
    data = request.json or {}
    required = ["num_locacao", "estado_carro", "combustivel_completo"]
    missing = validate_fields(data, required)
    if missing:
        return jsonify({"erro": "Campos faltando", "campos": missing}), 400

    db = DatabaseManager()
    try:
        # 1) Buscar aluguel e verificar se não foi devolvido
        aluguel = db.execute_select_one("""
            SELECT a.*, c.tipo_categoria, cat.preco_diaria, c.placa, a.cpf_cliente
            FROM Aluguel a
            JOIN Carro c ON a.placa = c.placa
            JOIN Categoria cat ON c.tipo_categoria = cat.tipo
            WHERE a.num_locacao = %s 
            AND NOT EXISTS (
                SELECT 1 FROM Devolucao d WHERE d.num_locacao = a.num_locacao
            )
        """, (data["num_locacao"],))

        if not aluguel:
            return jsonify({"erro": "Aluguel não encontrado ou já devolvido"}), 404

        # DEBUG opcional: ver tipos retornados
        # print("DEBUG aluguel fields types:", {k: type(v) for k, v in aluguel.items()})

        placa = aluguel.get("placa")
        cpf_cliente = aluguel.get("cpf_cliente")
        data_devolucao = date.today()

        # normaliza campos retornados pelo DB para operações de data
        data_retirada_db = to_date_obj(aluguel.get("data_retirada"))
        data_prevista = to_date_obj(aluguel.get("data_prevista_devolucao"))

        # 2) Calcular valor base do aluguel
        # Se data_retirada vier None, assume-se 1 dia
        if data_retirada_db:
            dias_locacao = max((data_devolucao - data_retirada_db).days, 1)
        else:
            dias_locacao = 1

        valor_base = float(aluguel.get("preco_diaria") or 0) * dias_locacao

        # 3) CALCULAR MULTAS
        multas = []
        valor_total_multas = 0.0

        # Multa por Atraso
        multa_atraso, dias_atraso = calcular_multa_atraso(
            db, data["num_locacao"], data_devolucao)
        if multa_atraso > 0:
            multas.append({
                "tipo": "ATRASO",
                "valor": multa_atraso,
                "referencia": f"{dias_atraso} dias",
                "codigo_motivo": "ATRASO"
            })
            valor_total_multas += multa_atraso

        # Multa por Tanque não cheio
        multa_tanque = calcular_multa_tanque(data["combustivel_completo"])
        if multa_tanque > 0:
            multas.append({
                "tipo": "TANQUE_NAO_CHEIO",
                "valor": multa_tanque,
                "referencia": None,
                "codigo_motivo": "TANQUE"
            })
            valor_total_multas += multa_tanque

        # Multa por Danos
        valor_danos = data.get("valor_danos", 0)
        multa_danos = calcular_multa_danos(valor_danos)
        if multa_danos > 0:
            multas.append({
                "tipo": "DANOS_VEICULO",
                "valor": multa_danos,
                "referencia": f"Valor danos: R$ {multa_danos}",
                "codigo_motivo": "DANO"
            })
            valor_total_multas += multa_danos

        # Multa por Quilometragem (se km_registro fornecido)
        km_registro = data.get("km_registro")
        if km_registro:
            multa_km, km_excedente = calcular_multa_km(
                db, data["num_locacao"], km_registro)
            if multa_km > 0:
                multas.append({
                    "tipo": "EXCESSO_QUILOMETRAGEM",
                    "valor": multa_km,
                    "referencia": f"{km_excedente} km excedentes",
                    "codigo_motivo": "KM_EXC"
                })
                valor_total_multas += multa_km

        # 4) CALCULAR DESCONTOS
        descontos = []
        valor_total_descontos = 0.0

        # Desconto Cliente Fiel
        desc_fiel = calcular_desconto_cliente_fiel(db, cpf_cliente)
        if desc_fiel > 0:
            descontos.append({
                "tipo": "CLIENTE_FIEL",
                "valor": desc_fiel,
                "codigo_desconto": "LOYALTY_50"
            })
            valor_total_descontos += desc_fiel

        # Desconto Reserva Antecipada
        desc_reserva = calcular_desconto_reserva_antecipada(
            db, data["num_locacao"])
        if desc_reserva > 0:
            descontos.append({
                "tipo": "RESERVA_ANTECIPADA",
                "valor": desc_reserva,
                "codigo_desconto": "EARLY_BOOKING"
            })
            valor_total_descontos += desc_reserva

        # Desconto Sem Multas
        desc_sem_multas = calcular_desconto_sem_multas(
            db, cpf_cliente, data["num_locacao"])
        if desc_sem_multas > 0:
            descontos.append({
                "tipo": "SEM_MULTAS",
                "valor": desc_sem_multas,
                "codigo_desconto": "NOFINE"
            })
            valor_total_descontos += desc_sem_multas

        # Desconto Todas Categorias
        desc_categorias = calcular_desconto_todas_categorias(db, cpf_cliente)
        if desc_categorias > 0:
            descontos.append({
                "tipo": "TODAS_CATEGORIAS",
                "valor": desc_categorias,
                "codigo_desconto": "ALLCATS"
            })
            valor_total_descontos += desc_categorias

        # Desconto Todos Acessórios
        desc_acessorios = calcular_desconto_todos_acessorios(db, cpf_cliente)
        if desc_acessorios > 0:
            descontos.append({
                "tipo": "TODOS_ACESSORIOS",
                "valor": desc_acessorios,
                "codigo_desconto": "ALLACC"
            })
            valor_total_descontos += desc_acessorios

        # 5) Calcular valor final
        valor_final = valor_base + valor_total_multas - valor_total_descontos
        valor_final = max(valor_final, 0)  # Não permitir valor negativo

        # 6) Criar Pagamento
        query_pag = "INSERT INTO Pagamento (valor_total, forma_pagamento) VALUES (%s, %s) RETURNING num_pagamento;"
        forma_pagamento = data.get("forma_pagamento", "Pix")
        pag = db.execute_insert_returning(
            query_pag, (valor_final, forma_pagamento))
        num_pagamento_final = pag["num_pagamento"]

        # 7) Inserir Devolucao com dados adicionais
        query_dev = """
            INSERT INTO Devolucao 
            (num_locacao, num_pagamento, combustivel_completo, estado_carro, data_real_devolucao)
            VALUES (%s, %s, %s, %s, %s);
        """
        db.execute_statement(query_dev, (
            data["num_locacao"],
            num_pagamento_final,
            data["combustivel_completo"],
            data["estado_carro"],
            data_devolucao
        ))

        # 10) Atualizar status do carro baseado no estado
        estado = (data.get("estado_carro") or "").upper()
        novo_status = "DISPONIVEL"
        novo_num_manut = None

        if any(tok in estado for tok in ("BATIDO", "AVARIA", "QUEBRADO", "AMASSADO", "COLISAO", "COLISÃO", "COLIDIDO", "DANIFICADO")) or multa_danos > 0:
            # Criar Manutencao
            query_ins_m = """
                INSERT INTO Manutencao (placa_carro, custo, data_inicio, descricao) 
                VALUES (%s, %s, %s, %s) 
                RETURNING num_manutencao;
            """
            descricao = f"Manutenção necessária: {estado}" if multa_danos == 0 else f"Manutenção por danos no valor de R$ {multa_danos}"
            m = db.execute_insert_returning(query_ins_m, (
                placa,
                multa_danos,
                data_devolucao,
                descricao
            ))
            if m:
                novo_num_manut = m["num_manutencao"]
                novo_status = "MANUTENCAO"

        # Atualizar carro
        if novo_num_manut:
            db.execute_statement(
                "UPDATE Carro SET status_carro = %s, num_manutencao = %s WHERE placa = %s",
                (novo_status, novo_num_manut, placa)
            )
        else:
            db.execute_statement(
                "UPDATE Carro SET status_carro = %s WHERE placa = %s",
                (novo_status, placa)
            )

        # Commit final
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        # 11) Preparar resposta detalhada
        response_data = {
            "mensagem": "Devolução realizada com sucesso!",
            "num_pagamento": num_pagamento_final,
            "resumo_financeiro": {
                "valor_base": valor_base,
                "total_multas": valor_total_multas,
                "total_descontos": valor_total_descontos,
                "valor_final": valor_final
            },
            "multas_aplicadas": multas,
            "descontos_aplicados": descontos,
            "detalhes": {
                "dias_locacao": dias_locacao,
                "data_devolucao": data_devolucao.isoformat(),
                "status_carro": novo_status
            }
        }

        if 'dias_atraso' in locals() and dias_atraso > 0:
            response_data["detalhes"]["dias_atraso"] = dias_atraso

        if novo_num_manut:
            response_data["num_manutencao"] = novo_num_manut
            response_data["observacao"] = "Carro enviado para manutenção."

        return jsonify(response_data), 200

    except Exception as e:
        try:
            if hasattr(db, "conn") and db.conn:
                db.conn.rollback()
        except:
            pass
        return internal_error(f"Erro na devolução: {str(e)}")

# =========================================================
# Endpoints Adicionais para Consulta de Multas e Descontos
# =========================================================


@aluguel_blueprint.route("/aluguel/<int:num_locacao>/multas", methods=["GET"])
def obter_multas_aluguel(num_locacao):
    """Retorna todas as multas aplicadas em um aluguel"""
    db = DatabaseManager()
    try:
        query = """
            SELECT m.*, p.valor_total as valor_pagamento
            FROM Multa m
            JOIN Pagamento p ON m.num_pagamento = p.num_pagamento
            JOIN Devolucao d ON d.num_pagamento = p.num_pagamento
            WHERE d.num_locacao = %s
        """
        multas = db.execute_select_all(query, (num_locacao,))
        return jsonify({"multas": multas}), 200
    except Exception as e:
        return internal_error(str(e))


@aluguel_blueprint.route("/aluguel/placa/<placa>", methods=["GET"])
def aluguel_por_placa(placa):
    db = DatabaseManager()
    try:
        query = """
            SELECT valor_previsto, data_retorno_prevista AS data_prevista_devolucao
            FROM aluguel
            WHERE placa = %s AND data_retorno IS NULL
            LIMIT 1
        """
        dados = db.execute_select_one(query, (placa,))
        return jsonify(dados), 200
    except Exception as e:
        return internal_error(str(e))


@aluguel_blueprint.route("/aluguel/<int:num_locacao>/descontos", methods=["GET"])
def obter_descontos_aluguel(num_locacao):
    """Retorna todos os descontos aplicados em um aluguel"""
    db = DatabaseManager()
    try:
        query = """
            SELECT d.*, p.valor_total as valor_pagamento
            FROM Desconto d
            JOIN Pagamento p ON d.num_pagamento = p.num_pagamento
            JOIN Devolucao dev ON dev.num_pagamento = p.num_pagamento
            WHERE dev.num_locacao = %s
        """
        descontos = db.execute_select_all(query, (num_locacao,))
        return jsonify({"descontos": descontos}), 200
    except Exception as e:
        return internal_error(str(e))


@aluguel_blueprint.route("/aluguel/<int:num_locacao>/detalhes", methods=["GET"])
def detalhes_aluguel(num_locacao):
    """Retorna detalhes de uma locação (valor_previsto, data_prevista_devolucao, placa, categoria, preco_diaria, cpf_cliente)."""
    db = DatabaseManager()
    try:
        query = """
            SELECT a.num_locacao,
                   a.placa,
                   a.cpf_cliente,
                   a.valor_previsto,
                   a.data_prevista_devolucao,
                   car.tipo_categoria AS tipo_carro,
                   c.preco_diaria
            FROM Aluguel a
            JOIN Carro car ON a.placa = car.placa
            JOIN Categoria c ON car.tipo_categoria = c.tipo
            WHERE a.num_locacao = %s
        """
        resultado = db.execute_select_one(query, (num_locacao,))

        if not resultado:
            return jsonify({"erro": "Locação não encontrada"}), 404

        resp = {
            "num_locacao": resultado["num_locacao"],
            "placa": resultado.get("placa"),
            "cpf_cliente": resultado.get("cpf_cliente"),
            "valor_previsto": resultado.get("valor_previsto"),
            "data_prevista_devolucao": resultado.get("data_prevista_devolucao"),
            "tipo_carro": resultado.get("tipo_carro"),
            "preco_diaria": float(resultado["preco_diaria"]) if resultado.get("preco_diaria") is not None else None
        }
        return jsonify(resp), 200

    except Exception as e:
        return internal_error(str(e))


@aluguel_blueprint.route("/clientes/<cpf>/historico-multas", methods=["GET"])
def historico_multas_cliente(cpf):
    """Retorna histórico de multas de um cliente"""
    db = DatabaseManager()
    try:
        query = """
            SELECT m.*, a.num_locacao, a.data_retirada, c.nome as nome_carro
            FROM Multa m
            JOIN Pagamento p ON m.num_pagamento = p.num_pagamento
            JOIN Devolucao d ON d.num_pagamento = p.num_pagamento
            JOIN Aluguel a ON a.num_locacao = d.num_locacao
            JOIN Carro c ON a.placa = c.placa
            WHERE a.cpf_cliente = %s
            ORDER BY a.data_retirada DESC
        """
        multas = db.execute_select_all(query, (cpf,))
        return jsonify({"multas": multas}), 200
    except Exception as e:
        return internal_error(str(e))

# ROTAS DE LOCAÇÕES ABERTAS


@aluguel_blueprint.route("/locacoes-abertas", methods=["GET"])
def locacoes_abertas():
    """Retorna todas as locações ainda não finalizadas (sem devolução)."""
    db = DatabaseManager()
    try:
        query = """
            SELECT a.num_locacao, a.placa, a.cpf_cliente
            FROM Aluguel a
            LEFT JOIN Devolucao d ON a.num_locacao = d.num_locacao
            WHERE d.num_locacao IS NULL
            ORDER BY a.num_locacao ASC
        """

        locacoes = db.execute_select_all(query)

        return jsonify({"locacoes": locacoes}), 200

    except Exception as e:
        return internal_error(str(e))


@aluguel_blueprint.route("/locacao/<int:num_locacao>/data-prevista", methods=["GET"])
def obter_data_prevista(num_locacao):
    """Retorna a data prevista de devolução de uma locação"""
    db = DatabaseManager()
    try:
        query = """
            SELECT data_prevista_devolucao
            FROM Aluguel
            WHERE num_locacao = %s
        """

        resultado = db.execute_select_one(query, (num_locacao,))

        if not resultado:
            return jsonify({"erro": "Locação não encontrada"}), 404

        return jsonify({"data_prevista": resultado["data_prevista_devolucao"]}), 200

    except Exception as e:
        return internal_error(str(e))


@aluguel_blueprint.route("/pagamento/<int:num_pagamento>/gerar_qrcode", methods=["POST"])
def gerar_qrcode_pagamento(num_pagamento):
    """
    Cria um NOVO pagamento com forma_pix, gera QR e retorna dados.
    """
    db = DatabaseManager()
    try:
        pagamento = db.execute_select_one(
            "SELECT valor_total FROM Pagamento WHERE num_pagamento = %s",
            (num_pagamento,)
        )
        if not pagamento:
            return jsonify({"erro": "Pagamento original não encontrado"}), 404

        valor_total = float(pagamento['valor_total'])

        qr_code_url = (
            f"https://api.qrserver.com/v1/create-qr-code/?size=220x220"
            f"&data=Pagamento%20Locadora%20num_pagamento={num_pagamento}"
        )
        if hasattr(db, "conn") and db.conn:
            db.conn.commit()

        return jsonify({
            "mensagem": "QR Code PIX gerado com sucesso!",
            "num_pagamento": num_pagamento,
            "valor_total": valor_total,
            "forma_pagamento": "PIX",
            "qr_code_url": qr_code_url
        }), 200

    except Exception as e:
        return internal_error(f"Erro ao gerar QR Code: {str(e)}")
