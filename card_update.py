from PIL import Image, ImageDraw, ImageFont


def crear_tarjeta(nombre, path_base, path_salida):
    imagen = Image.open(path_base)
    draw = ImageDraw.Draw(imagen)

    # Elegí una fuente que tengas instalada o poné la ruta
    fuente = ImageFont.truetype("arial.ttf", 60)

    texto = f"¡Feliz Cumple {nombre}!"
    ancho_texto, _ = draw.textsize(texto, font=fuente)

    # Posición aproximada donde está el texto original
    x = (imagen.width - ancho_texto) // 2
    y = 300  # Ajustar según el diseño

    draw.text((x, y), texto, font=fuente, fill="navy")
    imagen.save(f"{path_salida}/{nombre}_cumple.jpg")
