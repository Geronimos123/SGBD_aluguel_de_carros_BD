// js/devolucao.js (versão corrigida e mais robusta)

async function carregarOpcoes() {
    // 🔹 1. Preencher ESTADOS DO CARRO
    const estados = ["OK", "MANUTENCAO"];
    const selectEstado = document.getElementById("selectEstado");
    if (selectEstado) {
        selectEstado.innerHTML = "<option value=''>Selecione...</option>";
        estados.forEach(estado => {
            const option = document.createElement("option");
            option.value = estado;
            option.textContent = estado;
            selectEstado.appendChild(option);
        });
    } else console.warn("selectEstado não encontrado no DOM");

    // 🔹 2. Preencher COMBUSTÍVEL
    const selectComb = document.getElementById("selectCombustivel");
    if (selectComb) {
        selectComb.innerHTML = "<option value=''>Selecione...</option>";
        const combustiveis = [
            { valor: "true", texto: "Sim" },
            { valor: "false", texto: "Não" }
        ];
        combustiveis.forEach(item => {
            const option = document.createElement("option");
            option.value = item.valor;
            option.textContent = item.texto;
            selectComb.appendChild(option);
        });
    } else console.warn("selectCombustivel não encontrado no DOM");

    // 🔹 3. Buscar LOCAÇÕES abertas no backend
    try {
        const response = await fetch("http://127.0.0.1:5000/locacoes-abertas");
        if (!response.ok) throw new Error("Resposta não-OK ao buscar locações");
        const data = await response.json();
        const locacoes = data.locacoes || [];

        const selectLocacao = document.getElementById("selectLocacao");
        if (!selectLocacao) {
            console.warn("selectLocacao não encontrado no DOM");
            return;
        }

        // opção padrão
        selectLocacao.innerHTML = "<option value=''>Selecione uma locação</option>";

        locacoes.forEach(loc => {
            const option = document.createElement("option");
            option.value = loc.num_locacao;
            option.textContent = `${loc.num_locacao} - ${loc.placa} (Cliente: ${loc.cpf_cliente})`;

            if (loc.valor_previsto) option.dataset.valorPrevisto = String(loc.valor_previsto);
            if (loc.data_prevista_devolucao) option.dataset.dataPrevista = loc.data_prevista_devolucao;

            option.dataset.precoDiaria = loc.preco_diaria;   // ADICIONADO ❤️

            selectLocacao.appendChild(option);
});


    } catch (err) {
        console.error("Erro ao carregar locações", err);
        const selectLocacao = document.getElementById("selectLocacao");
        if (selectLocacao) selectLocacao.innerHTML = "<option value=''>Erro ao carregar</option>";
    }
}

carregarOpcoes();


// ---------------- Envio de devolução ----------------
// ---------------- Envio de devolução (corrigido) ----------------
const form = document.getElementById("formDevolucao");
if (form) {
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const msgEl = document.getElementById("mensagem");

        // 1️⃣ Monta o payload igual já estava
        const payload = {
            num_locacao: document.getElementById("selectLocacao")?.value,
            data_devolucao: document.getElementById("data_devolucao")?.value,
            estado_carro: document.getElementById("selectEstado")?.value,
            combustivel_completo: document.getElementById("selectCombustivel")?.value === "true",
            km_registro: Number(document.getElementById("km_registro")?.value) || null,
            valor_danos: Number(String(document.getElementById("valor_danos")?.value).replace(",", ".").replace("R$", "").trim()) || 0
        };

        try {
            // 2️⃣ Envia para backend
            const resp = await fetch("http://127.0.0.1:5000/aluguel/devolver", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const resultado = await resp.json();

            if (!resp.ok) {
                msgEl.textContent = `Erro: ${resultado?.erro || resultado?.mensagem || "Falha ao registrar."}`;
                msgEl.style.color = "red";
                return;
            }

            // 3️⃣ MOSTRA MENSAGEM DE SUCESSO
            msgEl.textContent = resultado.mensagem || "Devolução registrada com sucesso!";
            msgEl.style.color = "green";

            // 4️⃣ Salva o número do pagamento para gerar QR depois
            localStorage.setItem("num_pagamento", resultado.num_pagamento);

            // 5️⃣ Mostra a área de pagamento AUTOMATICAMENTE
            document.getElementById("secaoPagamento").style.display = "block";

            // 6️⃣ (Opcional) mostra automaticamente o valor final ao lado
            if (resultado.resumo_financeiro?.valor_final) {
                document.getElementById("valorFinal").value =
                    `R$ ${resultado.resumo_financeiro.valor_final.toFixed(2)}`;
            }

        } catch (err) {
            msgEl.textContent = "Erro ao conectar com servidor.";
            msgEl.style.color = "red";
        }
    });
}




