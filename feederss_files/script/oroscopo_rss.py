#!/usr/bin/env python3
"""
Script per generare feed RSS dell'oroscopo del Corriere della Sera
Genera feed per l'oroscopo del giorno di tutti i segni zodiacali
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from lxml import etree
import sys
import os

# Configurazione
BASE_URL = "https://www.corriere.it/oroscopo"
OUTPUT_DIR = "rss_feeds"

# Segni zodiacali
SEgni_ZODIACALI = [
    "ariete", "toro", "gemelli", "cancro", "leone", "vergine",
    "bilancia", "scorpione", "sagittario", "capricorno", "acquario", "pesci"
]

# Periodi di nascita per ogni segno
PERIODI_NASCITA = {
    "ariete": "21/3 - 19/4",
    "toro": "20/4 - 20/5",
    "gemelli": "21/5 - 20/6",
    "cancro": "21/6 - 22/7",
    "leone": "23/7 - 22/8",
    "vergine": "23/8 - 22/9",
    "bilancia": "23/9 - 22/10",
    "scorpione": "23/10 - 21/11",
    "sagittario": "22/11 - 21/12",
    "capricorno": "22/12 - 19/1",
    "acquario": "20/1 - 18/2",
    "pesci": "19/2 - 20/3"
}

# Tipologie di oroscopo (solo oggi)
TIPOLOGIE = {
    "oggi": "oggi"
}

def scarica_pagina(url):
    """Scarica una pagina web"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        # Forza l'encoding UTF-8
        response.encoding = 'utf-8'
        return response.text
    except Exception as e:
        print(f"Errore scaricando {url}: {e}")
        return None

def estrai_oroscopo(html, segno, tipo):
    """Estrae i dati dell'oroscopo dall'HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Estrazione del titolo dal meta tag con itemprop="name"
    title_tag = soup.find('meta', attrs={'itemprop': 'name'})
    if title_tag and title_tag.get('content'):
        titolo = title_tag.get('content')
    else:
        # Fallback: cerca il title tag HTML standard
        title_tag = soup.find('title')
        if title_tag:
            titolo = title_tag.get_text(strip=True)
        else:
            # Ulteriore fallback: cerca h1 con classe title-art
            h1_tag = soup.find('h1', class_='title-art')
            titolo = h1_tag.get_text(strip=True) if h1_tag else f"Oroscopo {segno.capitalize()} - {tipo.capitalize()}"
    
    # Aggiungi il periodo di nascita al titolo
    periodo = PERIODI_NASCITA.get(segno, "")
    if periodo:
        # Rimuovi eventuali parentesi duplicate
        if not titolo.endswith(f"({periodo})"):
            titolo = f"{titolo} ({periodo})"
    
    # Estrazione dell'autore
    author_tag = soup.find('span', class_='author-art')
    autore = author_tag.get_text(strip=True) if author_tag else "Paolo Fox"
    
    # Estrazione della data
    date_tag = soup.find('span', class_='date-art')
    if date_tag:
        data_text = date_tag.get_text(strip=True)
        # Formatta la data
        try:
            data = datetime.strptime(data_text, "%d %B %Y").strftime("%Y-%m-%d")
        except:
            data = datetime.now().strftime("%Y-%m-%d")
    else:
        data = datetime.now().strftime("%Y-%m-%d")
    
    # Estrazione dell'immagine
    immagine = ""
    # Cerca immagini nella pagina, specialmente nell'hero
    img_tags = soup.find_all('img')
    for img in img_tags:
        img_src = img.get('src', '')
        if 'oroscopo' in img_src and ('sfondo' in img_src or 'segno' in img_src):
            immagine = img_src
            if not immagine.startswith('http'):
                immagine = 'https:' + immagine
            break
    # Fallback: immagine di default
    if not immagine:
        immagine = "https://components2.corriereobjects.it/rcs_cor_corriere-layout/v2/assets/img/ext/oroscopo/sfondi/sfondo-hero.jpg"
    
    # Estrazione del contenuto principale
    contenuto = "Contenuto non disponibile"
    
    # Prova diversi selettori per trovare il contenuto
    # Metodo 1: Cerca div con classe 'content' che contiene paragrafi
    content_divs = soup.find_all('div', class_='content')
    for div in content_divs:
        paragraphs = div.find_all('p')
        if paragraphs:
            # Unisci il testo dai paragrafi
            contenuto = ""
            for p in paragraphs:
                text = p.get_text(separator='\n', strip=True)
                if text and len(text) > 50:  # Ignora paragrafi troppo corti
                    contenuto += text + "\n\n"
            if contenuto.strip():
                contenuto = contenuto.strip()
                break
    
    # Metodo 2: Se non ha trovato nulla, cerca paragrafi direttamente
    if contenuto == "Contenuto non disponibile":
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and len(text) > 100:  # Cerca paragrafi lunghi
                contenuto = text
                break
    
    # Costruisci l'URL
    if tipo == "scheda":
        url = f"{BASE_URL}/segni-zodiacali-caratteristiche/{segno}/"
    else:
        url = f"{BASE_URL}/{tipo}/{segno}/"
    
    # Debug: stampa se il contenuto è troppo breve
    if len(contenuto) < 200:
        print(f"  ⚠ Warning: Contenuto troppo breve per {segno} ({tipo}): {len(contenuto)} caratteri")
    
    return {
        'titolo': titolo,
        'autore': autore,
        'data': data,
        'contenuto': contenuto,
        'url': url,
        'immagine': immagine,
        'segno': segno,
        'tipo': tipo
    }

def genera_rss(oroscopo_data):
    """Genera XML RSS dai dati dell'oroscopo"""
    rss = etree.Element('rss', version='2.0')
    channel = etree.SubElement(rss, 'channel')
    
    # Informazioni del canale
    etree.SubElement(channel, 'title').text = f"Oroscopo {oroscopo_data['segno'].capitalize()} - {oroscopo_data['tipo'].capitalize()}"
    etree.SubElement(channel, 'description').text = f"Feed RSS per l'oroscopo {oroscopo_data['tipo']} di {oroscopo_data['segno'].capitalize()}"
    etree.SubElement(channel, 'link').text = oroscopo_data['url']
    etree.SubElement(channel, 'language').text = 'it-it'
    etree.SubElement(channel, 'lastBuildDate').text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
    
    # Item (articolo)
    item = etree.SubElement(channel, 'item')
    etree.SubElement(item, 'title').text = oroscopo_data['titolo']
    
    # Usa CDATA per il contenuto lungo
    description = etree.SubElement(item, 'description')
    description.text = etree.CDATA(oroscopo_data['contenuto'])
    
    etree.SubElement(item, 'link').text = oroscopo_data['url']
    etree.SubElement(item, 'author').text = oroscopo_data['autore']
    etree.SubElement(item, 'pubDate').text = datetime.strptime(oroscopo_data['data'], "%Y-%m-%d").strftime("%a, %d %b %Y %H:%M:%S %z")
    
    # Pretty print XML con lxml
    xml_str = '<?xml version="1.0" encoding="utf-8"?>\n' + etree.tostring(rss, pretty_print=True, encoding='unicode')
    return xml_str

