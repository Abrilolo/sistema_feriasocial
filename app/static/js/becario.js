import { requestJSON } from './api.js?v=2';
import { getAuthHeaders } from './auth.js';
import { showMessage, hideMessage, badgeLabel } from './ui.js';

let html5QrCode;

function onScanSuccess(decodedText, decodedResult) {
    console.log(`Scan result: ${decodedText}`);
    stopScanner();
    performCheckin(decodedText);
}

function onScanError(errorMessage) {
    // console.warn(`Scan error: ${errorMessage}`);
}

async function performCheckin(qrToken) {
    const msgEl = document.getElementById("scannerMessage");
    const infoEl = document.getElementById("scannedInfo");
    const resName = document.getElementById("resName");
    const resMatricula = document.getElementById("resMatricula");
    const resStatus = document.getElementById("resStatus");
    const btnRestart = document.getElementById("btnRestartScanner");

    msgEl.style.display = "none";
    infoEl.style.display = "none";

    try {
        const data = await requestJSON("/checkins/scan", {
            method: "POST",
            headers: { "Content-Type": "application/json", ...getAuthHeaders() },
            body: JSON.stringify({ qr_token: qrToken, method: "QR" })
        });

        // Show info
        infoEl.style.display = "block";
        resName.textContent = `✅ ${data.matricula}`;
        resMatricula.textContent = "Check-in realizado con éxito.";
        resStatus.innerHTML = badgeLabel("COMPLETADO", "success");
        
        msgEl.textContent = data.message;
        msgEl.style.background = "#dcfce7";
        msgEl.style.color = "#15803d";
        msgEl.style.display = "block";

        btnRestart.style.display = "block";

    } catch (err) {
        msgEl.textContent = "Error: " + err.message;
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
        console.error("Unable to start scanner", err);
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
        }).catch(err => console.error("Err clearing", err));
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const btnStart = document.getElementById("btnStartCamera");
    if (btnStart) {
        btnStart.addEventListener("click", startScanner);
    }

    document.getElementById("btnRestartScanner").addEventListener("click", () => {
        document.getElementById("btnRestartScanner").style.display = "none";
        document.getElementById("scannerMessage").style.display = "none";
        document.getElementById("scannedInfo").style.display = "none";
        const cameraControls = document.getElementById("cameraControls");
        if (cameraControls) cameraControls.style.display = "block";
        startScanner();
    });
});
