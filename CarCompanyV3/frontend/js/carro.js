async function carregarCarro() {
    const params = new URLSearchParams(window.location.search);
    const placa = params.get("placa"); 

    if (!placa) {
        alert("Carro não encontrado");
        return;
    }

    try {
        const response = await fetch(`http://127.0.0.1:5000/carros/${placa}`);
        const carro = await response.json();

        if (!response.ok) {
            throw new Error(carro.erro || "Erro ao carregar carro");
        }

        document.getElementById("carro-imagem").src = `images/${carro.imagem}`;
        document.getElementById("carro-imagem").alt = carro.nome;
        document.getElementById("carro-nome").textContent = carro.nome;
        document.getElementById("carro-descricao").textContent = carro.tipo_categoria;
        document.getElementById("carro-preco").textContent =
            Number(carro.preco || carro.preco_diaria).toLocaleString("pt-BR", {
                style: "currency",
                currency: "BRL"
            }) + " / dia";

        const btnAlugar = document.querySelector(".btn-alugar");
        if (btnAlugar) {
            btnAlugar.href = `alugar.html?placa=${encodeURIComponent(carro.placa)}`;
        }   
    } catch (err) {
        console.error(err);
        alert("Erro ao carregar detalhes do carro: " + err.message);
    }
}

carregarCarro();
