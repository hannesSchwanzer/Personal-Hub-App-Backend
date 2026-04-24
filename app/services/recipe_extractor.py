import requests
from bs4 import BeautifulSoup
import json

class RecipeExtractorService:

    @staticmethod
    def extract_recipe_auto(url: str):
        """
        Extracts recipe from a website URL.
        Returns a dict with extracted recipe, or raw text as fallback.
        """
        html = RecipeExtractorService._html_from_url(url)

        structured_recipe = RecipeExtractorService._extract_structured_recipe_from_html(html)
        if structured_recipe:
            return structured_recipe

        # Pure heuristic extraction as plain text
        return RecipeExtractorService._extract_recipe_text_from_html(html)

    @staticmethod
    def extract_recipe_structured(url: str):
        html = RecipeExtractorService._html_from_url(url)

        structured_recipe = RecipeExtractorService._extract_structured_recipe_from_html(html)
        return structured_recipe

    @staticmethod
    def extract_recipe_text(url: str):
        html = RecipeExtractorService._html_from_url(url)
        return RecipeExtractorService._extract_recipe_text_from_html(html)

    @staticmethod
    def _extract_structured_recipe_from_html(html: str):
        # Attempt to extract structured recipe JSON-LD
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script', type='application/ld+json')
        # Disabled extraction of structured recipe data, only fallback to text
        for script in scripts:
            try:
                if script.string:
                    data = json.loads(script.string)
                    # JSON-LD can be a list or dict
                    if isinstance(data, list):
                        for entry in data:
                            if entry.get('@type') == 'Recipe':
                                return {'type': 'structured', 'data': entry}
                    elif isinstance(data, dict):
                        if data.get('@type') == 'Recipe':
                            return {'type': 'structured', 'data': data}
            except Exception:
                continue

        return None

    @staticmethod
    def _html_from_url(url: str):
        response = requests.get(url)
        html = response.text
        return html


    @staticmethod
    def _extract_recipe_text_from_html(html: str):
        """
        Heuristically extract recipe text from raw HTML using BeautifulSoup only.
        Returns a dict with 'ingredients' and 'instructions' as text lists if possible; tries to
        avoid site navigation/ads and maximize useful info. If not found, collects best guess text.
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Find blocks near likely recipe-related headers
        def find_section(header_keywords, list_tags=['ul', 'ol']):
            for header in soup.find_all(lambda tag: tag.name in ['h1','h2','h3','h4'] and any(word in tag.get_text().lower() for word in header_keywords)):
                for tagname in list_tags:
                    possible = header.find_next(tagname)
                    if possible:
                        items = [li.get_text(strip=True) for li in possible.find_all('li')]
                        if items:
                            return items
            return []

        # Try to find ingredients
        ingredients = find_section(['ingredient'])
        if not ingredients:
            # Try any list with many entries and header nearby
            for ul in soup.find_all('ul'):
                if ul.find_previous(lambda tag: tag.name in ['h2','h3','h4'] and 'ingredient' in tag.get_text().lower()):
                    items = [li.get_text(strip=True) for li in ul.find_all('li') if li.get_text(strip=True)]
                    if len(items) >= 2:
                        ingredients = items
                        break

        # Try to find instructions
        instructions = find_section(['instruction','preparation','directions','method'], list_tags=['ol'])
        if not instructions:
            # Try ordered lists after relevant headers
            for ol in soup.find_all('ol'):
                if ol.find_previous(lambda tag: tag.name in ['h2','h3','h4'] and any(word in tag.get_text().lower() for word in ['instruction','step','direction','preparation','method'])):
                    items = [li.get_text(strip=True) for li in ol.find_all('li') if li.get_text(strip=True)]
                    if len(items) >= 2:
                        instructions = items
                        break

        # Fallback: paragraphs near keywords
        if not ingredients:
            ing_paras = []
            for p in soup.find_all('p'):
                prev = p.find_previous(lambda tag: tag.name in ['h2','h3','h4'] and 'ingredient' in tag.get_text().lower())
                text = p.get_text(strip=True)
                if prev and text:
                    ing_paras.append(text)
            ingredients = ing_paras

        if not instructions:
            inst_paras = []
            for p in soup.find_all('p'):
                prev = p.find_previous(lambda tag: tag.name in ['h2','h3','h4'] and any(word in tag.get_text().lower() for word in ['instruction','step','direction','preparation','method']))
                text = p.get_text(strip=True)
                if prev and text:
                    inst_paras.append(text)
            instructions = inst_paras

        # As a last resort: heuristical, skip menus/footers
        def guess_recipe_body():
            """Collect blocks that are neither nav/footer nor too short"""
            sections = []
            for section in soup.find_all(['section','article','div']):
                classes = section.get('class') or []
                class_str = ' '.join(classes).lower()
                if any(bad in class_str for bad in ['header','nav','menu','foot','ad','sidebar']):
                    continue
                text = section.get_text(separator='\n', strip=True)
                if text and 200 > len(text) > 30:
                    sections.append(text)
            return sections[:2]

        # Build the output
        # Always use strings for all results, to simplify downstream use
        result = {
            'ingredients': '\n'.join(ingredients) if ingredients else '',
            'instructions': '\n'.join(instructions) if instructions else '',
        }
        # Remove obvious junk from candidate lists
        for k in result:
            result[k] = [line for line in result[k] if not any(w in line.lower() for w in [
                'copyright','all rights','cookie','privacy','subscribe','sign up','newsletter','advertis','related post','leave a comment','latest recipe','search','share','author','time:','difficulty','youtube','instagram','twitter','facebook','info@','category:'
            ])]

        # Fallback: If all empty, best guess from content blocks
        if not any(result.values()) or all((not v or all(line.strip() == '' for line in v)) for v in result.values()):
            candidates = guess_recipe_body()
            text_blob = '\n\n'.join(candidates) if candidates else soup.get_text(separator='\n', strip=True)
            text_blob = '\n'.join([line for line in text_blob.splitlines() if not any(w in line.lower() for w in [
                'copyright','all rights','cookie','privacy','subscribe','sign up','newsletter','advertis','related post','leave a comment','latest recipe','search','share','author','time:','difficulty','youtube','instagram','twitter','facebook','info@','category:'
            ]) and len(line.strip()) > 10])
            if text_blob.strip():
                return {'text': text_blob.strip()}
            else:
                return {'text': 'No recipe content could be heuristically extracted.'}

        # Convert to string if list is too short or list is not useful
        for k in ('ingredients','instructions'):
            # Convert list (if present) to string, always; ensure not empty if any plausible fallback text
            text_blob = '\n'.join(result[k]) if result[k] else ''
            if not text_blob.strip():
                # fallback to best guess from visible body if present
                candidates = guess_recipe_body()
                backup = '\n\n'.join(candidates) if candidates else soup.get_text(separator='\n', strip=True)
                backup = '\n'.join([line for line in backup.splitlines() if not any(w in line.lower() for w in [
                    'copyright','all rights','cookie','privacy','subscribe','sign up','newsletter','advertis','related post','leave a comment','latest recipe','search','share','author','time:','difficulty','youtube','instagram','twitter','facebook','info@','category:'
                ]) and len(line.strip()) > 10])
                text_blob = backup.strip()
                if not text_blob:
                    text_blob = 'No recipe content could be heuristically extracted.'
            result[k] = text_blob
        return result
