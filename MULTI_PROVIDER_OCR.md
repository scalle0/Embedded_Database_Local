# Multi-Provider OCR Fallback Systeem

## Overzicht

Het OCR systeem gebruikt nu een **intelligente fallback chain** met meerdere providers voor optimale tekst extractie, vooral voor moeilijke handgeschreven documenten.

## OCR Fallback Chain

```
1. Tesseract (lokaal, snel)
   ↓ (als confidence < 70%)
2. EasyOCR (lokaal, beter voor complexe layouts)
   ↓ (als confidence < 70%)
3. Claude Vision API (beste voor handschrift) ⭐ NIEUW
   ↓ (als Claude faalt)
4. Gemini Vision API (backup)
```

## Waarom Claude als Primaire AI Fallback?

### Voordelen van Claude Opus 4.5 voor OCR:
- **Superieure handschrift herkenning**: State-of-the-art vision capabilities
- **Layout behoud**: Bewaart originele structuur perfect
- **Context begrip**: Beste in class voor tekst interpretatie
- **Betrouwbaarheid**: Hoogste kwaliteit resultaten
- **Nieuwste model**: Claude Opus 4.5 (released November 2024)

### Model Opties

Het systeem ondersteunt meerdere Claude modellen (configureerbaar in config.yaml):

| Model | Best voor | Snelheid | Kosten | Kwaliteit |
|-------|----------|----------|--------|-----------|
| **claude-opus-4-5-20251101** (default) | Beste kwaliteit OCR, complexe handschriften | ⭐⭐⭐⭐ | $$$ | ⭐⭐⭐⭐⭐ |
| **claude-sonnet-4-5-20250929** | Balans snelheid/kwaliteit | ⭐⭐⭐⭐⭐ | $$ | ⭐⭐⭐⭐ |
| **claude-haiku-4-5-20251001** | Volume processing | ⭐⭐⭐⭐⭐ | $ | ⭐⭐⭐ |

### Claude vs Gemini Vergelijking:

| Aspect | Claude Opus 4.5 | Gemini 2.0 Flash |
|--------|-----------------|------------------|
| Handschrift | ⭐⭐⭐⭐⭐ Best-in-class | ⭐⭐⭐⭐ Goed |
| Layout behoud | ⭐⭐⭐⭐⭐ Perfect | ⭐⭐⭐⭐ Goed |
| Snelheid | ⭐⭐⭐⭐ Snel | ⭐⭐⭐⭐⭐ Zeer snel |
| Kosten | Betaald | Gratis tier |
| Betrouwbaarheid | ⭐⭐⭐⭐⭐ Hoogst | ⭐⭐⭐⭐ Hoog |
| Complexe documenten | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Goed |

## Configuratie

### API Keys Instellen

1. **Kopieer het voorbeeld bestand**:
   ```bash
   cp .env.example .env
   ```

2. **Vul je API keys in** in `.env`:
   ```bash
   # Vereist voor embeddings
   GEMINI_API_KEY=your_gemini_api_key_here

   # Aanbevolen voor beste OCR resultaten
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

3. **API Keys verkrijgen**:
   - **Gemini API**: https://makersuite.google.com/app/apikey (Gratis tier beschikbaar)
   - **Anthropic API**: https://console.anthropic.com/ (Betaald, maar goedkoop)

### Config Aanpassingen

In [config/config.yaml](config/config.yaml):

```yaml
claude:
  api_key: ${ANTHROPIC_API_KEY}
  model_name: "claude-opus-4-5-20251101"  # Latest and most capable (Nov 2024)
  # Alternative: "claude-sonnet-4-5-20250929" (faster, cheaper)
  # Alternative: "claude-haiku-4-5-20251001" (fastest, cheapest)
  max_tokens: 4096
  max_retries: 3
  timeout: 60

ocr:
  # Claude fallback (primair)
  claude_fallback:
    enabled: true
    use_when_confidence_below: 70
    prompt: "Extract all text from this image, including handwritten text.
             Preserve the original layout and structure. If any text is unclear
             or illegible, indicate it with [unclear]. Be thorough and accurate."

  # Gemini fallback (backup)
  gemini_fallback:
    enabled: true
    use_when_confidence_below: 70
    use_as_backup: true  # Alleen gebruiken als Claude faalt
