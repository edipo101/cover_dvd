import os
from PIL import Image, ImageDraw, ImageOps, ImageFont
import textwrap
import re
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
import urllib.request
from io import BytesIO
import requests
from pathlib import Path
import ast

from imageOp import degrade_image
from config import load_config

def get_anilist_data(id):
    query = '''
    query Media($id: Int) {
        Media(id: $id) {
            id
            title { romaji }
            type
            status
            season
            seasonYear
            episodes
            genres
            description
            coverImage {
                extraLarge
            }
            bannerImage
            idMal
        }
    }
    '''
    vars = {'id': id}
    response = requests.post(cfg.get('anilist_url'), json={'query': query, 'variables': vars})
    return response.json()['data']['Media']

def get_tmdb_data(title, year):
    params = {
        "api_key": cfg.get('tmdb_key'),
        "query": title,
        "language": cfg.get('tmdb_lang'), # Traer datos en español
        "first_air_date_year": year, # Filtro para precisión
        "include_adult": "false"
    }

    try:
        response = requests.get(cfg.get('tmdb_url'), params=params)
        results = response.json().get('results', [])
        if results:
            return results[0] 
        return None
    except Exception as e:
        print(f"ERROR: No se puede conectar a TMDB: {e}")
        return None
    
def get_back_drops(series_id):
    url_images = cfg.get('tmdb_url_images')
    url_images = url_images.replace("series_id", str(series_id))
    params = {"api_key": cfg.get('tmdb_key')}
    try:
        response = requests.get(url_images, params=params).json()
        results = response.get('backdrops', [])
    except Exception as e:
        print(f"Error conectando a TMDB: {e}")
        results = []
    return results

def clean_title(title):
    # Elimina "Season X", "Part X", "2nd Season", etc.
    # El flag re.IGNORECASE hace que no importe si es mayúscula o minúscula
    patterns = [
        r' (?:S|s)eason \d+', 
        r' (?:P|p)art \d+',
        r' \d+(?:nd|st|rd|th) (?:S|s)eason',
        r' (?:T|t)(?:V|v)'
    ]
    for pattern in patterns:
        title = re.sub(pattern, '', title)
    return title.strip()
        
