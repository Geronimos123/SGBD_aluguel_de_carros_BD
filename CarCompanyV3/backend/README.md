Como Rodar o Projeto:

1. Clone o repositório:
git clone https://github.com/Geronimos123/SGBD_aluguel_de_carros_BDI.git

2. Navegue até a pasta de backend do projeto:
cd CarCompanyV3
cd backend

3. Instale as dependências com o comando:
"pip install -r requirements.txt"

4. Crie o servidor no PostGreSQL usando os seguintes dados:
- Nome do Server: "carcompany"
- Usuário: "postgres"
- Host: "127.0.0.1"
- Senha: "{Sua Senha do PostGreSQL}"
- Porta: "5432"

- Altere a senha e o usuário no arquivo connector.py para a sua senha e usuário do PostGreSQL

- Crie um banco de dados chamado "carcompany"
- Copie e Execute o Arquivo banco.sql no PostGreSQL

5. Inicie o servidor ainda estando na pasta backend:
python app.py

6. Execute o Frontend:
- Navegue até a pasta frontend do projeto:
cd ..
cd frontend

- Execute o comando "index.html"