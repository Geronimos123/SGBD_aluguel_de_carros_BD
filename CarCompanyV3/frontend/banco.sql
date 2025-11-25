DROP SCHEMA IF EXISTS aluguel CASCADE;
CREATE SCHEMA aluguel;
SET search_path TO aluguel;

CREATE TABLE Cliente (
    cpf CHAR(11) PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    endereco VARCHAR(200),
    telefone VARCHAR(20),
    CHECK (cpf ~ '^[0-9]{11}$')
);

-- ============================================
-- 2. FUNCIONARIO
-- ============================================
CREATE TABLE Funcionario (
    num_funcionario SERIAL PRIMARY KEY,
    cpf CHAR(11) UNIQUE NOT NULL,
    nome VARCHAR(100) NOT NULL,
    data_inicio DATE NOT NULL,
    endereco VARCHAR(200),
    telefone VARCHAR(20),
    qnt_vendas INTEGER DEFAULT 0,
    CHECK (cpf ~ '^[0-9]{11}$'),
    CHECK (qnt_vendas >= 0),
    CHECK (data_inicio <= CURRENT_DATE)
);

-- ============================================
-- 3. CATEGORIA
-- ============================================
CREATE TABLE Categoria (
    tipo VARCHAR(50) PRIMARY KEY,
    preco_diaria NUMERIC(10,2) NOT NULL,
    descricao TEXT,
    CHECK (preco_diaria >= 0)
);

-- ============================================
-- 4. CARRO
-- ============================================
CREATE TABLE Carro (
    placa VARCHAR(10) PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    chassi VARCHAR(50) UNIQUE NOT NULL,
    ano INTEGER NOT NULL,
    quilometragem INTEGER DEFAULT 0,
    tipo_categoria VARCHAR(50) NOT NULL,
    imagem_url VARCHAR(200),
    status_carro VARCHAR(20) DEFAULT 'DISPONIVEL',
    
    FOREIGN KEY (tipo_categoria) REFERENCES Categoria(tipo),
    
    -- Regex aceita Placa Antiga (AAA-1234) e Mercosul (ABC1D23)
    CHECK (UPPER(placa) ~ '^[A-Z]{3}[0-9][0-9A-Z][0-9]{2}$'),
    CHECK (ano > 1900),
    CHECK (quilometragem >= 0),
    CHECK (status_carro IN ('DISPONIVEL','ALUGADO','MANUTENCAO'))
);

-- ============================================
-- 5. MANUTENCAO
-- ============================================
CREATE TABLE Manutencao (
    num_manutencao SERIAL PRIMARY KEY,
    placa_carro VARCHAR(10) NOT NULL,
    cpf_mecanico CHAR(11),
    custo NUMERIC(10,2) NOT NULL,
    data_inicio DATE DEFAULT CURRENT_DATE,
    data_retorno DATE,
    descricao TEXT,
    
    FOREIGN KEY (placa_carro) REFERENCES Carro(placa),
    CHECK (custo >= 0),
    CHECK (cpf_mecanico IS NULL OR cpf_mecanico ~ '^[0-9]{11}$')
);

-- ============================================
-- 6. ACESSORIO
-- ============================================
CREATE TABLE Acessorio (
    tipo VARCHAR(50) PRIMARY KEY,
    preco_adicional NUMERIC(10,2) NOT NULL,
    CHECK (preco_adicional >= 0)
);

-- ============================================
-- 7. PAGAMENTO
-- (colocada antes de Aluguel para permitir FK)
-- ============================================
CREATE TABLE Pagamento (
    num_pagamento SERIAL PRIMARY KEY,
    valor_total NUMERIC(10,2) NOT NULL,
    forma_pagamento VARCHAR(50),
    CHECK (valor_total >= 0)
);

-- ============================================
-- 8. ALUGUEL
-- ============================================
CREATE TABLE Aluguel (
    num_locacao SERIAL PRIMARY KEY,
    data_retirada TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_prevista_devolucao TIMESTAMP NOT NULL,
    valor_previsto NUMERIC(10,2),
    num_funcionario INTEGER NOT NULL,
    placa VARCHAR(10) NOT NULL,
    cpf_cliente CHAR(11) NOT NULL,
    seguro_contratado BOOLEAN DEFAULT FALSE,
    num_pagamento INTEGER,
    
    FOREIGN KEY (num_pagamento) REFERENCES Pagamento(num_pagamento),
    FOREIGN KEY (num_funcionario) REFERENCES Funcionario(num_funcionario),
    FOREIGN KEY (placa) REFERENCES Carro(placa),
    
    CHECK (valor_previsto IS NULL OR valor_previsto >= 0),
    CHECK (data_prevista_devolucao > data_retirada)
);