class DVDGenAgent:
    def __init__(self, cfg):
        self.lang = 'jap' # Audio por defecto
        # Medidas en píxeles (a 300 DPI para calidad de impresión)
        self.side_width = (cfg.get('cover_width') - cfg.get('cover_spine')) // 2

        self.size_font_title = 42  # Tamaño de fuente para el título en pixeles (24 pt)
        self.size_font_year = 28  # Tamaño de fuente para el año de la temporada en pixeles (18 pt)
        
        # Texto y colores del idioma
        self.lang_japanese = "Japonés"
        self.lang_spanish = "Español"
        self.lang_latino = "Latino"
        self.color_jap = (255, 0, 0)
        self.color_spa = (255, 0, 0)
        self.color_lat = (255, 0, 0)
        self.cover_jap = (255, 255, 255)
        self.cover_spa = (255, 255, 51)
        self.cover_lat = (255, 255, 51)
    
    def create_rear(self, draw, data, cover, font_size=25, lang='jap'):
        title_romaji = data.get('title').get('romaji')
        title_cleaned = clean_title(title_romaji)
        if title_romaji and title_romaji[-1].isdigit():
            title_romaji = title_romaji[:-1]
        release_year = data.get('seasonYear')

        tmdb_info = get_tmdb_data(title_cleaned, release_year)
        # print(tmdb_info)
        
        if tmdb_info:
            back_drops = get_back_drops(tmdb_info.get('id'))
            img_base_url = cfg.get('tmdb_img_base_url')
            print("\nDatos obtenidos de TMDB exitosamente.")
            print(f"Generando cover para: {data['title']['romaji']}...")
            ''' 
            cant = len(back_drops)
            print(f"Number of backdrops found: {cant}")
            for img in back_drops:
                print(f"{img_base_url}{img.get('file_path')}")
            '''
            # También puedes obtener el póster de alta calidad de TMDB si quieres
            poster_path = tmdb_info.get('backdrop_path')
            rear_cover2 = Image.open(requests.get(f"{img_base_url}{back_drops[2].get('file_path')}", stream=True).raw)
            rear_cover2 = ImageOps.cover(rear_cover2, (self.side_width, (cfg.get('cover_height') // 4) * 3))
            porcent_y = 0.30
            pos_y = int(cfg.get('cover_height') * porcent_y)
            cover.paste(rear_cover2, (0, pos_y))  # Paste the rear cover onto the new image

            rear_cover = Image.open(requests.get(f"{img_base_url}{poster_path}", stream=True).raw)
            rear_cover = ImageOps.cover(rear_cover, (self.side_width, cfg.get('cover_height') // 2))
            rear_degrade = degrade_image(rear_cover)
            cover.paste(rear_degrade, (self.side_width // 2 - rear_cover.width // 2, 0), rear_degrade)  # Paste the rear cover onto the new image
        else:
            # Fallback: Si no está en TMDB, usamos la de AniList (y ahí sí traduces)
            print("ERROR: No se encontró datos en TMDB!")
            exit(0)

        # Agregar sinopsis
        synopsis = data.get('description', 'Sin sinopsis disponible.')
        synopsis = textwrap.shorten(synopsis, width=520, placeholder="...")  # Recortar la sinopsis a un máximo de caracteres
        synopsis_esp = GoogleTranslator(source='auto', target='es').translate(synopsis)  # Traducir la sinopsis al español
        clean_synopsis = BeautifulSoup(synopsis_esp, "html.parser").get_text(separator='. ', strip=True)  # Limpiar la sinopsis de etiquetas HTML
        font_syn = ImageFont.truetype(f"{cfg.get('assets_dir')}/agencyfb.TTF", font_size)
        rear_text = textwrap.fill(clean_synopsis, width=90)  # Wrap the synopsis text to fit within a certain width
        lines = rear_text.split('\n')
        count_lines = len(lines)
        left, top, right, bottom = font_syn.getbbox(rear_text)
        line_hight = bottom - top
        spacing = -3
        total_hight = (line_hight * count_lines) + (spacing * (count_lines - 1))
        rear_text_position = (20, 597 - total_hight - 100)  # Position for the synopsis text on the rear cover
        draw.multiline_text(rear_text_position, rear_text, font=font_syn, fill=(0, 0, 0), spacing=spacing, stroke_width=3, stroke_fill=(255, 255, 255))  # Draw the synopsis text on the rear cover
        
        # Datos tecnicos
        font_tech = ImageFont.truetype(f"{cfg.get('assets_dir')}/agencyfb.TTF", font_size)
        cover_tech = Image.new('RGBA', (352, 295), (255, 255, 255, 0))  # Create a transparent image for the technical information
        draw_tech = ImageDraw.Draw(cover_tech)
        technical_info_position = (20, 17)  # Position for the technical information on the rear cover
        draw_tech.rounded_rectangle((0, 0, 352, 295), fill=(255, 255, 255, 255), radius=15, outline=(255, 0, 0), width=2)

        # Diccionario de traducción
        stations = {
            "spring": "primavera",
            "summer": "verano", # Añadido por completitud
            "fall": "otoño",
            "autumn": "otoño",
            "winter": "invierno"
        }
        season = data.get('season', 'N/A')
        if season:
            season = season.lower()
            for eng, esp in stations.items():
                season = season.replace(eng, esp)
            season = season.capitalize()

        language_text = self.lang_japanese
        if lang == "esp":
            language_text = self.lang_spanish
        elif lang == "lat":
            language_text = self.lang_latino

        data_tech = {
            'Título': data.get('title', {}).get('romaji', 'N/A'),
            'Géneros': GoogleTranslator(source='auto', target='es').translate(', '.join(data.get('genres', []))),
            'Tipo': data.get('type', 'N/A'),
            'Episodios': data.get('episodes', 'N/A'),
            'Estado': GoogleTranslator(source='auto', target='es').translate(data.get('status', 'N/A')).capitalize(),
            'Audio': language_text,
            'Temporada': str(season) + ' ' + str(data.get('seasonYear', 'N/A'))
        }

        for key, value in data_tech.items():
            key_text = f"{key.capitalize()}: "
            value_text = str(value)
            # Wrap the value text to fit within width
            wrapped_lines = textwrap.wrap(value_text, width=35)  # Approximate width for 352px
            if wrapped_lines:
                # First line: key + first part of value
                first_value_line = wrapped_lines[0]
                first_line = key_text + first_value_line
                full_width = font_tech.getlength(first_line)
                center_x = 176
                start_x = center_x - full_width / 2
                if start_x < 0:
                    start_x = 0
                draw_tech.text((start_x, technical_info_position[1]), key_text, font=font_tech, fill=(255, 0, 0))
                key_width = font_tech.getlength(key_text)
                draw_tech.text((start_x + key_width, technical_info_position[1]), first_value_line, font=font_tech, fill=(0, 0, 0))
                technical_info_position = (technical_info_position[0], technical_info_position[1] + 30)
                # Subsequent lines of value, centered in black
                for line in wrapped_lines[1:]:
                    full_width = font_tech.getlength(line)
                    start_x = center_x - full_width / 2
                    if start_x < 0:
                        start_x = 0
                    draw_tech.text((start_x, technical_info_position[1]), line, font=font_tech, fill=(0, 0, 0))
                    technical_info_position = (technical_info_position[0], technical_info_position[1] + 30)
            else:
                # If no value, just draw key
                full_width = font_tech.getlength(key_text)
                start_x = center_x - full_width / 2
                draw_tech.text((start_x, technical_info_position[1]), key_text, font=font_tech, fill=(255, 0, 0))
                technical_info_position = (technical_info_position[0], technical_info_position[1] + 30)
        
        # Agregar borde rojo de 2px con puntas redondeadas
        
        cover.paste(cover_tech, (20, 597), cover_tech)  # Paste the technical information onto the rear cover

        # Cargar referencia
        reference = Image.open("assets/referencia.png")
        reference = reference.resize((738, 144))  # Resize the reference image to match the new image size
        cover.paste(reference, (0, cover.height - reference.height), reference)  # Paste the reference image onto the new image              
        
    def create_spine(self, draw, data, cover, font_size=38):
        # 3. Lomo (Centro)        
        spine_color = cfg.get('season_cl_' + data['season'].lower())
        
        draw.rectangle([self.side_width, 0, self.side_width + cfg.get('cover_spine'), cfg.get('cover_height')], fill=spine_color)

        # Agregamos el título de la temporada en el lomo
        title = data['title']['romaji'].upper()  # Título del anime para el lomo

        # Recorta a 30 caracteres pero intenta no romper la última palabra
        title = textwrap.shorten(title, width=35, placeholder="...")

        # Crear una imagen pequeña para el texto del lomo
        font = ImageFont.truetype(f"{cfg.get('assets_dir')}/CenturyGothic.TTF", font_size)
        # Calculamos tamaño del texto usando getbbox
        left, top, right, bottom = font.getbbox(title)
        tw, th = right - left, bottom - top
        
        # Crear imagen transparente para el texto
        txt_img = Image.new('RGBA', (tw + 10, th + 10), (255, 255, 255, 0))
        d = ImageDraw.Draw(txt_img)
        d.text((-left + 5, -top + 5), title, font=font, fill="white", stroke_width=3, stroke_fill=(0, 0, 0))
        
        # Rotar 90 grados (sentido horario para lectura vertical)
        spine_txt = txt_img.rotate(90, expand=True)
        txt_x = self.side_width + (cfg.get('cover_spine') - spine_txt.width) // 2 # Ajustamos la posición horizontal para centrar el texto en el lomo
        txt_y = (cfg.get('cover_height') - spine_txt.height) // 2
        cover.paste(spine_txt, (txt_x, txt_y), spine_txt)

        # Agregamos el icono DVD en la parte superior e inferior del lomo
        (margin_top, margin_bottom) = (15, 15)
        dvd_icon = Image.open("assets/dvd_icon.png")
        dvd_icon = ImageOps.contain(dvd_icon, (80, 80))  # Resize the DVD icon to match the new image size
        cover.paste(dvd_icon, (self.side_width + cfg.get('cover_spine') // 2 - dvd_icon.width // 2, margin_top), dvd_icon)  # Paste the DVD icon onto the new image
        cover.paste(dvd_icon, (self.side_width + cfg.get('cover_spine') // 2 - dvd_icon.width // 2, cfg.get('cover_height') - dvd_icon.height - margin_bottom), dvd_icon)  # Paste the DVD icon onto the new image
        
        # Season year
        season_year = data.get('seasonYear')
        title_font = ImageFont.truetype(f"{cfg.get('assets_dir')}/agencyfb.TTF", self.size_font_year)  # Load a font (make sure to have the font file in the same directory or provide the correct path)
        draw.text((self.side_width + (cfg.get('cover_spine') // 2 - title_font.getlength(str(season_year)) // 2), margin_top + dvd_icon.height + 5), str(season_year), fill=(0, 0, 0), font=title_font)  # Draw the season year on the spine

        # Agregar Id anime en la parte inferior del lomo
        anime_id_text = data['id']
        draw.text((self.side_width + (cfg.get('cover_spine') // 2 - title_font.getlength(str(anime_id_text)) // 2), cfg.get('cover_height') - 2 * margin_bottom - dvd_icon.height - 27), str(anime_id_text), fill=(0, 0, 0), font=title_font)
    
    def create_front(self, draw, data, cover, lang, cant=1):
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
            front_cover = Image.new("RGB", (self.side_width, cfg.get('cover_height')), color=(255, 255, 255))  # Create a blank white image

        front_cover = ImageOps.cover(front_cover, (self.side_width, cfg.get('cover_height')))
        cover.paste(front_cover, (self.side_width + cfg.get('cover_spine'), 0))  # Paste the front cover onto the new image

        # 5. Título del cover
        title_text = data['title']['romaji']  # Title text for the cover

        wrapped_title = textwrap.fill(title_text, width=30)  # Wrap the title text to fit within a certain width
        title_font_size = self.size_font_title  # Tamaño de fuente para el título en pixeles (24 pt)
        title_color = (255, 255, 255)  # White color for the title text
        front_cover_x = 738 + cfg.get('cover_spine')
        title_font = ImageFont.truetype(f"{cfg.get('assets_dir')}/GOTHICB.TTF", title_font_size)  # Load a font (make sure to have the font file in the same directory or provide the correct path)
    
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
        dvd_logo = dvd_logo.resize((85, 85))  # Resize the DVD logo to match the new image size
        pos_x = self.side_width + cfg.get('cover_spine')
            
        for x in range(0, cant):
            if x == 0:
                pos_x = pos_x + 5
            else:
                pos_x = pos_x + 67
            cover.paste(dvd_logo, (pos_x, 5), dvd_logo)  # Paste the DVD logo onto the new image
        # dvd_pos = (self.side_width + cfg.get('cover_spine') + 5, 5)

        # Etiqueta del idioma
        cover_language = Image.new('RGBA', (300, 55), self.cover_jap)  # Create a background for the language label
        language_color = self.color_jap
        language_text = self.lang_japanese
        if lang == "esp":
            cover_language = Image.new('RGBA', (300, 55), self.cover_spa)  # Create a background for the language label
            language_color = self.color_spa
            language_text = self.lang_spanish
        elif lang == "lat":
            cover_language = Image.new('RGBA', (300, 55), self.cover_lat)  # Create a background for the language label
            language_color = self.color_lat
            language_text = self.lang_latino

        # Centrar el texto dentro de la etiqueta del idioma
        language_font = ImageFont.truetype(f"{cfg.get('assets_dir')}/BRLNSDB.TTF", 36)  # Load a font for the language label
        d = ImageDraw.Draw(cover_language)
        
        left, top, right, bottom = language_font.getbbox(language_text)
        language_width = right - left
        language_height = bottom - top
        
        d.text(((cover_language.width - language_width) // 2, -top + (cover_language.height - language_height) // 2), language_text, font=language_font, fill=language_color)
        cover_language = cover_language.rotate(-45, expand=True, fillcolor=(0, 0, 0, 0))  # Rotate the language label by -45 degrees
        cover.paste(cover_language, (1380, -50), cover_language)  # Paste the language label onto the new image

    def create_cover(self):
        # 1. Crear lienzo base (Blanco o Negro)
        cover = Image.new('RGB', (cfg.get('cover_width'), cfg.get('cover_height')), color=(255, 255, 255))
        draw = ImageDraw.Draw(cover)
        
        # 2. Lógica para el posterior (Izquierdo del lienzo)
        self.create_rear(draw, data, cover, 25, lang)               

        # 3. Lógica para el lomo (Centro del lienzo)
        self.create_spine(draw, data, cover)

        # 4. Lógica para el Frente (Derecha del lienzo)
        self.create_front(draw, data, cover, lang, cant)

        # cover.show()
        # return  0

        # 5. Guardar resultado  
        title = data['title']['romaji']
        title = title.replace(':', ' -')
        title_cleaned = clean_title(title)
        title_shortened = textwrap.shorten(title_cleaned, width=45, placeholder='')
        
        # Language abbreviation
        lang_abbr = lang.upper()
        
        # Season
        season_name = data.get('season', '')
        if season_name:
            season_name = season_name.capitalize()
        season_year = str(data.get('seasonYear', ''))
        season_info = f"{season_name} {season_year}".strip()
        
        filename = f"{title_shortened} {lang_abbr} {season_info}.jpg"
        # cover.show()
        path = f"{cfg.get('output_dir')}/{filename}"
        cover.save(path, dpi=(150, 150))
        print(f"\nArchivo guardado como: {filename}")
        
        # Abrir el archivo creado
        path = Path(path)
        os.startfile(path)

if __name__ == "__main__":
    cfg = load_config()
    path = Path(cfg.get('output_dir'))
    if not path.exists():
        print("ERROR: La ruta destino no existe!")
        exit(0)
    
    agent = DVDGenAgent(cfg)
    
    id_anime = input("Ingrese el ID del anime en AniList: ")
    data = get_anilist_data(id_anime)    
    if data is None:
        print("No se encontró el anime con el ID proporcionado.")
        exit(0)
    print(f"Anime encontrado: {data['title']['romaji']} ({data.get('seasonYear', 'N/A')})")
    
    # Establecer el idioma
    print("\nIngrese el idioma del anime (jap, esp, lat): ")
    lang = input("Idioma (jap): ").lower()
    if not lang:
        print("Idioma por defecto: jap")
        lang = 'jap'
    elif lang not in ('jap', 'esp', 'lat'):
        print("Opción no válida, idioma por defecto (jap)")
        lang = 'jap'
    agent.lang = lang
    
    # Establecer la cantidad de discos
    cant = input("\n¿Cuántos logos de DVD quieres en el frente? (1-3): ")
    try:
        cant = int(cant)
        if cant < 1 or cant > 3:
            print("Número inválido, se colocará 1 logo por defecto.")
            cant = 1
    except ValueError:
        print("Entrada no válida, se colocará 1 logo por defecto.")
        cant = 1
    
    agent.create_cover()