def salva_rss(rss_content, filename):
    """Salva il feed RSS in un file"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(rss_content)
    print(f"✓ Feed salvato: {filepath}")
    return filepath

def genera_feed_completo(tipo):
    """Genera un feed RSS completo per tutti i segni di una determinata tipologia"""
    # Namespace come Feed RSS di Focus
    nsmap = {
        'atom': 'http://www.w3.org/2005/Atom',
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'media': 'http://search.yahoo.com/mrss/'
    }
    
    rss = etree.Element('rss', version='2.0', nsmap=nsmap)
    channel = etree.SubElement(rss, 'channel')
    
    # Informazioni del canale
    tipo_capitalizzato = tipo.capitalize()
    etree.SubElement(channel, 'title').text = f"Oroscopo {tipo_capitalizzato} - Tutti i Segni"
    etree.SubElement(channel, 'description').text = f"Feed RSS completo per l'oroscopo {tipo_capitalizzato} di tutti i segni zodiacali"
    etree.SubElement(channel, 'link').text = f"{BASE_URL}/{tipo}/"
    etree.SubElement(channel, 'language').text = 'it-IT'
    etree.SubElement(channel, 'copyright').text = "Paolo Fox - Corriere della Sera"
    etree.SubElement(channel, 'pubDate').text = datetime.now().strftime("%a, %d %b %Y 06:00:00 +0100")
    etree.SubElement(channel, 'lastBuildDate').text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
    etree.SubElement(channel, 'ttl').text = "300"
    
    # atom:link per self
    self_link = etree.SubElement(channel, '{http://www.w3.org/2005/Atom}link')
    self_link.set('href', f"{BASE_URL}/{tipo}/rss")
    self_link.set('rel', 'self')
    self_link.set('type', 'application/rss+xml')
    
    # Image del channel
    image = etree.SubElement(channel, 'image')
    etree.SubElement(image, 'url').text = "https://www.corriere.it/static/img/logos/corriere-320x320.png"
    etree.SubElement(image, 'title').text = "Oroscopo Corriere"
    etree.SubElement(image, 'link').text = f"{BASE_URL}/{tipo}/"
    etree.SubElement(image, 'width').text = "320"
    etree.SubElement(image, 'height').text = "320"
    etree.SubElement(image, 'description').text = "Oroscopo del Corriere della Sera"
    
    # Aggiungi item per ogni segno
    for segno in SEgni_ZODIACALI:
        if tipo == "scheda":
            url = f"{BASE_URL}/segni-zodiacali-caratteristiche/{segno}/"
        else:
            url = f"{BASE_URL}/{tipo}/{segno}/"
        
        print(f"  Scaricando {segno} ({tipo})...")
        html = scarica_pagina(url)
        
        if html:
            oroscopo = estrai_oroscopo(html, segno, tipo)
            
            item = etree.SubElement(channel, 'item')
            etree.SubElement(item, 'title').text = oroscopo['titolo']
            
            # Descrizione breve
            description_text = oroscopo['contenuto'][:200] + "..." if len(oroscopo['contenuto']) > 200 else oroscopo['contenuto']
            description = etree.SubElement(item, 'description')
            description.text = description_text
            
            etree.SubElement(item, 'link').text = oroscopo['url']
            etree.SubElement(item, 'author').text = oroscopo['autore']
            etree.SubElement(item, 'pubDate').text = datetime.strptime(oroscopo['data'], "%Y-%m-%d").strftime("%a, %d %b %Y 06:00:00 +0100")
            etree.SubElement(item, 'category').text = segno.capitalize()
            
            # GUID
            guid = etree.SubElement(item, 'guid')
            guid.set('isPermaLink', 'true')
            guid.text = oroscopo['url']
            
            # media:content per l'immagine
            media_content = etree.SubElement(item, '{http://search.yahoo.com/mrss/}content')
            media_content.set('url', oroscopo['immagine'])
            media_content.set('type', 'image/jpg')
            media_content.set('expression', 'full')
            media_content.set('width', '630')
            media_content.set('height', '360')
            
            # media:description
            media_description = etree.SubElement(media_content, '{http://search.yahoo.com/mrss/}description')
            media_description.set('type', 'plain')
            media_description.text = etree.CDATA(f" {oroscopo['titolo']} ")
            
            # content:encoded per il contenuto completo
            content_encoded = etree.SubElement(item, '{http://purl.org/rss/1.0/modules/content/}encoded')
            content_encoded.text = etree.CDATA(f" {oroscopo['contenuto']} ")
        else:
            print(f"  ✗ Errore scaricando {segno}")
    
    # Pretty print XML con lxml
    xml_str = '<?xml version="1.0" encoding="utf-8"?>\n' + etree.tostring(rss, pretty_print=True, encoding='unicode')
    return xml_str

def main():
    """Funzione principale"""
    print("=" * 60)
    print("Generatore Feed RSS Oroscopo - Corriere della Sera")
    print("=" * 60)
    
    # Genera feed completi per ogni tipologia
    for tipo in TIPOLOGIE.keys():
        print(f"\n🌟 Generando feed completo per: {tipo}")
        print(f"  URL base: {BASE_URL}/{tipo}/")
        rss_content = genera_feed_completo(tipo)
        
        filename = f"oroscopo_{tipo}_completo.xml"
        salva_rss(rss_content, filename)
    
    # Genera feed individuali per ogni segno
    print(f"\n🎯 Generando feed individuali per ogni segno...")
    for tipo in TIPOLOGIE.keys():
        for segno in SEgni_ZODIACALI:
            if tipo == "scheda":
                url = f"{BASE_URL}/segni-zodiacali-caratteristiche/{segno}/"
            else:
                url = f"{BASE_URL}/{tipo}/{segno}/"
            
            print(f"  Scaricando {segno} ({tipo})...")
            html = scarica_pagina(url)
            
            if html:
                oroscopo = estrai_oroscopo(html, segno, tipo)
                rss_content = genera_rss(oroscopo)
                
                filename = f"oroscopo_{tipo}_{segno}.xml"
                salva_rss(rss_content, filename)
    
    print("\n" + "=" * 60)
    print("✅ Tutti i feed RSS sono stati generati con successo!")
    print(f"📁 I file sono stati salvati nella directory: {OUTPUT_DIR}/")
    print("=" * 60)

if __name__ == "__main__":
    main()