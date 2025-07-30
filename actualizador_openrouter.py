from dotenv import load_dotenv
import os
import csv
import requests
import time


load_dotenv()

# ✅ CONFIGURA TU API KEY DE OPENROUTER AQUÍ:
OPENROUTER_API_KEY = os.getenv("API_KEY")  # Reemplaza por tu clave real de OpenRouter
OPENROUTER_MODEL = "gpt-4o"  # Puedes cambiar el modelo si gustas

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
Actúa como un experto en redacción SEO y marketing digital con experiencia en eCommerce. Recibirás un producto con su nombre y categoría. Debes generar 3 elementos bien redactados y optimizados para buscadores:

1. **Frase clave principal** (1 sola, específica, realista, con mas de 10 busquedas)
2. **Título SEO** (máx. 35 caracteres, atractivo y directo)
3. **Meta descripción** (máx. 160 caracteres, clara y vendedora)
4. **Descripción larga** (persuasiva, enfocada en beneficios y público mayorista de 250 a 300 palabras, y 3 parrafos y la frace clave debe estar almenos una vez en el primer parrafo)

### Reglas clave:
- No incluyas frases como "esta es la frase clave" o "esta es la meta descripción".
- Usa un tono humano, confiable y profesional.
- No inventes propiedades que el producto no tiene.
- No repitas el nombre del producto más de lo necesario.
- Si el producto tiene enfoque mayorista, destácalo.

### Entrada:
Nombre del producto: {nombre}
Categoría: {categoria}

### Salida esperada:
Frase clave: ...
Título SEO: ...
Meta descripción: ...
Descripción larga: ...
"""

#buscar frace clave
def prompt_extraer_frase_clave(nombre: str, categoria: str, titulo: str, metadesc: str, descripcion: str) -> str:
    return f"""
Analiza este contenido SEO de un producto mayorista chileno.

Producto: {nombre}
Categoría: {categoria}
Título SEO: {titulo}
Meta Descripción: {metadesc}
Descripción Larga: {descripcion}

⚠️ Extrae solamente **una frase clave única y relevante** para este producto. No agregues comentarios ni explicaciones, solo la frase clave.
"""



# ✅ Extrae los campos del texto generado
def extraer_campos(texto,focuskw):
    lineas = texto.split("\n")
    titulo = next((l.replace("Título SEO:", "").strip() for l in lineas if "Título SEO:" in l), "")
    descripcion = next((l.replace("Meta descripción:", "").strip() for l in lineas if "Meta descripción:" in l), "")
    desc_larga = "\n".join(l for l in lineas if not l.startswith("Título SEO:") and not l.startswith("Meta descripción:"))
    desc_larga = desc_larga.replace("Descripción Larga:", "").strip()
    return focuskw,titulo, descripcion, desc_larga

def procesar_csv(entrada_csv: str, salida_csv: str):
    with open(entrada_csv, mode="r", encoding="utf-8") as entrada,          open(salida_csv, mode="w", newline="", encoding="utf-8") as salida:
        
        reader = csv.DictReader(entrada)
        campos = reader.fieldnames or []
        
        nuevos_campos = [
            "ID", "Nombre", "Categoría", "Descripción",
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
                print(f"✍️ generando nuevo contenido SEO para {nombre}")
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
                "Descripción": descripcion,
                "Meta: _yoast_wpseo_focuskw": foco or "",
                "Meta: _yoast_wpseo_title": titulo or "",
                "Meta: _yoast_wpseo_metadesc": metadesc or ""
            })
            time.sleep(1.5)  # Para evitar rate limits

# ✅ Ejecuta el script
if __name__ == "__main__":
    procesar_csv('segunda.csv', "productos_conkw.csv")

