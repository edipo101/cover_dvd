from PIL import Image, ImageDraw

def degrade_image(imagen, proporcion_degradado=0.4):
    # 1. Abrir la imagen y asegurar que tenga canal alfa (RGBA)
    # img = Image.open(imagen).convert("RGBA")
    img = imagen.convert("RGBA")
    ancho, alto = img.size
    
    # 2. Crear una nueva imagen para la máscara (Modo 'L' para escala de grises)
    # 255 es blanco (opaco), 0 es negro (transparente)
    mask = Image.new('L', (ancho, alto), 255)
    draw = ImageDraw.Draw(mask)
    
    # 3. Calcular dónde empieza el degradado (ej: en el último 40% de la imagen)
    inicio_degradado = int(alto * (1 - proporcion_degradado))
    
    # 4. Dibujar el degradado línea por línea
    for y in range(inicio_degradado, alto):
        # Calculamos la opacidad: de 255 (inicio) a 0 (final)
        opacidad = int(255 * (1 - (y - inicio_degradado) / (alto - inicio_degradado)))
        draw.line((0, y, ancho, y), fill=opacidad)
    
    # 5. Aplicar la máscara a la imagen
    img.putalpha(mask)
    
    return img