-- ============================================
-- 9. ALUGUEL_ACESSORIO
-- ============================================
CREATE TABLE Aluguel_Acessorio (
    num_locacao INTEGER NOT NULL,
    tipo_acessorio VARCHAR(50) NOT NULL,
    PRIMARY KEY (num_locacao, tipo_acessorio),
    FOREIGN KEY (num_locacao) REFERENCES Aluguel(num_locacao),
    FOREIGN KEY (tipo_acessorio) REFERENCES Acessorio(tipo)
);

-- ============================================
-- 10. MULTA
-- ============================================
CREATE TABLE Multa (
    id_multa SERIAL PRIMARY KEY,
    num_pagamento INTEGER NOT NULL,
    tipo_multa VARCHAR(100) NOT NULL,
    valor NUMERIC(10,2) NOT NULL,
    
    FOREIGN KEY (num_pagamento) REFERENCES Pagamento(num_pagamento),
    CHECK (valor >= 0)
);

-- ============================================
-- 11. DESCONTO
-- ============================================
CREATE TABLE Desconto (
    id_desconto SERIAL PRIMARY KEY,
    num_pagamento INTEGER NOT NULL,
    tipo_desconto VARCHAR(100) NOT NULL,
    valor NUMERIC(10,2) NOT NULL,
    flag_ativo BOOLEAN NOT NULL DEFAULT TRUE,
    
    FOREIGN KEY (num_pagamento) REFERENCES Pagamento(num_pagamento),
    CHECK (valor >= 0)
);

-- ============================================
-- 12. DEVOLUCAO
-- ============================================
CREATE TABLE Devolucao (
    num_locacao INTEGER PRIMARY KEY,
    num_pagamento INTEGER NOT NULL,
    data_real_devolucao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    combustivel_completo BOOLEAN NOT NULL,
    estado_carro VARCHAR(200),
    
    FOREIGN KEY (num_locacao) REFERENCES Aluguel(num_locacao),
    FOREIGN KEY (num_pagamento) REFERENCES Pagamento(num_pagamento)
);

-- ============================================
-- 13. HISTORICO ALUGUEL
-- ============================================
CREATE TABLE HistoricoAluguel (
    id_historico SERIAL PRIMARY KEY,
    num_locacao INTEGER NOT NULL,
    cpf CHAR(11) NOT NULL,
    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (num_locacao) REFERENCES Aluguel(num_locacao),
    FOREIGN KEY (cpf) REFERENCES Cliente(cpf),
    CHECK (cpf ~ '^[0-9]{11}$')
);

SET search_path TO aluguel;

-- ============================================
-- 1. CATEGORIA (Tipos fixos)
-- ============================================
INSERT INTO Categoria (tipo, preco_diaria, descricao) VALUES 
('Economico', 100.00, 'Carros compactos, baixo consumo, ideais para cidade.'),
('Intermediario', 180.00, 'Sedans confortáveis com porta-malas amplo.'),
('SUV', 280.00, 'Altura elevada, motor potente e espaço para família.');

-- ============================================
-- 2. ACESSORIO (Tipos fixos)
-- ============================================
INSERT INTO Acessorio (tipo, preco_adicional) VALUES 
('GPS', 15.00),
('Cadeirinha', 20.00),
('Condutor Adicional', 30.00),
('Seguro Vidros', 10.00),
('Porta-Bike', 25.00);

