// js/relatorio.js (versão segura: evita TypeError quando inputs faltam)
document.addEventListener("DOMContentLoaded", () => {
  // localizar o form: prioriza id, depois classe, depois primeiro form
  let form = document.getElementById("relatorio-form-1")
          || document.getElementById("relatorio-form")
          || document.querySelector("form.filtro-relatorio")
          || document.querySelector("form");

  if (!form) {
    console.error("relatorio.js: nenhum <form> encontrado. Verifique o HTML.");
    return;
  }
  console.log("relatorio.js: form encontrado:", form);

  // procurar inputs de data preferencialmente dentro do form
  let inputMin = form.querySelector("#data-min-1")
               || form.querySelector("#data-min")
               || form.querySelector('input[name="data_min"]')
               || null;

  let inputMax = form.querySelector("#data-max-1")
               || form.querySelector("#data-max")
               || form.querySelector('input[name="data_max"]')
               || null;

  // fallback: pegar os dois primeiros input[type=date] do form
  if ((!inputMin || !inputMax) && form) {
    const dateInputs = form.querySelectorAll('input[type="date"]');
    if (dateInputs.length >= 2) {
      inputMin = inputMin || dateInputs[0];
      inputMax = inputMax || dateInputs[1];
      console.log("relatorio.js: inputs encontrados por ordem dentro do form.");
    } else if (dateInputs.length === 1) {
      inputMin = inputMin || dateInputs[0];
      console.warn("relatorio.js: encontrado apenas 1 input[type=date]; falta o outro.");
    }
  }

  if (!inputMin || !inputMax) {
    const msg = "Campos de data não encontrados no formulário. IDs esperados: data-min-1/data-max-1 ou inputs type=date dentro do form.";
    console.error("relatorio.js:", msg, { inputMin, inputMax });
    alert(msg);
    return;
  }

  // encontrar botão dentro do form
  let btn = form.querySelector(".btn-admin") || form.querySelector('button[type="button"]') || form.querySelector("button");
  if (!btn) {
    console.error("relatorio.js: botão de envio não encontrado dentro do form.");
    alert("Botão de gerar relatório não encontrado no formulário.");
    return;
  }

  const BASE_URL = "http://127.0.0.1:5000";
; // ex: "http://127.0.0.1:5000" caso necessário

  function formatFilename(min, max) {
    const a = (s) => s ? s.replaceAll("-", "") : "";
    return `vendas_${a(min)}_${a(max)}.csv`;
  }

  async function gerarRelatorio() {
    // checagem de segurança antes de acessar .value
    if (!inputMin || !inputMax) {
      alert("Inputs de data não encontrados. Recarregue a página ou verifique o HTML.");
      return;
    }

    const dataMin = inputMin.value;
    const dataMax = inputMax.value;

    if (!dataMin || !dataMax) {
      alert("Por favor selecione data mínima e máxima.");
      return;
    }
    if (dataMin > dataMax) {
      alert("A data mínima não pode ser maior que a máxima.");
      return;
    }

    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = "Gerando...";

    const endpoint = `${BASE_URL}/relatorios/vendas`.replace(/([^:]\/)\/+/g, "$1");

    try {
      console.log("Enviando requisição para:", endpoint, { data_min: dataMin, data_max: dataMax });

      const resp = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/csv, application/json"
        },
        body: JSON.stringify({ data_min: dataMin, data_max: dataMax })
      });

      console.log("Resposta:", resp.status, resp.statusText);

      if (!resp.ok) {
        let text = await resp.text();
        try {
          const j = JSON.parse(text);
          text = j.erro || j.message || JSON.stringify(j);
        } catch (e) { /* mantém text */ }
        throw new Error(`Erro ${resp.status}: ${text}`);
      }

      const contentType = resp.headers.get("Content-Type") || "";
      if (contentType.includes("text/csv") || contentType.includes("application/octet-stream")) {
        const blob = await resp.blob();
        const cd = resp.headers.get("Content-Disposition") || "";
        let filename = "";
        const m = cd.match(/filename\*=UTF-8''(.+)|filename="?(.*?)"?(;|$)/);
        if (m) filename = decodeURIComponent(m[1] || m[2]);
        if (!filename) filename = formatFilename(dataMin, dataMax);

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        console.log("Download iniciado:", filename);
      } else {
        const text = await resp.text();
        alert("Resposta inesperada do servidor:\n" + text);
        console.warn("Resposta inesperada:", contentType, text);
      }
    } catch (err) {
      console.error("Erro ao gerar relatório:", err);
      alert("Erro ao gerar relatório: " + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    gerarRelatorio();
  });
});
