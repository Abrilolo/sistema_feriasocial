import qrcode
from PIL import Image

def generar_qr(datos, nombre_archivo="codigo_qr.png"):
    try:
        # 1. Configuración del objeto QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        # 2. Añadir la información
        qr.add_data(datos)
        qr.make(fit=True)

        # 3. Crear la imagen
        img = qr.make_image(fill_color="black", back_color="white")

        # 4. Guardar la imagen
        img.save(nombre_archivo)
        
        # Eliminamos el emoji para evitar el UnicodeEncodeError
        print(f"Generado con exito: {nombre_archivo}")

        # 5. Visualización
        img.show()
        
    except Exception as e:
        print(f"Ocurrio un error: {e}")

if __name__ == "__main__":
    # Cambia esto por la URL o texto que desees
    contenido = "https://www.google.com"
    generar_qr(contenido)