-- ============================================
-- 3. FUNCIONARIO (25 Registros)
-- Padrão CPF: 100000000XX
-- ============================================
INSERT INTO Funcionario (cpf, nome, data_inicio, endereco, telefone, qnt_vendas) VALUES
('10000000001', 'Carlos Gerente', '2023-01-01', 'Rua A, 1', '11900000001', 50),
('10000000002', 'Ana Vendedora', '2023-02-01', 'Rua B, 2', '11900000002', 30),
('10000000003', 'Pedro Atendente', '2023-03-01', 'Rua C, 3', '11900000003', 10),
('10000000004', 'Mariana Silva', '2023-04-01', 'Rua D, 4', '11900000004', 15),
('10000000005', 'João Souza', '2023-05-01', 'Rua E, 5', '11900000005', 20),
('10000000006', 'Fernanda Lima', '2023-06-01', 'Rua F, 6', '11900000006', 25),
('10000000007', 'Ricardo Gomes', '2023-07-01', 'Rua G, 7', '11900000007', 5),
('10000000008', 'Patrícia Dias', '2023-08-01', 'Rua H, 8', '11900000008', 8),
('10000000009', 'Lucas Martins', '2023-09-01', 'Rua I, 9', '11900000009', 12),
('10000000010', 'Juliana Costa', '2023-10-01', 'Rua J, 10', '11900000010', 18),
('10000000011', 'Roberto Alves', '2023-11-01', 'Rua K, 11', '11900000011', 22),
('10000000012', 'Camila Rocha', '2023-12-01', 'Rua L, 12', '11900000012', 40),
('10000000013', 'Gustavo Santos', '2024-01-01', 'Rua M, 13', '11900000013', 2),
('10000000014', 'Vanessa Melo', '2024-02-01', 'Rua N, 14', '11900000014', 6),
('10000000015', 'Bruno Carvalho', '2024-03-01', 'Rua O, 15', '11900000015', 9),
('10000000016', 'Aline Ferreira', '2024-04-01', 'Rua P, 16', '11900000016', 14),
('10000000017', 'Felipe Barbosa', '2024-05-01', 'Rua Q, 17', '11900000017', 19),
('10000000018', 'Tatiane Ribeiro', '2024-06-01', 'Rua R, 18', '11900000018', 21),
('10000000019', 'Diego Araujo', '2024-07-01', 'Rua S, 19', '11900000019', 3),
('10000000020', 'Larissa Cunha', '2024-08-01', 'Rua T, 20', '11900000020', 7),
('10000000021', 'Rodrigo Nogueira', '2024-09-01', 'Rua U, 21', '11900000021', 11),
('10000000022', 'Bianca Cardoso', '2024-10-01', 'Rua V, 22', '11900000022', 16),
('10000000023', 'Marcelo Teixeira', '2024-11-01', 'Rua W, 23', '11900000023', 23),
('10000000024', 'Renata Mendes', '2024-12-01', 'Rua X, 24', '11900000024', 4),
('10000000025', 'Thiago Castro', '2025-01-01', 'Rua Y, 25', '11900000025', 0);

-- ============================================
-- 4. CLIENTE (25 Registros)
-- Padrão CPF: 111111111XX
-- ============================================
INSERT INTO Cliente (cpf, nome, endereco, telefone) VALUES
('11111111101', 'Cliente Alpha', 'Av Brasil, 100', '11988880001'),
('11111111102', 'Cliente Beta', 'Av Brasil, 200', '11988880002'),
('11111111103', 'Cliente Gama', 'Av Brasil, 300', '11988880003'),
('11111111104', 'João da Silva', 'Rua 1, 10', '11988880004'),
('11111111105', 'Maria Oliveira', 'Rua 2, 20', '11988880005'),
('11111111106', 'José Santos', 'Rua 3, 30', '11988880006'),
('11111111107', 'Ana Pereira', 'Rua 4, 40', '11988880007'),
('11111111108', 'Carlos Souza', 'Rua 5, 50', '11988880008'),
('11111111109', 'Paula Lima', 'Rua 6, 60', '11988880009'),
('11111111110', 'Marcos Costa', 'Rua 7, 70', '11988880010'),
('11111111111', 'Fernanda Rocha', 'Rua 8, 80', '11988880011'),
('11111111112', 'Lucas Alves', 'Rua 9, 90', '11988880012'),
('11111111113', 'Juliana Dias', 'Rua 10, 100', '11988880013'),
('11111111114', 'Ricardo Martins', 'Rua 11, 110', '11988880014'),
('11111111115', 'Patrícia Gomes', 'Rua 12, 120', '11988880015'),
('11111111116', 'Gabriel Ferreira', 'Rua 13, 130', '11988880016'),
('11111111117', 'Amanda Barbosa', 'Rua 14, 140', '11988880017'),
('11111111118', 'Rafael Ribeiro', 'Rua 15, 150', '11988880018'),
('11111111119', 'Beatriz Araujo', 'Rua 16, 160', '11988880019'),
('11111111120', 'Thiago Cunha', 'Rua 17, 170', '11988880020'),
('11111111121', 'Larissa Nogueira', 'Rua 18, 180', '11988880021'),
('11111111122', 'Felipe Cardoso', 'Rua 19, 190', '11988880022'),
('11111111123', 'Camila Teixeira', 'Rua 20, 200', '11988880023'),
('11111111124', 'Gustavo Mendes', 'Rua 21, 210', '11988880024'),
('11111111125', 'Vanessa Castro', 'Rua 22, 220', '11988880025');

