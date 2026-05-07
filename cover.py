from PIL import Image
from PIL import ImageDraw
from PIL import ImageOps
from PIL import ImageFont
import textwrap

import urllib.request
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont

class DVDGenAgent:
    def __init__(self):
        self.anilist_url = 'https://graphql.anilist.co'
        
        # Medidas en píxeles (a 300 DPI para calidad de impresión)
        self.canvas_width = 1572  # Ancho total del lienzo (frente + lomo + espalda)
        self.canvas_height = 1064  # Altura total del lienzo
        self.spine_width = 96  # Ancho del lomo del cover DVD (96 pixels for a standard DVD case)
        self.side_width = (self.canvas_width - self.spine_width) // 2
        self.season_year = ''

        self.size_font_title = 38  # Tamaño de fuente para el título en pixeles (24 pt)
        self.size_font_year = 28  # Tamaño de fuente para el año de la temporada en pixeles (18 pt)
        
        # Colores para cada temporada (puedes ajustar estos colores a tu preferencia)
        self.season_color_winter = (240, 148, 117)  # Color para invierno
        self.season_color_spring = (117, 240, 148)  # Color para primavera
        self.season_color_summer = (148, 117, 240)  # Color para verano
        self.season_color_fall = (240, 117, 148)  # Color para otoño
        self.season_color_default = (255, 255, 255)  # Color del lomo (you can choose any color you like)

    def get_anilist_data(self, media_id):
        query = '''
        query Media($mediaId: Int) {
            Media(id: $mediaId) {
                id
                title { romaji }
                type
                status
                season
                seasonYear
                episodes
                genres
                coverImage {
                  extraLarge
                }
                bannerImage
          }
        }
        '''
        vars = {'mediaId': media_id}
        response = requests.post(self.anilist_url, json={'query': query, 'variables': vars})
        return response.json()['data']['Media']

    def create_cover(self, media_id):
        data = self.get_anilist_data(media_id)

        # Aquí descargarías la imagen de TMDB o AniList
        print(f"Generando cover para: {data['title']['romaji']}...")
        
        # 1. Crear lienzo base (Blanco o Negro)
        cover = Image.new('RGB', (self.canvas_width, self.canvas_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(cover)

        # 2. Lógica para el posterior (Izquierdo del lienzo)
        # Cargar referencia
        reference = Image.open("assets/referencia.png")
        reference = reference.resize((738, 144))  # Resize the reference image to match the new image size
        cover.paste(reference, (0, cover.height - reference.height), reference)  # Paste the reference image onto the new image
        
        # 3. Lomo (Centro)        
        season = data['season']
        if season == 'WINTER':
            spine_color = self.season_color_winter
        elif season == 'SPRING':
            spine_color = self.season_color_spring
        elif season == 'SUMMER':
            spine_color = self.season_color_summer
        elif season == 'FALL':
            spine_color = self.season_color_fall
        else:
            spine_color = self.season_color_default

        draw.rectangle([self.side_width, 0, self.side_width + self.spine_width, self.canvas_height], fill=spine_color)
        
        # Agregamos el icono DVD en la parte superior e inferior del lomo
        (margin_top, margin_bottom) = (15, 15)
        dvd_icon = Image.open("assets/dvd_icon.png")
        dvd_icon = ImageOps.contain(dvd_icon, (80, 80))  # Resize the DVD icon to match the new image size
        cover.paste(dvd_icon, (self.side_width + self.spine_width // 2 - dvd_icon.width // 2, margin_top), dvd_icon)  # Paste the DVD icon onto the new image
        cover.paste(dvd_icon, (self.side_width + self.spine_width // 2 - dvd_icon.width // 2, self.canvas_height - dvd_icon.height - margin_bottom), dvd_icon)  # Paste the DVD icon onto the new image
        
        # Season year
        season_year = data.get('seasonYear')
        title_font = ImageFont.truetype("C:/Windows/Fonts/agencyfb.TTF", self.size_font_year)  # Load a font (make sure to have the font file in the same directory or provide the correct path)
        draw.text((self.side_width + (self.spine_width // 2 - title_font.getlength(str(season_year)) // 2), margin_top + dvd_icon.height + 5), str(season_year), fill=(0, 0, 0), font=title_font)  # Draw the season year on the spine

        # Agregar Id anime en la parte inferior del lomo
        anime_id_text = data['id']
        draw.text((self.side_width + (self.spine_width // 2 - title_font.getlength(str(anime_id_text)) // 2), self.canvas_height - 2 * margin_bottom - dvd_icon.height - 25), str(anime_id_text), fill=(0, 0, 0), font=title_font)

        # 4. Lógica para el Frente (Derecha del lienzo)
        # Definimos las cabeceras para imitar a un navegador web
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Referer': 'https://anilist.co/'
        }

        # Creamos la petición envolviendo la URL y los headers
        req = urllib.request.Request(data['coverImage']['extraLarge'], headers=headers)

        # front_cover = Image.open("fondo_frontal.png")
        try:
            with urllib.request.urlopen(req) as response:
                front_cover = Image.open(BytesIO(response.read()))
        except Exception as e:
            print(f"Error al cargar la imagen del cover: {e}")
            front_cover = Image.new("RGB", (self.side_width, self.canvas_height), color=(255, 255, 255))  # Create a blank white image

        front_cover = ImageOps.cover(front_cover, (self.side_width, self.canvas_height))
        cover.paste(front_cover, (self.side_width + self.spine_width, 0))  # Paste the front cover onto the new image

        # 5. Título del cover
        title_text = data['title']['romaji']  # Title text for the cover

        wrapped_title = textwrap.fill(title_text, width=33)  # Wrap the title text to fit within a certain width
        title_font_size = self.size_font_title  # Tamaño de fuente para el título en pixeles (24 pt)
        title_color = (255, 255, 255)  # White color for the title text
        front_cover_x = 738 + self.spine_width
        title_font = ImageFont.truetype("C:/Windows/Fonts/GOTHICB.TTF", title_font_size)  # Load a font (make sure to have the font file in the same directory or provide the correct path)
    
        # Calcular la posición del título para centrarlo horizontalmente en el cover frontal
        title_bbox = draw.multiline_textbbox((0, 0), wrapped_title, font=title_font, align="center")
        title_width = title_bbox[2] - title_bbox[0]
        title_x = front_cover_x + (self.side_width - title_width) // 2

        #Altura del título
        margin_bottom = 100
        title_height = title_bbox[3] - title_bbox[1]
        title_y = cover.height - title_height - margin_bottom

        title_position = (title_x, title_y)
        draw.multiline_text(title_position, wrapped_title, font=title_font, fill=title_color, stroke_width=3, stroke_fill=(0, 0, 0), align="center")  # Draw centered multiline title text

        # Logo DVD
        dvd_logo = Image.open("assets/logo_dvd.png")
        dvd_pos = (self.side_width + self.spine_width + 5, 5)
        dvd_logo = dvd_logo.resize((100, 100))  # Resize the DVD logo to match the new image size
        cover.paste(dvd_logo, dvd_pos, dvd_logo)  # Paste the DVD logo onto the new image
        
        cover.show()
        return  0

        # 5. Guardar resultado
        filename = f"{title_search.replace(' ', '_')}_cover.jpg"
        cover.save(filename, quality=95)
        print(f"Archivo guardado como: {filename}")

# Uso del agente
id_anime = input("Ingrese el ID del anime en AniList: ")
agent = DVDGenAgent()
# agent.create_cover("Cyberpunk Edgerunners")
agent.create_cover(int(id_anime))
exit(0)

def create_cover(image_path, url_cover, url_fondo1, url_fondo2):    
    print(f"Creando el cover...")    
    # Open the image
    img = Image.new("RGB", (1572, 1064), color=(255, 255, 255))  # Create a blank white image
    new_image = "image_png.png"

    # Cargar imagen de fondo 1
    with urllib.request.urlopen(url_fondo1) as response:
        img1 = Image.open(BytesIO(response.read()))

    # Cargar referencia
    reference = Image.open("assets/referencia.png")
    reference = reference.resize((738, 144))  # Resize the reference image to match the new image size
    img.paste(reference, (0, img.height - reference.height), reference)  # Paste the reference image onto the new image

    # Agregar fondo 1 y fondo 2 al nuevo lienzo
    img1 = ImageOps.fit(img1, (738, img.height // 2))  # Resize the background image to fit within the new image dimensions
    img.paste(img1, (0, 0))  # Paste the first background image onto the new image

    # img2 = Image.open("fondo2.png")
    with urllib.request.urlopen(url_fondo2) as response:
        img2 = Image.open(BytesIO(response.read()))
    img2 = ImageOps.cover(img2, (738, img.height // 2))  # Resize the background image to fit within the new image dimensions
    img.paste(img2, (0, img.height // 2))  # Paste the second background image onto the new image

    # Crear el lomo del cover DVD
    spine_width = 96  # Ancho del lomo del cover DVD (96 pixels for a standard DVD case)
    spine_color = (240, 148, 117)  # Color del lomo (you can choose any color you like)
    spine = Image.new("RGB", (spine_width, img.height), color=spine_color)  # Create the spine image
    img.paste(spine, (738, 0))  # Paste the spine onto the new image

    # Crear el fondo del cover frontal
    front_cover_width = 738  # Width of the front cover 

    # Definimos las cabeceras para imitar a un navegador web
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': 'https://anilist.co/'
    }

    # Creamos la petición envolviendo la URL y los headers
    req = urllib.request.Request(url_cover, headers=headers)
    
    # front_cover = Image.open("fondo_frontal.png")
    try:
        with urllib.request.urlopen(req) as response:
            front_cover = Image.open(BytesIO(response.read()))
    except Exception as e:
        print(f"Error al cargar la imagen del cover: {e}")
        front_cover = Image.new("RGB", (front_cover_width, img.height), color=(255, 255, 255))  # Create a blank white image

    front_cover = ImageOps.cover(front_cover, (front_cover_width, img.height))
    img.paste(front_cover, (738 + spine_width, 0))  # Paste the front cover onto the new image

    # Titulo del cover
    title_text = "Akujiki Reijou to Kyouketsu Koushasku: Sono Mamono, Watashi ga Oishiku Itadakimasu!"  # Title text for the cover

    wrapped_title = textwrap.fill(title_text, width=33)  # Wrap the title text to fit within a certain width
    title_font_size = 38 # Tamaño de fuente para el título en pixeles (24 pt)
    title_color = (255, 255, 255)  # White color for the title text
    front_cover_x = 738 + spine_width
    draw = ImageDraw.Draw(img)
    title_font = ImageFont.truetype("C:/Windows/Fonts/GOTHICB.TTF", title_font_size)  # Load a font (make sure to have the font file in the same directory or provide the correct path)
    
    # Calcular la posición del título para centrarlo horizontalmente en el cover frontal
    title_bbox = draw.multiline_textbbox((0, 0), wrapped_title, font=title_font, align="center")
    title_width = title_bbox[2] - title_bbox[0]
    title_x = front_cover_x + (front_cover_width - title_width) // 2

    #Altura del título
    margin_bottom = 100
    title_height = title_bbox[3] - title_bbox[1]
    title_y = img.height - title_height - margin_bottom

    title_position = (title_x, title_y)
    draw.multiline_text(title_position, wrapped_title, font=title_font, fill=title_color, stroke_width=3, stroke_fill=(0, 0, 0), align="center")  # Draw centered multiline title text

    img.show()
    return 0
    
    img.save(new_image)
    print(f"New image saved as: {new_image}")

image_path = "fondo.jpg"  # Replace with your image path

# Establecemos algunas variables
# url_cover = "https://image.tmdb.org/t/p/original/4B6btop1kg5Q3UNnZ0KoZKCkCJG.jpg"
url_cover = "https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx120377-ayZPoxiWt4Li.jpg"
url_fondo1 = "https://image.tmdb.org/t/p/original/9B5LzLJ26cq80rwnItaW4sf6EOS.jpg"
url_fondo2 = "https://image.tmdb.org/t/p/original/w1HbeProIahk07Ksj5Y2OVo5Zxx.jpg"

create_cover(image_path, url_cover, url_fondo1, url_fondo2)