// ---------------- Ao trocar de locação ----------------
// ---------------- Ao trocar de locação ----------------
const selectLocacaoEl = document.getElementById("selectLocacao");
if (selectLocacaoEl) {
    selectLocacaoEl.addEventListener("change", async function () {
        const numLocacao = this.value;

        // limpa campos visuais
        const dataPrevInput = document.getElementById("data_prevista");
        if (dataPrevInput) dataPrevInput.value = "";

        const valorFinalEl = document.getElementById("valorFinal");
        if (valorFinalEl) valorFinalEl.value = "R$ 0.00";

        if (!numLocacao) return;

        try {
            // Buscamos os detalhes completos da locação (contendo preco_diaria, valor_previsto e data_prevista_devolucao)
            const resp = await fetch(`http://127.0.0.1:5000/aluguel/${numLocacao}/detalhes`);
            if (!resp.ok) throw new Error("Erro ao buscar detalhes da locação");
            const dados = await resp.json();

            // pega a option correspondente
            const selectedOption = selectLocacaoEl.querySelector(`option[value="${numLocacao}"]`);
            if (selectedOption) {
                // salva no dataset: precoDiaria e valorPrevisto (strings)
                selectedOption.dataset.precoDiaria = String(dados.preco_diaria ?? dados.precoDiaria ?? 0);
                selectedOption.dataset.valorPrevisto = String(dados.valor_previsto ?? dados.valorPrevisto ?? 0);
                selectedOption.dataset.diasPrevistos = String(dados.dias_previstos ?? dados.diasPrevistos ?? "");
            }

            // preenche data prevista no campo (se disponível)
            if (dados.data_prevista_devolucao) {
                // Se seu backend retornar no formato YYYY-MM-DD, tudo certo.
                if (dataPrevInput) dataPrevInput.value = dados.data_prevista_devolucao;
            } else {
                if (dataPrevInput) dataPrevInput.value = "";
            }

            // DEBUG - opcional, para ver o que chegou
            console.log("detalhes locacao:", dados);
            console.log("dataset option agora:", selectedOption?.dataset);

            // recalcula com os dados novos
            calcularValorFinal();
        } catch (err) {
            console.error("Erro ao buscar detalhes do aluguel:", err);
            if (dataPrevInput) dataPrevInput.value = "";
        }
    });
} else {
    console.warn("selectLocacao não encontrado — não será possível escolher locações.");
}



// ---------------- Cálculo do valor final ----------------
function calcularValorFinal() {
    const selectLocacao = document.getElementById("selectLocacao");
    const opt = selectLocacao?.selectedOptions[0];

    // se não tiver opção selecionada, zera e retorna
    if (!opt) {
        const valorFinalEl = document.getElementById("valorFinal");
        if (valorFinalEl) valorFinalEl.value = "R$ 0.00";
        return;
    }

    const valorPrevisto = parseFloat(opt.dataset.valorPrevisto || "0");
    const precoDiaria = parseFloat(opt.dataset.precoDiaria || "0");

    const dataPrevista = document.getElementById("data_prevista")?.value;
    const dataDevolucao = document.getElementById("data_devolucao")?.value;
    const combustivel = document.getElementById("selectCombustivel")?.value; // "true"/"false"

    let valorFinal = Number(valorPrevisto) || 0;

    if (dataPrevista && dataDevolucao) {
        const dtPrev = new Date(dataPrevista);
        const dtDev = new Date(dataDevolucao);
        if (dtDev > dtPrev) {
            const diasAtraso = Math.ceil((dtDev - dtPrev) / (1000 * 60 * 60 * 24));
            // cada dia de atraso adiciona: preco_diaria + 50
            valorFinal += diasAtraso * (precoDiaria + 50);
        }
    }

    if (combustivel === "false") {
        valorFinal += 200;
    }

    const valorFinalEl = document.getElementById("valorFinal");
    if (valorFinalEl) {
        valorFinalEl.value = `R$ ${valorFinal.toFixed(2)}`;
    }
}

// Recalcula sempre que data de devolução ou seleção de combustível mudar
const dataDevolInput = document.getElementById("data_devolucao");
if (dataDevolInput) dataDevolInput.addEventListener("change", calcularValorFinal);

const selectCombEl = document.getElementById("selectCombustivel");
if (selectCombEl) selectCombEl.addEventListener("change", calcularValorFinal);

// também recalcula ao carregar opções (caso já haja seleção)

document.getElementById("btnGerarPagamento").addEventListener("click", async () => {
    const num_pagamento = localStorage.getItem("num_pagamento");

    if (!num_pagamento) {
        alert("Número do pagamento não encontrado!");
        return;
    }

    try {
        const resp = await fetch(`http://127.0.0.1:5000/pagamento/${num_pagamento}/gerar_qrcode`, {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });

        const data = await resp.json();

        if (!resp.ok) {
            alert(data.erro || "Erro ao gerar QR Code");
            return;
        }

        document.getElementById("qrcodeImagem").src = data.qr_code_url;
        document.getElementById("areaQrcode").style.display = "block";

    } catch (err) {
        console.error("Erro ao gerar QR Code:", err);
        alert("Falha ao gerar QR Code");
    }
});