-- ============================================
-- 5. CARRO (25 Registros)
-- 10 Mobis (Econ), 10 Compass (SUV), 5 BMWs (Economico)
-- Alguns em Manutenção, Alguns Alugados
-- ============================================

-- 10 Carros Economicos (Disponíveis)
INSERT INTO Carro (placa, nome, chassi, ano, quilometragem, tipo_categoria, imagem_url, status_carro) VALUES
('ECO0001', 'HB20', 'CHASSIE01', 2022, 15000, 'Economico', 'hb20.png', 'DISPONIVEL'),
('ECO0002', 'HB20', 'CHASSIE02', 2022, 16000, 'Economico', 'hb20.png', 'DISPONIVEL'),
('ECO0003', 'HB20', 'CHASSIE03', 2023, 5000, 'Economico', 'hb20.png', 'DISPONIVEL'),
('ECO0004', 'HB20', 'CHASSIE04', 2023, 6000, 'Economico', 'hb20.png', 'DISPONIVEL'),
('ECO0005', 'HB20', 'CHASSIE05', 2023, 7000, 'Economico', 'hb20.png', 'DISPONIVEL'),
('ECO0006', 'HB20', 'CHASSIE06', 2023, 8000, 'Economico', 'hb20.png', 'DISPONIVEL'),
('ECO0007', 'HB20', 'CHASSIE07', 2024, 1000, 'Economico', 'hb20.png', 'DISPONIVEL'),
('ECO0008', 'HB20', 'CHASSIE08', 2024, 2000, 'Economico', 'hb20.png', 'DISPONIVEL'),
('ECO0009', 'HB20', 'CHASSIE09', 2024, 3000, 'Economico', 'hb20.png', 'DISPONIVEL'),
('ECO0010', 'HB20', 'CHASSIE10', 2024, 4000, 'Economico', 'hb20.png', 'ALUGADO'); -- Teste Indisponivel

-- 10 SUVs (Misturados Disponivel e Manutenção)
INSERT INTO Carro (placa, nome, chassi, ano, quilometragem, tipo_categoria, imagem_url, status_carro) VALUES
('SUV0001', 'Creta', 'CHASSIS01', 2023, 12000, 'SUV', 'creta.png', 'DISPONIVEL'),
('SUV0002', 'Creta', 'CHASSIS02', 2023, 13000, 'SUV', 'creta.png', 'DISPONIVEL'),
('SUV0003', 'Creta', 'CHASSIS03', 2023, 14000, 'SUV', 'creta.png', 'DISPONIVEL'),
('SUV0004', 'Creta', 'CHASSIS04', 2023, 15000, 'SUV', 'creta.png', 'DISPONIVEL'),
('SUV0005', 'Creta', 'CHASSIS05', 2023, 16000, 'SUV', 'creta.png', 'ALUGADO'),
('SUV0006', 'Creta', 'CHASSIS06', 2024, 1000, 'SUV', 'creta.png', 'MANUTENCAO'), -- Teste Manutenção
('SUV0007', 'Creta', 'CHASSIS07', 2024, 2000, 'SUV', 'creta.png', 'MANUTENCAO'),
('SUV0008', 'Creta', 'CHASSIS08', 2024, 3000, 'SUV', 'creta.png', 'DISPONIVEL'),
('SUV0009', 'Creta', 'CHASSIS09', 2024, 4000, 'SUV', 'creta.png', 'DISPONIVEL'),
('SUV0010', 'Creta', 'CHASSIS10', 2024, 5000, 'SUV', 'creta.png', 'DISPONIVEL');

