async function carregarCarros() {

    const resposta = await fetch("http://127.0.0.1:5000/carros");
    const data = await resposta.json();

    console.log(data); // veja o formato real para confirmar

    const carros = Array.isArray(data) ? data : data.carros;

    const container = document.getElementById("lista-carros");
    container.innerHTML = "";

    carros.forEach(carro => {
        const card = document.createElement("div");
        card.classList.add("col-md-4", "col-sm-6", "car-card");

        card.innerHTML = `
            <a href="carro.html?placa=${carro.placa}" class="car-link">
                <div class="car-box">
                    <img src="images/${carro.imagem}" alt="${carro.nome}">
                    <h3>${carro.nome}</h3>
                    <p>${carro.descricao}</p>
                    <span class="price">
                        ${Number(carro.preco).toLocaleString('pt-BR', {
                            style: 'currency',
                            currency: 'BRL'
                        })} / dia
                    </span>
                </div>
            </a>
        `;

        container.appendChild(card);
    });
}

carregarCarros();
