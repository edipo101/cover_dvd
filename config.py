import os
from dotenv import load_dotenv
import ast

def load_config():
    if not load_dotenv():
        print("Error: No se pudo cargar el archivo .env")
        exit(0)
    config = {
        "env": os.getenv("APP_ENV", "production"),
        "debug": os.getenv("APP_DEBUG", "false").lower() == "true",
        
        # APIs de metadatos
        "tmdb_key": os.getenv("TMDB_API_KEY", ""),
        "tmdb_lang": os.getenv("TMDB_LANGUAGE", "es-ES"),
        
        # Rutas locales en Laragon
        "output_dir": os.getenv("OUTPUT_DIR", "."),
        "assets_dir": os.getenv("ASSETS_DIR", "./assets"),
        
        # Dimensiones físicas para los cálculos de lienzo en Pillow
        "cover_width": int(os.getenv("COVER_WIDTH_PX", 272)),
        "cover_height": int(os.getenv("COVER_HEIGHT_PX", 184)),
        "cover_spine": int(os.getenv("COVER_SPINE_PX", 14)),
        "dpi": int(os.getenv("COVER_DPI", 300)),

        # urls
        "anilist_url": os.getenv("ANILIST_API_URL", "https://graphql.anilist.co"),
        "tmdb_url": "https://api.themoviedb.org/3/search/multi",
        "tmdb_img_base_url": "https://image.tmdb.org/t/p/original", # url para mostrar la imagenes
        "tmdb_url_images": "https://api.themoviedb.org/3/tv/series_id/images", # url para obtener los back_drops

        # Establecer colores para el lomo
        "season_cl_winter": ast.literal_eval(os.getenv("SEASON_WINTER")),
        "season_cl_spring": ast.literal_eval(os.getenv("SEASON_SPRING")),
        "season_cl_summer": ast.literal_eval(os.getenv("SEASON_SUMMER")),
        "season_cl_fall": ast.literal_eval(os.getenv("SEASON_FALL"))
    }
    return config