-- 5 Economico (Maioria Alugada ou Manutenção para gerar escassez)
INSERT INTO Carro (placa, nome, chassi, ano, quilometragem, tipo_categoria, imagem_url, status_carro) VALUES
('LUX0001', 'Argo', 'CHASSIL01', 2023, 8000, 'Economico', 'argo.png', 'ALUGADO'),
('LUX0002', 'Argo', 'CHASSIL02', 2023, 9000, 'Economico', 'argo.png', 'ALUGADO'),
('LUX0003', 'Argo', 'CHASSIL03', 2024, 1000, 'Economico', 'argo.png', 'DISPONIVEL'),
('LUX0004', 'Argo', 'CHASSIL04', 2024, 2000, 'Economico', 'argo.png', 'MANUTENCAO'),
('LUX0005', 'Argo', 'CHASSIL05', 2024, 3000, 'Economico', 'argo.png', 'DISPONIVEL');

INSERT INTO Carro (placa, nome, chassi, ano, quilometragem, tipo_categoria, imagem_url, status_carro) VALUES
('ONX0001', 'Onix', 'CHASSIO01', 2023, 8000, 'Economico', 'onix.png', 'ALUGADO'),
('ONX0002', 'Onix', 'CHASSIO02', 2023, 9000, 'Economico', 'onix.png', 'ALUGADO'),
('ONX0003', 'Onix', 'CHASSIO03', 2024, 1000, 'Economico', 'onix.png', 'DISPONIVEL'),
('ONX0004', 'Onix', 'CHASSIO04', 2024, 2000, 'Economico', 'onix.png', 'MANUTENCAO'),
('ONX0005', 'Onix', 'CHASSIO05', 2024, 3000, 'Economico', 'onix.png', 'DISPONIVEL');

-- ============================================
-- 6. MANUTENCAO (25 Registros)
-- Histórico de manutenções passadas
-- ============================================
INSERT INTO Manutencao (placa_carro, custo, data_inicio, data_retorno, descricao) VALUES
('ECO0001', 200.00, '2024-01-10', '2024-01-12', 'Troca de Óleo'),
('ECO0002', 250.00, '2024-02-15', '2024-02-16', 'Alinhamento'),
('ECO0003', 300.00, '2024-03-20', '2024-03-22', 'Revisão Geral'),
('ECO0004', 150.00, '2024-01-05', '2024-01-06', 'Troca de Pastilha'),
('ECO0005', 500.00, '2024-04-10', '2024-04-15', 'Funilaria Leve'),
('ECO0006', 200.00, '2024-05-01', '2024-05-02', 'Troca de Óleo'),
('ECO0007', 220.00, '2024-06-10', '2024-06-11', 'Balanceamento'),
('ECO0008', 180.00, '2024-07-20', '2024-07-21', 'Higienização'),
('ECO0009', 200.00, '2024-08-15', '2024-08-16', 'Troca de Óleo'),
('ECO0010', 350.00, '2024-09-01', '2024-09-03', 'Troca de Pneus'),
('SUV0001', 400.00, '2024-01-10', '2024-01-12', 'Revisão Freios'),
('SUV0002', 450.00, '2024-02-20', '2024-02-22', 'Troca de Amortecedor'),
('SUV0003', 300.00, '2024-03-15', '2024-03-16', 'Troca de Óleo'),
('SUV0004', 250.00, '2024-04-05', '2024-04-06', 'Alinhamento'),
('SUV0005', 600.00, '2024-05-10', '2024-05-15', 'Reparo Câmbio'),
('SUV0006', 0.00, CURRENT_DATE, NULL, 'Em Andamento - Motor'), -- Manutenção Atual
('SUV0007', 0.00, CURRENT_DATE, NULL, 'Em Andamento - Elétrica'), -- Manutenção Atual
('SUV0008', 300.00, '2024-08-20', '2024-08-21', 'Troca de Óleo'),
('SUV0009', 400.00, '2024-09-10', '2024-09-12', 'Revisão 10k'),
('SUV0010', 350.00, '2024-10-05', '2024-10-06', 'Troca de Pastilha'),
('LUX0001', 800.00, '2024-01-15', '2024-01-18', 'Revisão Completa'),
('LUX0002', 900.00, '2024-02-20', '2024-02-25', 'Reparo Ar Condicionado'),
('LUX0003', 700.00, '2024-03-10', '2024-03-12', 'Polimento Cristalizado'),
('LUX0004', 0.00, CURRENT_DATE, NULL, 'Em Andamento - Suspensão'), -- Manutenção Atual
('LUX0005', 750.00, '2024-05-05', '2024-05-08', 'Revisão Geral');

-- ============================================
-- 7. ALUGUEL (25 Registros)
-- IDs 1 a 20: Aluguéis Passados (Finalizados)
-- IDs 21 a 25: Aluguéis Ativos (Sem devolução ainda)
-- ============================================

