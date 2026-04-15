// becario.js - Scanner de QR para check-in
// El QR ahora contiene solo la matrícula en texto plano (más simple y confiable)

let html5QrCode;

function onScanSuccess(decodedText) {
    console.log(`QR escaneado: ${decodedText}`);
    stopScanner();
    performCheckin(decodedText.trim().toUpperCase());
}

function onScanError() {
    // Errores de escaneo son normales mientras busca el QR, no los mostramos
}

async function performCheckin(matricula) {
    const msgEl = document.getElementById("scannerMessage");
    const infoEl = document.getElementById("scannedInfo");
    const resName = document.getElementById("resName");
    const resMatricula = document.getElementById("resMatricula");
    const resStatus = document.getElementById("resStatus");
    const btnRestart = document.getElementById("btnRestartScanner");

    msgEl.style.display = "none";
    infoEl.style.display = "none";

    try {
        // Enviamos la matrícula en texto plano — el backend la valida contra la BD
        const response = await fetch("/checkins/scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ matricula }),
            credentials: "same-origin"  // Envía la cookie access_token automáticamente
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `Error ${response.status}`);
        }

        // Mostrar resultado
        infoEl.style.display = "block";
        resName.textContent = data.student?.full_name || data.student?.matricula || matricula;
        resMatricula.textContent = `Matrícula: ${data.student?.matricula || matricula}`;
        if (data.student?.career) {
            resMatricula.textContent += ` | ${data.student.career}`;
        }

        if (data.already_checked_in) {
            resStatus.innerHTML = `<span style="background:#fef9c3;color:#854d0e;padding:4px 10px;border-radius:12px;font-size:0.85rem;">Ya tenía check-in</span>`;
        } else {
            resStatus.innerHTML = `<span style="background:#dcfce7;color:#15803d;padding:4px 10px;border-radius:12px;font-size:0.85rem;">✅ Check-in registrado</span>`;
        }

        msgEl.textContent = data.message;
        msgEl.style.background = data.already_checked_in ? "#fef9c3" : "#dcfce7";
        msgEl.style.color = data.already_checked_in ? "#854d0e" : "#15803d";
        msgEl.style.display = "block";

        btnRestart.style.display = "block";

    } catch (err) {
        msgEl.textContent = "⚠️ " + (err.message || "Error al registrar check-in");
        msgEl.style.background = "#fee2e2";
        msgEl.style.color = "#b91c1c";
        msgEl.style.display = "block";
        btnRestart.style.display = "block";
    }
}

function startScanner() {
    const btnStart = document.getElementById("btnStartCamera");
    const msgEl = document.getElementById("scannerMessage");

    if (btnStart) btnStart.setAttribute("disabled", "true");
    if (msgEl) {
        msgEl.style.display = "none";
        msgEl.textContent = "";
    }

    html5QrCode = new Html5Qrcode("reader");
    const config = { fps: 10, qrbox: { width: 250, height: 250 } };

    html5QrCode.start({ facingMode: "environment" }, config, onScanSuccess, onScanError)
    .then(() => {
        if (btnStart) btnStart.parentElement.style.display = "none";
    })
    .catch(err => {
        console.error("Error al iniciar cámara:", err);
        if (btnStart) btnStart.removeAttribute("disabled");
        const errorMessage = document.getElementById("scannerMessage");
        errorMessage.textContent = "Error al iniciar cámara: " + err;
        errorMessage.style.background = "#fee2e2";
        errorMessage.style.color = "#b91c1c";
        errorMessage.style.display = "block";
    });
}

function stopScanner() {
    if (html5QrCode && html5QrCode.isScanning) {
        html5QrCode.stop().then(() => {
            html5QrCode.clear();
        }).catch(err => console.error("Error deteniendo scanner:", err));
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const btnStart = document.getElementById("btnStartCamera");
    if (btnStart) {
        btnStart.addEventListener("click", startScanner);
    }

    const btnRestart = document.getElementById("btnRestartScanner");
    if (btnRestart) {
        btnRestart.addEventListener("click", () => {
            btnRestart.style.display = "none";
            document.getElementById("scannerMessage").style.display = "none";
            document.getElementById("scannedInfo").style.display = "none";
            const cameraControls = document.getElementById("cameraControls");
            if (cameraControls) cameraControls.style.display = "block";
            startScanner();
        });
    }
});
