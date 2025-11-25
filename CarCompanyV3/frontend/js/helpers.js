// js/helpers.js - CORRIGIDO
const API_URL = "http://127.0.0.1:5000";

async function apiFetch(path, options = {}) {
    const url = `${API_URL}${path}`;
    const opts = {
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        ...options
    };
    
    if (opts.body && typeof opts.body !== "string") {
        opts.body = JSON.stringify(opts.body);
    }
    
    try {
        const res = await fetch(url, opts);
        let payload = null;
        
        // Tentar parsear JSON apenas se houver conteúdo
        const contentType = res.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            payload = await res.json();
        }
        
        if (!res.ok) {
            const errMsg = (payload && (payload.erro || payload.message)) || `HTTP ${res.status}`;
            const err = new Error(errMsg);
            err.status = res.status;
            err.body = payload;
            throw err;
        }
        
        return payload;
    } catch (error) {
        console.error("API Fetch Error:", error);
        throw error;
    }
}

function qparam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
}

function formatCurrency(v) {
    if (!v) return "R$ 0,00";
    return Number(v).toLocaleString("pt-BR", { 
        style: "currency", 
        currency: "BRL" 
    });
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text ?? "";
}

function showError(message) {
    alert(message); // Pode ser substituído por um modal mais elegante
}

// Exportar para uso global
window.apiFetch = apiFetch;
window.qparam = qparam;
window.formatCurrency = formatCurrency;
window.setText = setText;
window.showError = showError;