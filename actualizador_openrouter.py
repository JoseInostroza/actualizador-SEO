from dotenv import load_dotenv
import os
import csv
import requests
import time


load_dotenv()

# ✅ CONFIGURA TU API KEY DE OPENROUTER AQUÍ:
OPENROUTER_API_KEY = os.getenv("API_KEY")  # Reemplaza por tu clave real de OpenRouter
OPENROUTER_MODEL = "mistralai/mistral-7b-instruct"  # Puedes cambiar el modelo si gustas

# ✅ Consulta a OpenRouter
def solicitar_respuesta(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://tusitio.com",  # Puedes cambiar esto a tu web
        "X-Title": "seo-product-generator"
    }

    data = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Eres redactor SEO."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(f"Error code: {response.status_code} - {response.json()}")
    return response.json()["choices"][0]["message"]["content"].strip()

# verificadores 
def se_debe_omitir(nombre: str) -> bool:
    nombre = nombre.lower()
    return  "Valor al detalle" in nombre or "Valor al por Mayor" in nombre

def necesita_generarse(valor: str) -> bool:
    if not valor:
        return True
    if valor.strip().lower().startswith("title") or valor.strip().lower().startswith("meta"):
        return True
    return False


# ✅ Genera todo el contenido SEO basado en nombre y categoría
def generar_contenido(nombre, categoria):
    return f"""
Quiero que generes contenido SEO para un producto de una tienda online mayorista chilena llamada comercio el sol.

Producto: {nombre}
Categoría: {categoria}

1. Identifica una única frase clave clara y breve relacionada con el producto, que tenga mas de 10 busquedas en google chile.
2. Crea un **meta título SEO** que incluya la frase clave al inicio y no exceda los 40 caracteres.
3. Redacta una **meta descripción** con tono humano y vendedor, incluyendo la frase clave, con un máximo de 130 caracteres.
4. Redacta una **descripción larga** (300 palabras aprox.) que comience con un resumen del producto y luego profundice en su uso y beneficios. Debe sonar natural, sin repetir frases o estructuras genéricas y tener almenos 3 parrafos de contenido.

Consideraciones importantes:
    Para la descripcion larga la frace clave debe aparecer maximo 3 veces en toda la redaccion y tener como minimo 3 parrafos.
    debes serguir el formado de respuesta que se te entrega, sin poner el meta titulo o la meta descripcion como parte de la respuesta de la descripcion larga 
    la respuesta tiene que ser lo mas humanizada posible, no puede ser redundante. 

Responde en el siguiente formato:
---
Frase Clave: [aquí va la frase]
Título SEO: [aquí va el título SEO]
Descripción Meta: [aquí va la descripción corta]
Descripción Larga: [aquí va la descripción larga]
"""

#buscar frace clave
def prompt_extraer_frase_clave(nombre: str, categoria: str, titulo: str, metadesc: str, descripcion: str) -> str:
    return f"""
Analiza este contenido SEO de un producto mayorista chileno.

Producto: {nombre}
Categoría: {categoria}
Título SEO: {titulo}
Meta Descripción: {metadesc}
Descripción larga: {descripcion}

⚠️ Extrae solamente **una frase clave única y relevante** para este producto. No agregues comentarios ni explicaciones, solo la frase clave.
"""



# ✅ Extrae los campos del texto generado
def extraer_campos(texto,focuskw):
    lineas = texto.split("\n")
    titulo = next((l.replace("Título SEO:", "").strip() for l in lineas if "Título SEO:" in l), "")
    descripcion = next((l.replace("Meta descripción:", "").strip() for l in lineas if "Meta descripción:" in l), "")
    desc_larga = "\n".join(l for l in lineas if not l.startswith("Título SEO:") and not l.startswith("Meta descripción:"))
    desc_larga = desc_larga.replace("Descripción larga:", "").strip()
    return focuskw,titulo, descripcion, desc_larga

def procesar_csv(entrada_csv: str, salida_csv: str):
    with open(entrada_csv, mode="r", encoding="utf-8") as entrada,          open(salida_csv, mode="w", newline="", encoding="utf-8") as salida:
        
        reader = csv.DictReader(entrada)
        campos = reader.fieldnames or []
        
        nuevos_campos = [
            "ID", "Nombre", "Categoría",
            "Meta: _yoast_wpseo_focuskw",
            "Meta: _yoast_wpseo_title",
            "Meta: _yoast_wpseo_metadesc"
        ]
        writer = csv.DictWriter(salida, fieldnames=nuevos_campos)
        writer.writeheader()

        for fila in reader:
            id_producto = fila.get("ID", "").strip()
            nombre = fila.get("Nombre", "").strip()
            categoria = fila.get("Categorías", "").strip() or "Undefined"
            foco = fila.get("Meta: _yoast_wpseo_focuskw", "").strip()
            titulo = fila.get("Meta: _yoast_wpseo_title", "").strip()
            metadesc = fila.get("Meta: _yoast_wpseo_metadesc", "").strip()
            descripcion = fila.get("Descripción", "").strip()

            if se_debe_omitir(nombre):
                continue

            if necesita_generarse(descripcion):
                print("✍️ generando nuevo contenido SEO para {nombre}")
                prompt = generar_contenido(nombre, categoria)
                respuesta = solicitar_respuesta(prompt)

                if respuesta:
                    try:
                        clave, titulo, metadesc, descripcion_larga = "", "", "", ""
                        for linea in respuesta.splitlines():
                            if "Frase Clave:" in linea:
                                clave = linea.split(":", 1)[1].strip()
                            elif "Título SEO:" in linea:
                                titulo = linea.split(":", 1)[1].strip()
                            elif "Meta descripción:" in linea:
                                metadesc = linea.split(":", 1)[1].strip()
                            elif "Descripción Larga:" in linea:
                                descripcion_larga = linea.split(":", 1)[1].strip()
                        foco = clave
                        descripcion = descripcion_larga
                        print("🆗 el seo")
                    except Exception as parse_error:
                        print(f"Error procesando respuesta IA para {nombre}: {parse_error}")
            else:
                print("🕵️ buscando esa frase clave")
                prompt = prompt_extraer_frase_clave(nombre, categoria, titulo, metadesc, descripcion)
                clave = solicitar_respuesta(prompt)
                foco = clave
                print("🆗 la frase")

            writer.writerow({
                "ID": id_producto,
                "Nombre": nombre,
                "Categoría": categoria,
                "Meta: _yoast_wpseo_focuskw": foco or "",
                "Meta: _yoast_wpseo_title": titulo or "",
                "Meta: _yoast_wpseo_metadesc": metadesc or ""
            })
            time.sleep(1.5)  # Para evitar rate limits

# ✅ Ejecuta el script
if __name__ == "__main__":
    procesar_csv('tercera.csv', "productos_conkw.csv")