-- Aluguéis Finalizados (Passados)
INSERT INTO Aluguel (data_retirada, data_prevista_devolucao, valor_previsto, num_funcionario, placa, cpf_cliente, seguro_contratado) VALUES
('2024-01-01 10:00', '2024-01-05 10:00', 500.00, 1, 'ECO0001', '11111111101', TRUE),
('2024-02-01 10:00', '2024-02-03 10:00', 200.00, 2, 'ECO0002', '11111111102', FALSE),
('2024-03-01 10:00', '2024-03-05 10:00', 1120.00, 3, 'SUV0001', '11111111103', TRUE), -- SUV 280 * 4 dias
('2024-04-01 10:00', '2024-04-02 10:00', 550.00, 4, 'LUX0001', '11111111104', TRUE),
('2024-05-01 08:00', '2024-05-05 08:00', 400.00, 5, 'ECO0003', '11111111105', FALSE),
('2024-06-01 09:00', '2024-06-04 09:00', 840.00, 6, 'SUV0002', '11111111106', TRUE),
('2024-07-01 10:00', '2024-07-03 10:00', 200.00, 7, 'ECO0004', '11111111107', FALSE),
('2024-08-01 10:00', '2024-08-02 10:00', 100.00, 8, 'ECO0005', '11111111108', FALSE),
('2024-09-01 10:00', '2024-09-10 10:00', 2520.00, 9, 'SUV0003', '11111111109', TRUE), -- Longa duração
('2024-10-01 10:00', '2024-10-05 10:00', 2200.00, 10, 'LUX0002', '11111111110', TRUE),
('2024-11-01 10:00', '2024-11-02 10:00', 100.00, 11, 'ECO0006', '11111111111', FALSE),
('2024-12-01 10:00', '2024-12-03 10:00', 560.00, 12, 'SUV0004', '11111111112', TRUE),
('2024-01-15 10:00', '2024-01-20 10:00', 500.00, 13, 'ECO0007', '11111111113', TRUE),
('2024-02-15 10:00', '2024-02-17 10:00', 200.00, 14, 'ECO0008', '11111111114', FALSE),
('2024-03-15 10:00', '2024-03-18 10:00', 840.00, 15, 'SUV0008', '11111111115', TRUE),
('2024-04-15 10:00', '2024-04-16 10:00', 100.00, 16, 'ECO0009', '11111111116', FALSE),
('2024-05-15 10:00', '2024-05-20 10:00', 2750.00, 17, 'LUX0003', '11111111117', TRUE),
('2024-06-15 10:00', '2024-06-17 10:00', 560.00, 18, 'SUV0009', '11111111118', TRUE),
('2024-07-15 10:00', '2024-07-20 10:00', 500.00, 19, 'ECO0001', '11111111119', TRUE), -- Reuso de carro
('2024-08-15 10:00', '2024-08-18 10:00', 300.00, 20, 'ECO0002', '11111111120', FALSE);

-- Aluguéis EM ABERTO (Carros marcados como ALUGADO acima)
-- Data retirada = Hoje ou ontem
INSERT INTO Aluguel (data_retirada, data_prevista_devolucao, valor_previsto, num_funcionario, placa, cpf_cliente, seguro_contratado) VALUES
(CURRENT_TIMESTAMP - INTERVAL '1 day', CURRENT_TIMESTAMP + INTERVAL '2 days', 300.00, 21, 'ECO0010', '11111111121', TRUE),
(CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP + INTERVAL '1 day', 840.00, 22, 'SUV0005', '11111111122', TRUE),
(CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '3 days', 1650.00, 23, 'LUX0001', '11111111123', TRUE),
(CURRENT_TIMESTAMP - INTERVAL '1 hour', CURRENT_TIMESTAMP + INTERVAL '1 day', 550.00, 24, 'LUX0002', '11111111124', TRUE),
(CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '5 days', 500.00, 25, 'ECO0003', '11111111125', FALSE);

