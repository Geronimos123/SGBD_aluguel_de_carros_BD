# relatorio_rota.py
from flask import Blueprint, request, Response, jsonify, current_app
from datetime import datetime
import csv
import io
import traceback

from database.conector import DatabaseManager  # usa seu conector existente

relatorio_bp = Blueprint("relatorios", __name__)


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


@relatorio_bp.route("/relatorios/vendas", methods=["POST", "OPTIONS"])
def gerar_relatorio_vendas():
    # Preflight CORS
    if request.method == "OPTIONS":
        return ("", 200, {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept",
        })

    try:
        payload = request.get_json(silent=True) or {}
        data_min = payload.get("data_min")
        data_max = payload.get("data_max")

        current_app.logger.info(
            f"Gerar relatório: {data_min} - {data_max} (method=POST)")

        if not data_min or not data_max:
            return jsonify({"erro": "Campos 'data_min' e 'data_max' são obrigatórios."}), 400

        # valida e transforma para garantir ordem correta
        dt_min = parse_date(data_min)
        dt_max = parse_date(data_max)

        if dt_min > dt_max:
            return jsonify({"erro": "data_min não pode ser maior que data_max."}), 400

        # Query — utiliza placeholders %s e passa params
        sql = """
            SELECT *
            FROM aluguel
            WHERE data_retirada::date >= %s
              AND data_retirada::date <= %s
            ORDER BY data_retirada;
        """
        params = (data_min, data_max)

        # Usa seu DatabaseManager (que já abre conn e cursor no __init__)
        db = DatabaseManager()
        try:
            rows_dicts = db.execute_select_all(
                sql, params)  # retorna lista de dicts
        except Exception as e:
            current_app.logger.exception("Erro ao executar select_all: %s", e)
            return jsonify({"erro": "Erro ao consultar banco de dados.", "detalhes": str(e)}), 500

        # Normaliza resultados: extrair colunas (ordem) e transformar rows em tuplas
        columns = []
        rows = []
        if rows_dicts:
            # manter a ordem das chaves conforme o primeiro dict
            first = rows_dicts[0]
            # psycopg2 DictCursor mantém as chaves na ordem das colunas da query
            columns = list(first.keys())
            for d in rows_dicts:
                rows.append(tuple(d.get(col) for col in columns))

        # Gera CSV em memória
        output = io.StringIO()
        writer = csv.writer(output)

        if columns:
            writer.writerow(columns)
        else:
            # se não houver linhas, escrever cabeçalho vazio (ou nada)
            writer.writerow([])

        for r in rows:
            cleaned = []
            for v in r:
                if v is None:
                    cleaned.append("")
                else:
                    if hasattr(v, "isoformat"):
                        cleaned.append(v.isoformat())
                    else:
                        cleaned.append(str(v))
            writer.writerow(cleaned)

        csv_content = output.getvalue()
        output.close()

        filename = f"vendas_{data_min.replace('-', '')}_{data_max.replace('-', '')}.csv"
        headers = {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Access-Control-Allow-Origin": "*"
        }

        return Response(csv_content, headers=headers)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno ao gerar relatório.", "detalhes": str(e)}), 500