```

**Model Keuze Tips**:
- **Opus 4.5** (default): Gebruik voor moeilijke handschriften en belangrijke documenten
- **Sonnet 4.5**: Balans tussen kosten en kwaliteit, goed voor de meeste use cases
- **Haiku 4.5**: Budget optie voor grote volumes duidelijke tekst

## Gebruik Scenarios

### Scenario 1: Alle Providers Beschikbaar (Aanbevolen)
```
Input: Handgeschreven nota scan met lage kwaliteit
→ Tesseract: 45% confidence (te laag)
→ EasyOCR: 62% confidence (te laag)
→ Claude: Succesvolle extractie ✓
→ Result: Hoogkwaliteit tekst met behouden layout
```

### Scenario 2: Alleen Gemini Beschikbaar
```
Input: Handgeschreven nota
→ Tesseract: 50% confidence (te laag)
→ EasyOCR: 65% confidence (te laag)
→ Claude: Niet beschikbaar
→ Gemini: Succesvolle extractie ✓
→ Result: Goede kwaliteit tekst
```

### Scenario 3: Claude Faalt
```
Input: Zeer moeilijke handgeschreven tekst
→ Local OCR: Te lage confidence
→ Claude: API error of mislukt
→ Gemini: Backup extractie ✓
→ Result: Gemini probeert als laatste redmiddel
```

### Scenario 4: Geen AI APIs (Alleen Lokaal)
```
Input: Duidelijk getypte tekst
→ Tesseract: 95% confidence ✓
→ Result: Snelle lokale extractie zonder API kosten
```

## Kosten Optimalisatie

### API Gebruik Minimaliseren:

1. **Lokale OCR eerst**: Gratis Tesseract en EasyOCR proberen eerst
2. **Confidence threshold**: Alleen AI gebruiken bij confidence < 70%
3. **Caching**: Embedding cache voorkomt dubbele API calls
4. **Batch processing**: Efficiënte verwerking van meerdere documenten

### Geschatte Kosten per Model:

**Claude Pricing** (approximaties voor OCR use case):
- **Opus 4.5**: ~$15 per 1 miljoen input tokens (~$10-15 per 1000 complexe afbeeldingen)
- **Sonnet 4.5**: ~$3 per 1 miljoen input tokens (~$2-3 per 1000 afbeeldingen)
- **Haiku 4.5**: ~$0.80 per 1 miljoen input tokens (~$0.50-1 per 1000 afbeeldingen)

**Gemini Pricing**:
- **Vision**: Gratis tier: 50 requests/dag, daarna betaald
- **Embeddings**: Gratis tier: 1500 requests/dag

**Tip**:
- Lokale OCR werkt gratis voor ~60-70% van documenten (goede kwaliteit)
- Claude wordt alleen gebruikt bij lage confidence (handschriften, slechte scans)
- Voor de meeste use cases: **<$5/maand** bij normale volumes
- Overweeg **Sonnet 4.5** als Opus te duur is (goede balans kwaliteit/kosten)

## Metadata Tracking

Het systeem voegt metadata toe over welke OCR methode gebruikt is:

```python
doc.metadata['ocr_method'] = 'claude'        # Claude gebruikt
doc.metadata['ocr_method'] = 'gemini'        # Gemini gebruikt
doc.metadata['ocr_method'] = 'gemini_backup' # Gemini als backup
doc.metadata['ocr_method'] = 'tesseract'     # Lokale OCR
```

Dit helpt bij:
- **Kwaliteit monitoring**: Zie welke methode het meest succesvol is
- **Debugging**: Begrijp welke fallback gebruikt werd
- **Cost tracking**: Identificeer hoeveel API calls gemaakt werden

## Installatie

### 1. Update Dependencies
```bash
pip install -r requirements.txt
```

Nieuwe dependency:
- `anthropic>=0.39.0` - Claude API client

### 2. Configureer API Keys
```bash
cp .env.example .env
# Edit .env en voeg je ANTHROPIC_API_KEY toe
```

### 3. Test de Setup
```bash
python main.py --input data/input/test_handwritten.jpg
```

## Troubleshooting

### Claude Fallback Werkt Niet

**Symptoom**: Systeem gebruikt alleen Gemini of lokale OCR

**Oplossingen**:
1. Check of ANTHROPIC_API_KEY correct is in `.env`
2. Verifieer API key: `echo $ANTHROPIC_API_KEY`
3. Check logs: `tail -f logs/pipeline.log`
4. Test Claude API apart:
   ```python
   import anthropic
   client = anthropic.Anthropic(api_key="your-key")
   # Test call
   ```

### API Rate Limits

**Claude**:
- **Rate limit**: Afhankelijk van je plan
- **Oplossing**: Verlaag `max_workers` in config.yaml

**Gemini**:
- **Free tier**: 50 requests/dag voor vision
- **Oplossing**: Upgrade naar betaald plan of gebruik alleen Claude

### Hoge Kosten

**Als je teveel API calls maakt**:

1. **Verhoog confidence threshold**:
   ```yaml
   claude_fallback:
     use_when_confidence_below: 80  # Was 70
   ```

2. **Disable Claude voor makkelijke afbeeldingen**:
   - Alleen gebruiken voor échte handschrift
   - Lokale OCR is vaak voldoende voor getypte tekst

3. **Monitor usage**:
   ```bash
   grep "Claude OCR" logs/pipeline.log | wc -l
   ```

## Best Practices

### 1. Scan Kwaliteit
- **Minimaal 300 DPI** voor handgeschreven documenten
- **Goed contrast**: Donkere inkt, lichte achtergrond
- **Rechte scans**: Vermijd scheef gescande pagina's

### 2. API Key Beveiliging
- Gebruik `.env` file (nooit committen!)
- Voeg `.env` toe aan `.gitignore`
- Roteer keys periodiek

### 3. Performance
- Gebruik `--no-parallel` voor debugging
- Parallel processing voor productie
- Monitor logs voor fallback gebruik

### 4. Cost Management
- Start met lokale OCR
- Gebruik Claude voor belangrijke documenten
- Gemini als gratis backup

## Toekomstige Verbeteringen

Mogelijke uitbreidingen:

- [ ] **OpenAI Vision fallback**: Nog een alternatief
- [ ] **Embedding provider fallback**: OpenAI of Cohere als Gemini backup
- [ ] **Adaptive threshold**: Dynamische confidence threshold per document type
- [ ] **Quality scoring**: Automatische kwaliteit beoordeling van OCR resultaten
- [ ] **A/B testing**: Vergelijk Claude vs Gemini resultaten voor je use case

## Support

Voor vragen of problemen:
- Check de logs: `logs/pipeline.log`
- Zie [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Check API status:
  - Claude: https://status.anthropic.com/
  - Gemini: https://status.cloud.google.com/