-- ============================================
-- 8. PAGAMENTO (20 Registros - Só para os finalizados)
-- ============================================
INSERT INTO Pagamento (valor_total, forma_pagamento) VALUES
(500.00, 'Cartao Credito'), -- 1
(200.00, 'Pix'),            -- 2
(1120.00, 'Cartao Credito'),-- 3
(550.00, 'Dinheiro'),       -- 4
(400.00, 'Cartao Debito'),  -- 5
(840.00, 'Pix'),            -- 6
(250.00, 'Cartao Credito'), -- 7 (Teve multa, valor maior que previsto)
(100.00, 'Pix'),            -- 8
(2520.00, 'Cartao Credito'),-- 9
(2200.00, 'Cartao Credito'),-- 10
(100.00, 'Dinheiro'),       -- 11
(560.00, 'Pix'),            -- 12
(500.00, 'Cartao Credito'), -- 13
(200.00, 'Pix'),            -- 14
(840.00, 'Cartao Credito'), -- 15
(100.00, 'Dinheiro'),       -- 16
(2750.00, 'Cartao Credito'),-- 17
(560.00, 'Pix'),            -- 18
(650.00, 'Cartao Credito'), -- 19 (Multa alta)
(300.00, 'Pix');            -- 20

-- ============================================
-- 9. DEVOLUCAO (20 Registros - Finalizados)
-- ============================================
INSERT INTO Devolucao (num_locacao, num_pagamento, combustivel_completo, estado_carro, data_real_devolucao) VALUES
(1, 1, TRUE, 'OK', '2024-01-05 10:00'),
(2, 2, TRUE, 'OK', '2024-02-03 10:00'),
(3, 3, TRUE, 'OK', '2024-03-05 10:00'),
(4, 4, TRUE, 'OK', '2024-04-02 10:00'),
(5, 5, TRUE, 'OK', '2024-05-05 08:00'),
(6, 6, TRUE, 'OK', '2024-06-04 09:00'),
(7, 7, FALSE, 'OK', '2024-07-03 10:00'), -- Tanque Vazio (Gera Multa)
(8, 8, TRUE, 'OK', '2024-08-02 10:00'),
(9, 9, TRUE, 'OK', '2024-09-10 10:00'),
(10, 10, TRUE, 'OK', '2024-10-05 10:00'),
(11, 11, TRUE, 'OK', '2024-11-02 10:00'),
(12, 12, TRUE, 'OK', '2024-12-03 10:00'),
(13, 13, TRUE, 'OK', '2024-01-20 10:00'),
(14, 14, TRUE, 'OK', '2024-02-17 10:00'),
(15, 15, TRUE, 'OK', '2024-03-18 10:00'),
(16, 16, TRUE, 'OK', '2024-04-16 10:00'),
(17, 17, TRUE, 'OK', '2024-05-20 10:00'),
(18, 18, TRUE, 'OK', '2024-06-17 10:00'),
(19, 19, TRUE, 'MANUTENCAO', '2024-07-20 10:00'), -- Avaria (Gera Multa)
(20, 20, TRUE, 'OK', '2024-08-18 10:00');

-- ============================================
-- 10. MULTA (Associada a Pagamentos)
-- ============================================
INSERT INTO Multa (num_pagamento, tipo_multa, valor) VALUES
(7, 'Combustivel Incompleto', 50.00), -- Associado ao pagamento 7 (Locação 7)
(19, 'Dano Lataria', 150.00);        -- Associado ao pagamento 19 (Locação 19)

-- ============================================
-- 11. DESCONTO (Associada a Pagamentos)
-- ============================================
INSERT INTO Desconto (num_pagamento, tipo_desconto, valor, flag_ativo) VALUES
(9, 'Fidelidade', 100.00, TRUE),   -- Locação Longa
(17, 'Promocao Economico', 200.00, TRUE);

-- ============================================
-- 12. ALUGUEL_ACESSORIO (Mix aleatório)
-- ============================================
INSERT INTO Aluguel_Acessorio (num_locacao, tipo_acessorio) VALUES
(1, 'GPS'),
(1, 'Cadeirinha'), -- Locação 1 levou 2 itens
(3, 'GPS'),
(3, 'Seguro Vidros'),
(6, 'Cadeirinha'),
(9, 'Condutor Adicional'),
(10, 'GPS'),
(12, 'Porta-Bike'),
(15, 'GPS'),
(17, 'Condutor Adicional'),
(21, 'GPS'),       -- Locação Aberta com acessorio
(22, 'Cadeirinha');

-- ============================================
-- 13. HISTORICO ALUGUEL (Espelho dos Alugueis)
-- ============================================
INSERT INTO HistoricoAluguel (num_locacao, cpf) 
SELECT num_locacao, cpf_cliente FROM Aluguel;
