from flask import Flask
from flask_cors import CORS

from carros_rota import carros_blueprint
from aluguel_rota import aluguel_blueprint
from clientes_rota import clientes_blueprint
from funcionarios_rota import funcionarios_blueprint
from relatorio_rota import relatorio_bp

app = Flask(__name__)
CORS(app)
CORS(app, resources={r"*": {"origins": "*"}})

# registra as rotas
app.register_blueprint(carros_blueprint)
app.register_blueprint(aluguel_blueprint)
app.register_blueprint(clientes_blueprint)
app.register_blueprint(funcionarios_blueprint)
app.register_blueprint(relatorio_bp)


@app.route("/")
def home():
    return "API Locadora de Carros ativa!"


if __name__ == "__main__":
    app.run(debug=True)
