// js/alugar.js - CORRIGIDO
class AluguelForm {
    constructor() {
        this.form = document.getElementById('form-aluguel');
        this.init();
    }

    async init() {
        try {
            await this.carregarFuncionarios();
            await this.carregarCarrosDisponiveis();
            this.configurarEventos();
        } catch (error) {
            console.error('Erro na inicialização:', error);
            showError('Erro ao carregar dados iniciais.');
        }
    }

    async carregarFuncionarios() {
        const selectFunc = document.getElementById('func');
        try {
            const funcData = await apiFetch('/funcionarios');
            const funcionarios = funcData.funcionarios || [];
            
            selectFunc.innerHTML = '<option value="">Selecione o funcionário...</option>';
            
            funcionarios.forEach(f => {
                const opt = document.createElement('option');
                opt.value = f.num_funcionario;
                opt.textContent = `${f.nome} (ID: ${f.num_funcionario})`;
                selectFunc.appendChild(opt);
            });
        } catch (error) {
            console.error('Erro ao carregar funcionários:', error);
            selectFunc.innerHTML = '<option value="">Erro ao carregar funcionários</option>';
        }
    }

    async carregarCarrosDisponiveis() {
        const selectCarro = document.getElementById('carro');
        try {
            const carrosData = await apiFetch('/carros/disponiveis');
            const carros = carrosData.carros || [];
            
            selectCarro.innerHTML = '<option value="">Selecione o carro...</option>';
            
            carros.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.placa;
                opt.textContent = `${c.nome} - ${c.tipo_categoria} (${formatCurrency(c.preco)}/dia)`;
                opt.dataset.preco = c.preco;
                selectCarro.appendChild(opt);
            });
        } catch (error) {
            console.error('Erro ao carregar carros:', error);
            selectCarro.innerHTML = '<option value="">Erro ao carregar carros</option>';
        }
    }

    configurarEventos() {
        // Quando selecionar carro, preencher placa e calcular valor
        document.getElementById('carro').addEventListener('change', (e) => {
            const selectedOption = e.target.options[e.target.selectedIndex];
            document.getElementById('placa').value = selectedOption.value;
            this.calcularValorPrevisto();
        });

        // Quando mudar datas, recalcular valor
        document.getElementById('data-retirada').addEventListener('change', () => this.calcularValorPrevisto());
        document.getElementById('data-devolucao').addEventListener('change', () => this.calcularValorPrevisto());
        document.getElementById('seguro').addEventListener('change', () => this.calcularValorPrevisto());

        // Submissão do formulário
        this.form.addEventListener('submit', (e) => this.enviarFormulario(e));
    }

    calcularValorPrevisto() {
        const carroSelect = document.getElementById('carro');
        const dataRetirada = document.getElementById('data-retirada').value;
        const dataDevolucao = document.getElementById('data-devolucao').value;
        const seguro = document.getElementById('seguro').checked;

        if (!carroSelect.value || !dataRetirada || !dataDevolucao) {
            document.getElementById('valor-previsto').textContent = 'R$ 0,00';
            return;
        }

        const precoDiaria = parseFloat(carroSelect.options[carroSelect.selectedIndex].dataset.preco || 0);
        
        // Calcular dias
        const inicio = new Date(dataRetirada);
        const fim = new Date(dataDevolucao);
        const dias = Math.max(1, Math.ceil((fim - inicio) / (1000 * 60 * 60 * 24)));
        
        let valor = precoDiaria * dias;
        if (seguro) {
            valor *= 1.2; // +20% para seguro
        }

        document.getElementById('valor-previsto').textContent = formatCurrency(valor);
    }

    async enviarFormulario(e) {
        e.preventDefault();
        
        const formData = {
            placa: document.getElementById('placa').value,
            cpf_cliente: document.getElementById('cpf-cliente').value.replace(/\D/g, ''), // Remove não números
            num_funcionario: parseInt(document.getElementById('func').value),
            data_retirada: document.getElementById('data-retirada').value,
            data_prevista_devolucao: document.getElementById('data-devolucao').value,
            seguro_contratado: document.getElementById('seguro').checked,
            valor_previsto: document.getElementById('valor-previsto').textContent
        };

        // Validações
        if (!this.validarFormulario(formData)) {
            return;
        }

        const btnSubmit = this.form.querySelector('button[type="submit"]');
        btnSubmit.disabled = true;
        btnSubmit.textContent = 'PROCESSANDO...';

        try {
            const resultado = await apiFetch('/aluguel', {
                method: 'POST',
                body: formData
            });

            showError(`Aluguel criado com sucesso! Número: ${resultado.num_locacao}`);
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);

        } catch (error) {
            console.error('Erro ao criar aluguel:', error);
            showError(error.message || 'Erro ao criar aluguel.');
            btnSubmit.disabled = false;
            btnSubmit.textContent = 'CONFIRMAR ALUGUEL';
        }
    }

    validarFormulario(data) {
        const erros = [];

        if (!data.placa) erros.push('Selecione um carro');
        if (!data.cpf_cliente || data.cpf_cliente.length !== 11) erros.push('CPF deve ter 11 dígitos');
        if (!data.num_funcionario) erros.push('Selecione um funcionário');
        if (!data.data_retirada) erros.push('Informe a data de retirada');
        if (!data.data_prevista_devolucao) erros.push('Informe a data de devolução');

        const inicio = new Date(data.data_retirada);
        const fim = new Date(data.data_prevista_devolucao);
        if (fim <= inicio) erros.push('Data de devolução deve ser posterior à data de retirada');

        if (erros.length > 0) {
            showError('Corrija os seguintes erros:\n• ' + erros.join('\n• '));
            return false;
        }

        return true;
    }
}

// Inicializar quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', () => {
    new AluguelForm();
    
    // Configurar data mínima como hoje
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('data-retirada').min = today;
    document.getElementById('data-devolucao').min = today;
});